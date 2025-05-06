import os
import re
import difflib
import traceback
from typing import Dict, Any, Optional, List, Tuple
import typing
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.agent.base_agentic.types import ReplaceInFileTool, ToolResult  # Import ToolResult from types
from autocoder.common.printer import Printer
from autocoder.common import AutoCoderArgs
from loguru import logger
from autocoder.common.auto_coder_lang import get_message_with_format
if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent

class ReplaceInFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['BaseAgent'], tool: ReplaceInFileTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: ReplaceInFileTool = tool  # For type hinting
        self.shadow_manager = self.agent.shadow_manager if self.agent else None

    def parse_diff(self, diff_content: str) -> List[Tuple[str, str]]:
        """
        Parses the diff content into a list of (search_block, replace_block) tuples.
        """
        blocks = []
        lines = diff_content.splitlines(keepends=True)
        i = 0
        n = len(lines)

        while i < n:
            line = lines[i]
            if line.strip() == "<<<<<<< SEARCH":
                i += 1
                search_lines = []
                # Accumulate search block
                while i < n and lines[i].strip() != "=======":
                    search_lines.append(lines[i])
                    i += 1
                if i >= n:
                    logger.warning("Unterminated SEARCH block found in diff content.")
                    break
                i += 1  # skip '======='
                replace_lines = []
                # Accumulate replace block
                while i < n and lines[i].strip() != ">>>>>>> REPLACE":
                    replace_lines.append(lines[i])
                    i += 1
                if i >= n:
                    logger.warning("Unterminated REPLACE block found in diff content.")
                    break
                i += 1  # skip '>>>>>>> REPLACE'

                search_block = ''.join(search_lines)
                replace_block = ''.join(replace_lines)
                blocks.append((search_block, replace_block))
            else:
                i += 1

        if not blocks and diff_content.strip():
            logger.warning(f"Could not parse any SEARCH/REPLACE blocks from diff: {diff_content}")
        return blocks

    def resolve(self) -> ToolResult:
        file_path = self.tool.path
        diff_content = self.tool.diff
        source_dir = self.args.source_dir or "."
        abs_project_dir = os.path.abspath(source_dir)
        abs_file_path = os.path.abspath(os.path.join(source_dir, file_path))

        # Security check
        if not abs_file_path.startswith(abs_project_dir):
            return ToolResult(success=False, message=get_message_with_format("replace_in_file.access_denied", file_path=file_path))

        # Determine target path: shadow file if shadow_manager exists
        target_path = abs_file_path
        if self.shadow_manager:
            target_path = self.shadow_manager.to_shadow_path(abs_file_path)

        # If shadow file does not exist yet, but original file exists, copy original content into shadow first? No, just treat as normal file.
        # For now, read from shadow if exists, else fallback to original file
        try:
            if os.path.exists(target_path) and os.path.isfile(target_path):
                with open(target_path, 'r', encoding='utf-8', errors='replace') as f:
                    original_content = f.read()
            elif self.shadow_manager and os.path.exists(abs_file_path) and os.path.isfile(abs_file_path):
                # If shadow doesn't exist, but original exists, read original content (create shadow implicitly later)
                with open(abs_file_path, 'r', encoding='utf-8', errors='replace') as f:
                    original_content = f.read()
                # create parent dirs of shadow if needed
                os.makedirs(os.path.dirname(target_path), exist_ok=True)
                # write original content into shadow file as baseline
                with open(target_path, 'w', encoding='utf-8') as f:
                    f.write(original_content)
                logger.info(f"[Shadow] Initialized shadow file from original: {target_path}")
            else:
                return ToolResult(success=False, message=get_message_with_format("replace_in_file.file_not_found", file_path=file_path))
        except Exception as e:
            logger.error(f"Error reading file for replace '{file_path}': {str(e)}")
            return ToolResult(success=False, message=get_message_with_format("replace_in_file.read_error", error=str(e)))

        parsed_blocks = self.parse_diff(diff_content)
        if not parsed_blocks:
            return ToolResult(success=False, message=get_message_with_format("replace_in_file.no_valid_blocks"))

        current_content = original_content
        applied_count = 0
        errors = []

        # Apply blocks sequentially
        for i, (search_block, replace_block) in enumerate(parsed_blocks):
            start_index = current_content.find(search_block)

            if start_index != -1:
                current_content = current_content[:start_index] + replace_block + current_content[start_index + len(search_block):]
                applied_count += 1
                logger.info(f"Applied SEARCH/REPLACE block {i+1} in file {file_path}")
            else:
                error_message = f"SEARCH block {i+1} not found in the current file content. Content to search:\n---\n{search_block}\n---"
                logger.warning(error_message)
                context_start = max(0, original_content.find(search_block[:20]) - 100)
                context_end = min(len(original_content), context_start + 200 + len(search_block[:20]))
                logger.warning(f"Approximate context in file:\n---\n{original_content[context_start:context_end]}\n---")
                errors.append(error_message)
                # continue applying remaining blocks

        if applied_count == 0 and errors:
            return ToolResult(success=False, message=get_message_with_format("replace_in_file.apply_failed", errors="\n".join(errors)))

        try:
            os.makedirs(os.path.dirname(target_path), exist_ok=True)
            with open(target_path, 'w', encoding='utf-8') as f:
                f.write(current_content)
            logger.info(f"Successfully applied {applied_count}/{len(parsed_blocks)} changes to file: {file_path}")

            if errors:
                message = get_message_with_format("replace_in_file.apply_success_with_warnings", 
                                                  applied=applied_count, 
                                                  total=len(parsed_blocks), 
                                                  file_path=file_path,
                                                  errors="\n".join(errors))
            else:
                message = get_message_with_format("replace_in_file.apply_success", 
                                                  applied=applied_count, 
                                                  total=len(parsed_blocks), 
                                                  file_path=file_path)

            # 变更跟踪，回调AgenticEdit
            if self.agent:
                rel_path = os.path.relpath(abs_file_path, abs_project_dir)
                self.agent.record_file_change(rel_path, "modified", diff=diff_content, content=current_content)

            return ToolResult(success=True, message=message, content=current_content)
        except Exception as e:
            logger.error(f"Error writing replaced content to file '{file_path}': {str(e)}")
            return ToolResult(success=False, message=get_message_with_format("replace_in_file.write_error", error=str(e)))
