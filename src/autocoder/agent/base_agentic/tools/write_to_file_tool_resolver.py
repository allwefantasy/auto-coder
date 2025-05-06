import os
from typing import Dict, Any, Optional
from autocoder.agent.base_agentic.types import WriteToFileTool, ToolResult  # Import ToolResult from types
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from loguru import logger
from autocoder.common import AutoCoderArgs
import typing

if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent

class WriteToFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['BaseAgent'], tool: WriteToFileTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: WriteToFileTool = tool  # For type hinting
        self.shadow_manager = self.agent.shadow_manager if self.agent else None

    def resolve(self) -> ToolResult:
        file_path = self.tool.path
        content = self.tool.content
        source_dir = self.args.source_dir or "."
        abs_project_dir = os.path.abspath(source_dir)
        abs_file_path = os.path.abspath(os.path.join(source_dir, file_path))

        # Security check: ensure the path is within the source directory
        if not abs_file_path.startswith(abs_project_dir):
            return ToolResult(success=False, message=f"Error: Access denied. Attempted to write file outside the project directory: {file_path}")

        try:
            if self.shadow_manager:
                shadow_path = self.shadow_manager.to_shadow_path(abs_file_path)
                # Ensure shadow directory exists
                os.makedirs(os.path.dirname(shadow_path), exist_ok=True)
                with open(shadow_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"[Shadow] Successfully wrote shadow file: {shadow_path}")

                # 回调AgenticEdit，记录变更
                if self.agent:
                    rel_path = os.path.relpath(abs_file_path, abs_project_dir)
                    self.agent.record_file_change(rel_path, "added", diff=None, content=content)

                return ToolResult(success=True, message=f"Successfully wrote to file (shadow): {file_path}", content=content)
            else:
                # No shadow manager fallback to original file
                os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)
                with open(abs_file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                logger.info(f"Successfully wrote to file: {file_path}")

                if self.agent:
                    rel_path = os.path.relpath(abs_file_path, abs_project_dir)
                    self.agent.record_file_change(rel_path, "added", diff=None, content=content)

                return ToolResult(success=True, message=f"Successfully wrote to file: {file_path}", content=content)
        except Exception as e:
            logger.error(f"Error writing to file '{file_path}': {str(e)}")
            return ToolResult(success=False, message=f"An error occurred while writing to the file: {str(e)}")