
import os
import re
import glob
from typing import Dict, Any, Optional
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import SearchFilesTool, ToolResult  # Import ToolResult from types
from loguru import logger
from autocoder.common import AutoCoderArgs
import typing

from autocoder.ignorefiles.ignore_file_utils import should_ignore

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit  


class SearchFilesToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: SearchFilesTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: SearchFilesTool = tool
        self.shadow_manager = self.agent.shadow_manager if self.agent else None

    def resolve(self) -> ToolResult:
        search_path_str = self.tool.path
        regex_pattern = self.tool.regex
        file_pattern = self.tool.file_pattern or "*"
        source_dir = self.args.source_dir or "."
        absolute_source_dir = os.path.abspath(source_dir)
        absolute_search_path = os.path.abspath(os.path.join(source_dir, search_path_str))

        # Security check
        if not absolute_search_path.startswith(absolute_source_dir):
            return ToolResult(success=False, message=f"Error: Access denied. Attempted to search outside the project directory: {search_path_str}")

        # Determine search base directory: prefer shadow if exists
        search_base_path = absolute_search_path
        shadow_exists = False
        if self.shadow_manager:
            try:
                shadow_dir_path = self.shadow_manager.to_shadow_path(absolute_search_path)
                if os.path.exists(shadow_dir_path) and os.path.isdir(shadow_dir_path):
                    search_base_path = shadow_dir_path
                    shadow_exists = True
            except Exception as e:
                logger.warning(f"Error checking shadow path for {absolute_search_path}: {e}")

        # Validate that at least one of the directories exists
        if not os.path.exists(absolute_search_path) and not shadow_exists:
            return ToolResult(success=False, message=f"Error: Search path not found: {search_path_str}")
        if os.path.exists(absolute_search_path) and not os.path.isdir(absolute_search_path):
            return ToolResult(success=False, message=f"Error: Search path is not a directory: {search_path_str}")
        if shadow_exists and not os.path.isdir(search_base_path):
            return ToolResult(success=False, message=f"Error: Shadow search path is not a directory: {search_base_path}")

        results = []
        try:
            compiled_regex = re.compile(regex_pattern)
            search_glob_pattern = os.path.join(search_base_path, "**", file_pattern)

            logger.info(f"Searching for regex '{regex_pattern}' in files matching '{file_pattern}' under '{search_base_path}' (shadow: {shadow_exists}) with ignore rules applied.")

            for filepath in glob.glob(search_glob_pattern, recursive=True):
                abs_path = os.path.abspath(filepath)
                if should_ignore(abs_path):
                    continue

                if os.path.isfile(filepath):
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                            lines = f.readlines()
                        for i, line in enumerate(lines):
                            if compiled_regex.search(line):
                                context_start = max(0, i - 2)
                                context_end = min(len(lines), i + 3)
                                context = "".join([f"{j+1}: {lines[j]}" for j in range(context_start, context_end)])
                                if shadow_exists and self.shadow_manager:
                                    try:
                                        abs_project_path = self.shadow_manager.from_shadow_path(filepath)
                                        relative_path = os.path.relpath(abs_project_path, source_dir)
                                    except Exception:
                                        relative_path = os.path.relpath(filepath, source_dir)
                                else:
                                    relative_path = os.path.relpath(filepath, source_dir)
                                results.append({
                                    "path": relative_path,
                                    "line_number": i + 1,
                                    "match_line": line.strip(),
                                    "context": context.strip()
                                })
                    except Exception as e:
                        logger.warning(f"Could not read or process file {filepath}: {e}")
                        continue

            message = f"Search completed. Found {len(results)} matches."
            logger.info(message)
            return ToolResult(success=True, message=message, content=results)

        except re.error as e:
            logger.error(f"Invalid regex pattern '{regex_pattern}': {e}")
            return ToolResult(success=False, message=f"Invalid regex pattern: {e}")
        except Exception as e:
            logger.error(f"Error during file search: {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred during search: {str(e)}")
