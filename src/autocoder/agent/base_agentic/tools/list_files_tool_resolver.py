import os
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.agent.base_agentic.types import ListFilesTool, ToolResult  # Import ToolResult from types
from typing import Optional, Dict, Any, List, Set, Union
import fnmatch
import re
import json
from loguru import logger
import typing
from autocoder.common import AutoCoderArgs

from autocoder.common.ignorefiles.ignore_file_utils import should_ignore

if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent


class ListFilesToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['BaseAgent'], tool: ListFilesTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: ListFilesTool = tool  # For type hinting
        self.shadow_manager = self.agent.shadow_manager

    def list_files_in_dir(self, base_dir: str, recursive: bool, source_dir: str, is_outside_source: bool) -> Set[str]:
        """Helper function to list files in a directory"""
        result = set()
        try:
            if recursive:
                for root, dirs, files in os.walk(base_dir):
                    # Modify dirs in-place to skip ignored dirs early
                    dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d))]
                    for name in files:
                        full_path = os.path.join(root, name)
                        if should_ignore(full_path):
                            continue
                        display_path = os.path.relpath(full_path, source_dir) if not is_outside_source else full_path
                        result.add(display_path)
                    for d in dirs:
                        full_path = os.path.join(root, d)
                        display_path = os.path.relpath(full_path, source_dir) if not is_outside_source else full_path
                        result.add(display_path + "/")
            else:
                for item in os.listdir(base_dir):
                    full_path = os.path.join(base_dir, item)
                    if should_ignore(full_path):
                        continue
                    display_path = os.path.relpath(full_path, source_dir) if not is_outside_source else full_path
                    if os.path.isdir(full_path):
                        result.add(display_path + "/")
                    else:
                        result.add(display_path)
        except Exception as e:
            logger.warning(f"Error listing files in {base_dir}: {e}")
        return result
        
    def list_files_with_shadow(self, list_path_str: str, recursive: bool, source_dir: str, absolute_source_dir: str, absolute_list_path: str) -> Union[ToolResult, List[str]]:
        """List files using shadow manager for path translation"""
        # Security check: Allow listing outside source_dir IF the original path is outside?
        is_outside_source = not absolute_list_path.startswith(absolute_source_dir)
        if is_outside_source:
            logger.warning(f"Listing path is outside the project source directory: {list_path_str}")

        # Check if shadow directory exists for this path
        shadow_exists = False
        shadow_dir_path = None
        if self.shadow_manager:
            try:
                shadow_dir_path = self.shadow_manager.to_shadow_path(absolute_list_path)
                if os.path.exists(shadow_dir_path) and os.path.isdir(shadow_dir_path):
                    shadow_exists = True
            except Exception as e:
                logger.warning(f"Error checking shadow path for {absolute_list_path}: {e}")

        # Validate that at least one of the directories exists
        if not os.path.exists(absolute_list_path) and not shadow_exists:
            return ToolResult(success=False, message=f"Error: Path not found: {list_path_str}")
        if os.path.exists(absolute_list_path) and not os.path.isdir(absolute_list_path):
            return ToolResult(success=False, message=f"Error: Path is not a directory: {list_path_str}")
        if shadow_exists and not os.path.isdir(shadow_dir_path):
            return ToolResult(success=False, message=f"Error: Shadow path is not a directory: {shadow_dir_path}")

        # Collect files from shadow and/or source directory
        shadow_files_set = set()
        if shadow_exists:
            shadow_files_set = self.list_files_in_dir(shadow_dir_path, recursive, source_dir, is_outside_source)

        source_files_set = set()
        if os.path.exists(absolute_list_path) and os.path.isdir(absolute_list_path):
            source_files_set = self.list_files_in_dir(absolute_list_path, recursive, source_dir, is_outside_source)

        # Merge results, prioritizing shadow files if exist
        if shadow_exists:
            merged_files = shadow_files_set.union(
                {f for f in source_files_set if f not in shadow_files_set}
            )
        else:
            merged_files = source_files_set

        try:
            message = f"Successfully listed contents of '{list_path_str}' (Recursive: {recursive}). Found {len(merged_files)} items."
            logger.info(message)
            return sorted(merged_files)
        except Exception as e:
            logger.error(f"Error listing files in '{list_path_str}': {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred while listing files: {str(e)}")

    def list_files_normal(self, list_path_str: str, recursive: bool, source_dir: str, absolute_source_dir: str, absolute_list_path: str) -> Union[ToolResult, List[str]]:
        """List files directly without using shadow manager"""
        # Security check: Allow listing outside source_dir IF the original path is outside?
        is_outside_source = not absolute_list_path.startswith(absolute_source_dir)
        if is_outside_source:
            logger.warning(f"Listing path is outside the project source directory: {list_path_str}")

        # Validate that the directory exists
        if not os.path.exists(absolute_list_path):
            return ToolResult(success=False, message=f"Error: Path not found: {list_path_str}")
        if not os.path.isdir(absolute_list_path):
            return ToolResult(success=False, message=f"Error: Path is not a directory: {list_path_str}")

        # Collect files from the directory
        files_set = self.list_files_in_dir(absolute_list_path, recursive, source_dir, is_outside_source)

        try:
            message = f"Successfully listed contents of '{list_path_str}' (Recursive: {recursive}). Found {len(files_set)} items."
            logger.info(message)
            return sorted(files_set)
        except Exception as e:
            logger.error(f"Error listing files in '{list_path_str}': {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred while listing files: {str(e)}")

    def resolve(self) -> ToolResult:
        """Resolve the list files tool by calling the appropriate implementation"""
        list_path_str = self.tool.path
        recursive = self.tool.recursive or False
        source_dir = self.args.source_dir or "."
        absolute_source_dir = os.path.abspath(source_dir)
        absolute_list_path = os.path.abspath(os.path.join(source_dir, list_path_str))

        # Choose the appropriate implementation based on whether shadow_manager is available
        if self.shadow_manager:
            result = self.list_files_with_shadow(list_path_str, recursive, source_dir, absolute_source_dir, absolute_list_path)
        else:
            result = self.list_files_normal(list_path_str, recursive, source_dir, absolute_source_dir, absolute_list_path)

        # Handle the case where the implementation returns a sorted list instead of a ToolResult
        if isinstance(result, list):
            message = f"Successfully listed contents of '{list_path_str}' (Recursive: {recursive}). Found {len(result)} items."
            return ToolResult(success=True, message=message, content=result)
        else:
            return result
