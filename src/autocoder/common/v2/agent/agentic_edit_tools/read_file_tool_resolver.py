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
                        return ToolResult(success=True, message=f"{file_path}", content=content)
            except Exception as e:
                pass
            # else fallback to original file
            # Fallback to original file
            if not os.path.exists(abs_file_path):
                return ToolResult(success=False, message=f"Error: File not found at path: {file_path}")
            if not os.path.isfile(abs_file_path):
                return ToolResult(success=False, message=f"Error: Path is not a file: {file_path}")

            content = ""
            ext = os.path.splitext(abs_file_path)[1].lower()

            if ext == '.pdf':
                logger.info(f"Extracting text from PDF: {abs_file_path}")
                content = extract_text_from_pdf(abs_file_path)
            elif ext == '.docx':
                logger.info(f"Extracting text from DOCX: {abs_file_path}")
                content = extract_text_from_docx(abs_file_path)
            elif ext in ('.pptx', '.ppt'):
                logger.info(f"Extracting text from PPT/PPTX: {abs_file_path}")
                slide_texts = []
                for slide_identifier, slide_content in extract_text_from_ppt(abs_file_path):
                    slide_texts.append(f"--- Slide {slide_identifier} ---\n{slide_content}")
                content = "\n\n".join(slide_texts) if slide_texts else ""
            else:
                logger.info(f"Reading plain text file: {abs_file_path}")
                with open(abs_file_path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
            
            logger.info(f"Successfully processed file: {file_path}")
            return ToolResult(success=True, message=f"{file_path}", content=content)
        except Exception as e:
            logger.warning(f"Error processing file '{file_path}': {str(e)}")
            logger.exception(e) # Includes stack trace
            return ToolResult(success=False, message=f"An error occurred while processing the file '{file_path}': {str(e)}")
