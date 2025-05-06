import os
import re
import glob
from typing import Dict, Any, Optional, List
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.agent.base_agentic.types import SearchFilesTool, ToolResult  # Import ToolResult from types
from loguru import logger
from autocoder.common import AutoCoderArgs
import typing

from autocoder.common.ignorefiles.ignore_file_utils import should_ignore

if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent


class SearchFilesToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['BaseAgent'], tool: SearchFilesTool, args: AutoCoderArgs):
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

        # Check if shadow directory exists
        shadow_exists = False
        shadow_dir_path = None
        if self.shadow_manager:
            try:
                shadow_dir_path = self.shadow_manager.to_shadow_path(absolute_search_path)
                if os.path.exists(shadow_dir_path) and os.path.isdir(shadow_dir_path):
                    shadow_exists = True
            except Exception as e:
                logger.warning(f"Error checking shadow path for {absolute_search_path}: {e}")

        # Validate that at least one of the directories exists
        if not os.path.exists(absolute_search_path) and not shadow_exists:
            return ToolResult(success=False, message=f"Error: Search path not found: {search_path_str}")
        if os.path.exists(absolute_search_path) and not os.path.isdir(absolute_search_path):
            return ToolResult(success=False, message=f"Error: Search path is not a directory: {search_path_str}")
        if shadow_exists and not os.path.isdir(shadow_dir_path):
            return ToolResult(success=False, message=f"Error: Shadow search path is not a directory: {shadow_dir_path}")

        try:
            compiled_regex = re.compile(regex_pattern)
            
            # Helper function to search in a directory
            def search_in_dir(base_dir, is_shadow=False):
                search_results = []
                search_glob_pattern = os.path.join(base_dir, "**", file_pattern)
                
                logger.info(f"Searching for regex '{regex_pattern}' in files matching '{file_pattern}' under '{base_dir}' (shadow: {is_shadow}) with ignore rules applied.")
                
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
                                    
                                    if is_shadow and self.shadow_manager:
                                        try:
                                            abs_project_path = self.shadow_manager.from_shadow_path(filepath)
                                            relative_path = os.path.relpath(abs_project_path, source_dir)
                                        except Exception:
                                            relative_path = os.path.relpath(filepath, source_dir)
                                    else:
                                        relative_path = os.path.relpath(filepath, source_dir)
                                    
                                    search_results.append({
                                        "path": relative_path,
                                        "line_number": i + 1,
                                        "match_line": line.strip(),
                                        "context": context.strip()
                                    })
                        except Exception as e:
                            logger.warning(f"Could not read or process file {filepath}: {e}")
                            continue
                
                return search_results
            
            # Search in both directories and merge results
            shadow_results = []
            source_results = []
            
            if shadow_exists:
                shadow_results = search_in_dir(shadow_dir_path, is_shadow=True)
            
            if os.path.exists(absolute_search_path) and os.path.isdir(absolute_search_path):
                source_results = search_in_dir(absolute_search_path, is_shadow=False)
            
            # Merge results, prioritizing shadow results
            # Create a dictionary for quick lookup
            results_dict = {}
            for result in source_results:
                key = (result["path"], result["line_number"])
                results_dict[key] = result
            
            # Override with shadow results
            for result in shadow_results:
                key = (result["path"], result["line_number"])
                results_dict[key] = result
            
            # Convert back to list
            merged_results = list(results_dict.values())

            message = f"Search completed. Found {len(merged_results)} matches."
            logger.info(message)
            return ToolResult(success=True, message=message, content=merged_results)

        except re.error as e:
            logger.error(f"Invalid regex pattern '{regex_pattern}': {e}")
            return ToolResult(success=False, message=f"Invalid regex pattern: {e}")
        except Exception as e:
            logger.error(f"Error during file search: {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred during search: {str(e)}")
