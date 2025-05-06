import os
from typing import Dict, Any, Optional
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.agent.base_agentic.types import ReadFileTool, ToolResult  # Import ToolResult from types
from loguru import logger
import typing
from autocoder.common import AutoCoderArgs

if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent


class ReadFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['BaseAgent'], tool: ReadFileTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: ReadFileTool = tool  # For type hinting
        self.shadow_manager = self.agent.shadow_manager if self.agent else None

    def resolve(self) -> ToolResult:
        file_path = self.tool.path
        source_dir = self.args.source_dir or "."
        abs_project_dir = os.path.abspath(source_dir)
        abs_file_path = os.path.abspath(os.path.join(source_dir, file_path))

        # # Security check: ensure the path is within the source directory
        # if not abs_file_path.startswith(abs_project_dir):
        #     return ToolResult(success=False, message=f"Error: Access denied. Attempted to read file outside the project directory: {file_path}")

        try:
            try:
                if self.shadow_manager:
                    shadow_path = self.shadow_manager.to_shadow_path(abs_file_path)
                    # If shadow file exists, read from it
                    if os.path.exists(shadow_path) and os.path.isfile(shadow_path):
                        with open(shadow_path, 'r', encoding='utf-8', errors='replace') as f:
                            content = f.read()
                        logger.info(f"[Shadow] Successfully read shadow file: {shadow_path}")
                        return ToolResult(success=True, message=f"Successfully read file (shadow): {file_path}", content=content)
            except Exception as e:
                pass
            # else fallback to original file
            # Fallback to original file
            if not os.path.exists(abs_file_path):
                return ToolResult(success=False, message=f"Error: File not found at path: {file_path}")
            if not os.path.isfile(abs_file_path):
                return ToolResult(success=False, message=f"Error: Path is not a file: {file_path}")

            with open(abs_file_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            logger.info(f"Successfully read file: {file_path}")
            return ToolResult(success=True, message=f"Successfully read file: {file_path}", content=content)
        except Exception as e:
            logger.error(f"Error reading file '{file_path}': {str(e)}")
            return ToolResult(success=False, message=f"An error occurred while reading the file: {str(e)}")
