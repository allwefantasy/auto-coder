import os
import re
import glob
from typing import Dict, Any, Optional, List, Union
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import SearchFilesTool, ToolResult  # Import ToolResult from types
from loguru import logger
from autocoder.common import AutoCoderArgs
import typing

from autocoder.common.ignorefiles.ignore_file_utils import should_ignore

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit  


class SearchFilesToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: SearchFilesTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: SearchFilesTool = tool
        self.shadow_manager = self.agent.shadow_manager if self.agent else None

    def search_in_dir(self, base_dir: str, regex_pattern: str, file_pattern: str, source_dir: str, is_shadow: bool = False, compiled_regex: Optional[re.Pattern] = None) -> List[Dict[str, Any]]:
        """Helper function to search in a directory"""
        search_results = []
        search_glob_pattern = os.path.join(base_dir, "**", file_pattern)
        
        logger.info(f"Searching for regex '{regex_pattern}' in files matching '{file_pattern}' under '{base_dir}' (shadow: {is_shadow}) with ignore rules applied.")
        
        if compiled_regex is None:
            compiled_regex = re.compile(regex_pattern)
            
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

    def search_files_with_shadow(self, search_path_str: str, regex_pattern: str, file_pattern: str, source_dir: str, absolute_source_dir: str, absolute_search_path: str) -> Union[ToolResult, List[Dict[str, Any]]]:
        """Search files using shadow manager for path translation"""
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
            
            # Search in both directories and merge results
            shadow_results = []
            source_results = []
            
            if shadow_exists:
                shadow_results = self.search_in_dir(shadow_dir_path, regex_pattern, file_pattern, source_dir, is_shadow=True, compiled_regex=compiled_regex)
            
            if os.path.exists(absolute_search_path) and os.path.isdir(absolute_search_path):
                source_results = self.search_in_dir(absolute_search_path, regex_pattern, file_pattern, source_dir, is_shadow=False, compiled_regex=compiled_regex)
            
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

            return merged_results

        except re.error as e:
            logger.error(f"Invalid regex pattern '{regex_pattern}': {e}")
            return ToolResult(success=False, message=f"Invalid regex pattern: {e}")
        except Exception as e:
            logger.error(f"Error during file search: {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred during search: {str(e)}")
    
    def search_files_normal(self, search_path_str: str, regex_pattern: str, file_pattern: str, source_dir: str, absolute_source_dir: str, absolute_search_path: str) -> Union[ToolResult, List[Dict[str, Any]]]:
        """Search files directly without using shadow manager"""
        # Security check
        if not absolute_search_path.startswith(absolute_source_dir):
            return ToolResult(success=False, message=f"Error: Access denied. Attempted to search outside the project directory: {search_path_str}")

        # Validate that the directory exists
        if not os.path.exists(absolute_search_path):
            return ToolResult(success=False, message=f"Error: Search path not found: {search_path_str}")
        if not os.path.isdir(absolute_search_path):
            return ToolResult(success=False, message=f"Error: Search path is not a directory: {search_path_str}")

        try:
            compiled_regex = re.compile(regex_pattern)
            
            # Search in the directory
            search_results = self.search_in_dir(absolute_search_path, regex_pattern, file_pattern, source_dir, is_shadow=False, compiled_regex=compiled_regex)
            
            return search_results

        except re.error as e:
            logger.error(f"Invalid regex pattern '{regex_pattern}': {e}")
            return ToolResult(success=False, message=f"Invalid regex pattern: {e}")
        except Exception as e:
            logger.error(f"Error during file search: {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred during search: {str(e)}")

    def resolve(self) -> ToolResult:
        """Resolve the search files tool by calling the appropriate implementation"""
        search_path_str = self.tool.path
        regex_pattern = self.tool.regex
        file_pattern = self.tool.file_pattern or "*"
        source_dir = self.args.source_dir or "."
        absolute_source_dir = os.path.abspath(source_dir)
        absolute_search_path = os.path.abspath(os.path.join(source_dir, search_path_str))

        # Choose the appropriate implementation based on whether shadow_manager is available
        if self.shadow_manager:
            result = self.search_files_with_shadow(search_path_str, regex_pattern, file_pattern, source_dir, absolute_source_dir, absolute_search_path)
        else:
            result = self.search_files_normal(search_path_str, regex_pattern, file_pattern, source_dir, absolute_source_dir, absolute_search_path)

        # Handle the case where the implementation returns a list instead of a ToolResult
        if isinstance(result, list):
            total_results = len(result)            
            # Limit results to 200 if needed
            if total_results > 200:
                truncated_results = result[:200]
                message = f"Search completed. Found {total_results} matches, showing only the first 200."                
                logger.info(message)
                return ToolResult(success=True, message=message, content=truncated_results)
            else:
                message = f"Search completed. Found {total_results} matches."
                logger.info(message)
                return ToolResult(success=True, message=message, content=result)
        else:
            return result
