import os
from typing import Dict, Any, Optional
from .base_tool_resolver import BaseToolResolver
from autocoder.agent.agentic_edit_types import ReadFileTool, ToolResult # Import ToolResult from types
from loguru import logger


class ReadFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional[Any], tool: ReadFileTool, args: Dict[str, Any]):
        super().__init__(agent, tool, args)
        self.tool: ReadFileTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        file_path = self.tool.path
        source_dir = self.args.get("source_dir", ".")
        absolute_path = os.path.abspath(os.path.join(source_dir, file_path))

        # Security check: ensure the path is within the source directory
        if not absolute_path.startswith(os.path.abspath(source_dir)):
            return ToolResult(success=False, message=f"Error: Access denied. Attempted to read file outside the project directory: {file_path}")

        try:
            if not os.path.exists(absolute_path):
                return ToolResult(success=False, message=f"Error: File not found at path: {file_path}")
            if not os.path.isfile(absolute_path):
                 return ToolResult(success=False, message=f"Error: Path is not a file: {file_path}")

            # Handle different file types if necessary (e.g., PDF, DOCX)
            # For now, assume text files
            with open(absolute_path, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            logger.info(f"Successfully read file: {file_path}")
            return ToolResult(success=True, message=f"Successfully read file: {file_path}", content=content)
        except Exception as e:
            logger.error(f"Error reading file '{file_path}': {str(e)}")
            return ToolResult(success=False, message=f"An error occurred while reading the file: {str(e)}")
