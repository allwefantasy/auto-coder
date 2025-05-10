import os
from typing import Dict, Any, Optional
from autocoder.common import AutoCoderArgs
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import ReadFileTool, ToolResult  # Import ToolResult from types
from loguru import logger
import typing
from autocoder.rag.loaders import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_ppt
)

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit


class ReadFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: ReadFileTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: ReadFileTool = tool  # For type hinting
        self.shadow_manager = self.agent.shadow_manager if self.agent else None

    def _read_file_content(self, file_path_to_read: str) -> str:
        content = ""
        ext = os.path.splitext(file_path_to_read)[1].lower()

        if ext == '.pdf':
            logger.info(f"Extracting text from PDF: {file_path_to_read}")
            content = extract_text_from_pdf(file_path_to_read)
        elif ext == '.docx':
            logger.info(f"Extracting text from DOCX: {file_path_to_read}")
            content = extract_text_from_docx(file_path_to_read)
        elif ext in ('.pptx', '.ppt'):
            logger.info(f"Extracting text from PPT/PPTX: {file_path_to_read}")
            slide_texts = []
            for slide_identifier, slide_text_content in extract_text_from_ppt(file_path_to_read):
                slide_texts.append(f"--- Slide {slide_identifier} ---\n{slide_text_content}")
            content = "\n\n".join(slide_texts) if slide_texts else ""
        else:
            logger.info(f"Reading plain text file: {file_path_to_read}")
            with open(file_path_to_read, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
        return content

    def resolve(self) -> ToolResult:
        file_path = self.tool.path
        source_dir = self.args.source_dir or "."
        abs_project_dir = os.path.abspath(source_dir)
        abs_file_path = os.path.abspath(os.path.join(source_dir, file_path))

        # # Security check: ensure the path is within the source directory
        # if not abs_file_path.startswith(abs_project_dir):
        #     return ToolResult(success=False, message=f"Error: Access denied. Attempted to read file outside the project directory: {file_path}")

        try:
            # Attempt to read from shadow file first
            if self.shadow_manager:
                shadow_path = self.shadow_manager.to_shadow_path(abs_file_path)
                if os.path.exists(shadow_path) and os.path.isfile(shadow_path):
                    try:
                        # Use the new centralized method for shadow files
                        content = self._read_file_content(shadow_path)
                        logger.info(f"[Shadow] Successfully processed shadow file: {shadow_path}")
                        return ToolResult(success=True, message=f"{file_path}", content=content)
                    except Exception as e_shadow:
                        logger.warning(f"Failed to read shadow file {shadow_path} with _read_file_content: {str(e_shadow)}. Falling back to original file.")
                        # Fall through to read the original file if shadow read fails

            # If not read from shadow, or shadow reading failed, proceed with original file
            if not os.path.exists(abs_file_path):
                return ToolResult(success=False, message=f"Error: File not found at path: {file_path}")
            if not os.path.isfile(abs_file_path):
                return ToolResult(success=False, message=f"Error: Path is not a file: {file_path}")

            # Use the new centralized method for original files
            content = self._read_file_content(abs_file_path)
            logger.info(f"Successfully processed file: {file_path}")
            return ToolResult(success=True, message=f"{file_path}", content=content)
        
        except Exception as e:
            # This will catch exceptions from _read_file_content if they are not caught internally,
            # or other unexpected errors.
            logger.warning(f"Error processing file '{file_path}': {str(e)}")
            logger.exception(e) # Includes stack trace
            return ToolResult(success=False, message=f"An error occurred while processing the file '{file_path}': {str(e)}")
