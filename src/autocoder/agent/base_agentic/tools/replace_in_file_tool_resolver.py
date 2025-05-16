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
from autocoder.common.file_checkpoint.models import FileChange as CheckpointFileChange
from autocoder.common.file_checkpoint.manager import FileChangeManager as CheckpointFileChangeManager
from autocoder.linters.models import IssueSeverity, FileLintResult
if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent

class ReplaceInFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['BaseAgent'], tool: ReplaceInFileTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: ReplaceInFileTool = tool  # For type hinting
        self.args = args
        self.shadow_manager = self.agent.shadow_manager if self.agent else None
        self.shadow_linter = self.agent.shadow_linter if self.agent else None

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

    def _filter_lint_issues(self, lint_result:FileLintResult, levels: List[IssueSeverity] = [IssueSeverity.ERROR, IssueSeverity.WARNING]):
        """
        过滤 lint 结果，只保留指定级别的问题
        
        参数:
            lint_result: 单个文件的 lint 结果对象
            levels: 要保留的问题级别列表，默认保留 ERROR 和 WARNING 级别
            
        返回:
            过滤后的 lint 结果对象（原对象的副本）
        """
        if not lint_result or not lint_result.issues:
            return lint_result
            
        # 创建一个新的 issues 列表，只包含指定级别的问题
        filtered_issues = []
        for issue in lint_result.issues:
            if issue.severity in levels:                
                filtered_issues.append(issue)
                
        # 更新 lint_result 的副本
        filtered_result = lint_result
        filtered_result.issues = filtered_issues
        
        # 更新计数
        filtered_result.error_count = sum(1 for issue in filtered_result.issues if issue.severity == IssueSeverity.ERROR)
        filtered_result.warning_count = sum(1 for issue in filtered_result.issues if issue.severity == IssueSeverity.WARNING)
        filtered_result.info_count = sum(1 for issue in filtered_result.issues if issue.severity == IssueSeverity.INFO)
        
        return filtered_result
        
    def _format_lint_issues(self, lint_result:FileLintResult):
        """
        将 lint 结果格式化为可读的文本格式
        
        参数:
            lint_result: 单个文件的 lint 结果对象
            
        返回:
            str: 格式化的问题描述
        """
        formatted_issues = []
        
        for issue in lint_result.issues:
            severity = "错误" if issue.severity.value == 3 else "警告" if issue.severity.value == 2 else "信息"
            line_info = f"第{issue.position.line}行"
            if issue.position.column:
                line_info += f", 第{issue.position.column}列"
            
            formatted_issues.append(
                f"  - [{severity}] {line_info}: {issue.message} (规则: {issue.code})"
            )
        
        return "\n".join(formatted_issues)

    

    def replace_in_file_normal(self, file_path: str, diff_content: str, source_dir: str, abs_project_dir: str, abs_file_path: str) -> ToolResult:
        """Replace content in file directly without using shadow manager"""
        try:
            # Read original content
            if not os.path.exists(abs_file_path):
                return ToolResult(success=False, message=get_message_with_format("replace_in_file.file_not_found", file_path=file_path))
            if not os.path.isfile(abs_file_path):
                return ToolResult(success=False, message=get_message_with_format("replace_in_file.not_a_file", file_path=file_path))

            with open(abs_file_path, 'r', encoding='utf-8', errors='replace') as f:
                original_content = f.read()

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

            if applied_count == 0 and errors:
                return ToolResult(success=False, message=get_message_with_format("replace_in_file.apply_failed", errors="\n".join(errors)))

            # Write the modified content back to file
            if self.agent and self.agent.checkpoint_manager:
                changes = {
                    file_path: CheckpointFileChange(
                        file_path=file_path,
                        content=current_content,
                        is_deletion=False,
                        is_new=True
                    )
                }
                change_group_id = self.args.event_file
                
                self.agent.checkpoint_manager.apply_changes_with_conversation(
                            changes=changes,
                            conversations=self.agent.current_conversations,
                            change_group_id=change_group_id,
                            metadata={"event_file": self.args.event_file}
                        )                                
            else:
                with open(abs_file_path, 'w', encoding='utf-8') as f:
                    f.write(current_content)
            
            logger.info(f"Successfully applied {applied_count}/{len(parsed_blocks)} changes to file: {file_path}")

            # 新增：执行代码质量检查
            lint_results = None
            lint_message = ""
            formatted_issues = ""
            has_lint_issues = False
            
            # 检查是否启用了Lint功能
            enable_lint = self.args.enable_auto_fix_lint
            logger.info(f"检查Lint功能状态: enable_lint={enable_lint}")
            
            if enable_lint:
                try:
                    if self.agent.linter:
                        lint_results = self.agent.linter.lint_file(file_path)
                        if lint_results and lint_results.issues:
                            # 过滤 lint 结果，只保留 ERROR 和 WARNING 级别的问题
                            filtered_results = self._filter_lint_issues(lint_results)
                            if filtered_results.issues:
                                has_lint_issues = True
                                # 格式化 lint 问题
                                formatted_issues = self._format_lint_issues(filtered_results)
                                lint_message = f"\n\n代码质量检查发现 {len(filtered_results.issues)} 个问题"
                except Exception as e:
                    logger.error(f"Lint 检查失败: {str(e)}")
                    lint_message = "\n\n尝试进行代码质量检查时出错。"
            else:
                logger.info("代码质量检查已禁用")

            # 构建包含 lint 结果的返回消息
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
                        
            # 附加 lint 结果到返回内容
            result_content = {
                "content": current_content,
            }
            
            # 只有在启用Lint时才添加Lint结果
            if enable_lint:
                message = message + "\n" + lint_message
                result_content["lint_results"] = {
                    "has_issues": has_lint_issues,
                    "issues": formatted_issues if has_lint_issues else None
                }

            return ToolResult(success=True, message=message, content=result_content)
        except Exception as e:
            logger.error(f"Error writing replaced content to file '{file_path}': {str(e)}")
            return ToolResult(success=False, message=get_message_with_format("replace_in_file.write_error", error=str(e)))

    def resolve(self) -> ToolResult:
        """Resolve the replace in file tool by calling the appropriate implementation"""
        file_path = self.tool.path
        diff_content = self.tool.diff
        source_dir = self.args.source_dir or "."
        abs_project_dir = os.path.abspath(source_dir)
        abs_file_path = os.path.abspath(os.path.join(source_dir, file_path))

        # Security check
        if not abs_file_path.startswith(abs_project_dir):
            return ToolResult(success=False, message=get_message_with_format("replace_in_file.access_denied", file_path=file_path))
                
        return self.replace_in_file_normal(file_path, diff_content, source_dir, abs_project_dir, abs_file_path)
