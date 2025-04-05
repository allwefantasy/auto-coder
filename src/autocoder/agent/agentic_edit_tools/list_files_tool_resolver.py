import os
from typing import Dict, Any, Optional
from .base_tool_resolver import BaseToolResolver
from autocoder.agent.agentic_edit_types import ListFilesTool, ToolResult # Import ToolResult from types
from loguru import logger


class ListFilesToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional[Any], tool: ListFilesTool, args: Dict[str, Any]):
        super().__init__(agent, tool, args)
        self.tool: ListFilesTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        list_path_str = self.tool.path
        recursive = self.tool.recursive or False
        source_dir = self.args.get("source_dir", ".")
        absolute_list_path = os.path.abspath(os.path.join(source_dir, list_path_str))

        # Security check: Allow listing outside source_dir IF the original path is outside?
        # For now, let's restrict to source_dir for safety, unless path explicitly starts absolute
        # This needs careful consideration based on security requirements.
        # Let's allow listing anywhere for now, but log a warning if outside source_dir.
        is_outside_source = not absolute_list_path.startswith(os.path.abspath(source_dir))
        if is_outside_source:
             logger.warning(f"Listing path is outside the project source directory: {list_path_str}")
             # Add more checks if needed, e.g., prevent listing sensitive system dirs

        if not os.path.exists(absolute_list_path):
            return ToolResult(success=False, message=f"Error: Path not found: {list_path_str}")
        if not os.path.isdir(absolute_list_path):
             return ToolResult(success=False, message=f"Error: Path is not a directory: {list_path_str}")

        file_list = []
        try:
            if recursive:
                for root, dirs, files in os.walk(absolute_list_path):
                    for name in files:
                        full_path = os.path.join(root, name)
                        # Return relative path if inside source_dir, else absolute
                        display_path = os.path.relpath(full_path, source_dir) if not is_outside_source else full_path
                        file_list.append(display_path)
                    for name in dirs:
                         # Optionally list directories too? The description implies files and dirs.
                         full_path = os.path.join(root, name)
                         display_path = os.path.relpath(full_path, source_dir) if not is_outside_source else full_path
                         file_list.append(display_path + "/") # Indicate directory
            else:
                for item in os.listdir(absolute_list_path):
                    full_path = os.path.join(absolute_list_path, item)
                    display_path = os.path.relpath(full_path, source_dir) if not is_outside_source else full_path
                    if os.path.isdir(full_path):
                        file_list.append(display_path + "/")
                    else:
                        file_list.append(display_path)

            message = f"Successfully listed contents of '{list_path_str}' (Recursive: {recursive}). Found {len(file_list)} items."
            logger.info(message)
            return ToolResult(success=True, message=message, content=sorted(file_list))

        except Exception as e:
            logger.error(f"Error listing files in '{list_path_str}': {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred while listing files: {str(e)}")