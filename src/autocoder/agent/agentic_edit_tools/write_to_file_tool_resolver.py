import os
from typing import Dict, Any, Optional
from .base_tool_resolver import BaseToolResolver, ToolResult
from autocoder.agent.agentic_edit_types import WriteToFileTool
from loguru import logger


class WriteToFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional[Any], tool: WriteToFileTool, args: Dict[str, Any]):
        super().__init__(agent, tool, args)
        self.tool: WriteToFileTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        file_path = self.tool.path
        content = self.tool.content
        source_dir = self.args.get("source_dir", ".")
        absolute_path = os.path.abspath(os.path.join(source_dir, file_path))

        # Security check: ensure the path is within the source directory
        if not absolute_path.startswith(os.path.abspath(source_dir)):
            return ToolResult(success=False, message=f"Error: Access denied. Attempted to write file outside the project directory: {file_path}")

        try:
            # Create directories if they don't exist
            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

            with open(absolute_path, 'w', encoding='utf-8') as f:
                f.write(content)

            logger.info(f"Successfully wrote to file: {file_path}")
            # Return the final content (might be changed by auto-formatting later)
            # For simplicity now, just return the written content
            return ToolResult(success=True, message=f"Successfully wrote to file: {file_path}", content=content)
        except Exception as e:
            logger.error(f"Error writing to file '{file_path}': {str(e)}")
            return ToolResult(success=False, message=f"An error occurred while writing to the file: {str(e)}")