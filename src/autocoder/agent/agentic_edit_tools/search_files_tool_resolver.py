import os
import re
import glob
from typing import Dict, Any, Optional
from .base_tool_resolver import BaseToolResolver
from autocoder.agent.agentic_edit_types import SearchFilesTool, ToolResult # Import ToolResult from types
from loguru import logger


class SearchFilesToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional[Any], tool: SearchFilesTool, args: Dict[str, Any]):
        super().__init__(agent, tool, args)
        self.tool: SearchFilesTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        search_path_str = self.tool.path
        regex_pattern = self.tool.regex
        file_pattern = self.tool.file_pattern or "*" # Default to all files
        source_dir = self.args.get("source_dir", ".")
        absolute_search_path = os.path.abspath(os.path.join(source_dir, search_path_str))

        # Security check
        if not absolute_search_path.startswith(os.path.abspath(source_dir)):
            return ToolResult(success=False, message=f"Error: Access denied. Attempted to search outside the project directory: {search_path_str}")

        if not os.path.exists(absolute_search_path):
            return ToolResult(success=False, message=f"Error: Search path not found: {search_path_str}")
        if not os.path.isdir(absolute_search_path):
             return ToolResult(success=False, message=f"Error: Search path is not a directory: {search_path_str}")

        results = []
        try:
            compiled_regex = re.compile(regex_pattern)
            search_glob_pattern = os.path.join(absolute_search_path, "**", file_pattern)

            logger.info(f"Searching for regex '{regex_pattern}' in files matching '{file_pattern}' under '{absolute_search_path}'")

            for filepath in glob.glob(search_glob_pattern, recursive=True):
                if os.path.isfile(filepath):
                    try:
                        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
                            lines = f.readlines()
                        for i, line in enumerate(lines):
                            if compiled_regex.search(line):
                                # Provide context (e.g., line number and surrounding lines)
                                context_start = max(0, i - 2)
                                context_end = min(len(lines), i + 3)
                                context = "".join([f"{j+1}: {lines[j]}" for j in range(context_start, context_end)])
                                relative_path = os.path.relpath(filepath, source_dir)
                                results.append({
                                    "path": relative_path,
                                    "line_number": i + 1,
                                    "match_line": line.strip(),
                                    "context": context.strip()
                                })
                                # Limit results per file? Or overall? For now, collect all.
                    except Exception as e:
                        logger.warning(f"Could not read or process file {filepath}: {e}")
                        continue # Skip files that can't be read

            message = f"Search completed. Found {len(results)} matches."
            logger.info(message)
            return ToolResult(success=True, message=message, content=results)

        except re.error as e:
            logger.error(f"Invalid regex pattern '{regex_pattern}': {e}")
            return ToolResult(success=False, message=f"Invalid regex pattern: {e}")
        except Exception as e:
            logger.error(f"Error during file search: {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred during search: {str(e)}")