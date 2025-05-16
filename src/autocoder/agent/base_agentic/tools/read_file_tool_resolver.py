import os
from typing import Dict, Any, Optional
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.agent.base_agentic.types import ReadFileTool, ToolResult  # Import ToolResult from types
from loguru import logger
import typing
from autocoder.common import AutoCoderArgs
from autocoder.common.context_pruner import PruneContext
from autocoder.common import SourceCode
from autocoder.rag.token_counter import count_tokens
from loguru import logger
import typing
from autocoder.rag.loaders import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_ppt
)

if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent


class ReadFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['BaseAgent'], tool: ReadFileTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: ReadFileTool = tool  # For type hinting
        self.shadow_manager = self.agent.shadow_manager if self.agent else None
        self.context_pruner = PruneContext(
            max_tokens=self.args.context_prune_safe_zone_tokens,
            args=self.args,
            llm=self.agent.context_prune_llm
        )

    def _prune_file_content(self, content: str, file_path: str) -> str:
        """对文件内容进行剪枝处理"""
        if not self.context_pruner:
            return content

        # 计算 token 数量
        tokens = count_tokens(content)
        if tokens <= self.args.context_prune_safe_zone_tokens:
            return content

        # 创建 SourceCode 对象
        source_code = SourceCode(
            module_name=file_path,
            source_code=content,
            tokens=tokens
        )

        # 使用 context_pruner 进行剪枝
        pruned_sources = self.context_pruner.handle_overflow(
            file_sources=[source_code],
            conversations=self.agent.current_conversations if self.agent else [],
            strategy=self.args.context_prune_strategy
        )

        if not pruned_sources:
            return content

        return pruned_sources[0].source_code

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

        # 对内容进行剪枝处理
        return self._prune_file_content(content, file_path_to_read)
    

    def read_file_normal(self, file_path: str, source_dir: str, abs_project_dir: str, abs_file_path: str) -> ToolResult:
        """Read file directly without using shadow manager"""
        try:
            # Security check: ensure the path is within the source directory
            if not abs_file_path.startswith(abs_project_dir):
                return ToolResult(success=False, message=f"Error: Access denied. Attempted to read file outside the project directory: {file_path}")

            # Check if file exists
            if not os.path.exists(abs_file_path):
                return ToolResult(success=False, message=f"Error: File not found: {file_path}")
            if not os.path.isfile(abs_file_path):
                return ToolResult(success=False, message=f"Error: Not a file: {file_path}")

            # Read file content
            content = self._read_file_content(abs_file_path)
            logger.info(f"Successfully read file: {file_path}")
            return ToolResult(success=True, message=f"Successfully read file: {file_path}", content=content)
        except Exception as e:
            logger.error(f"Error reading file '{file_path}': {str(e)}")
            return ToolResult(success=False, message=f"An error occurred while reading the file: {str(e)}")

    def resolve(self) -> ToolResult:
        """Resolve the read file tool by calling the appropriate implementation"""
        file_path = self.tool.path
        source_dir = self.args.source_dir or "."
        abs_project_dir = os.path.abspath(source_dir)
        abs_file_path = os.path.abspath(os.path.join(source_dir, file_path))
        
        return self.read_file_normal(file_path, source_dir, abs_project_dir, abs_file_path)
            
