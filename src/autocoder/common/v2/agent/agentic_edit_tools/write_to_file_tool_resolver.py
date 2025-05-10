import os
from typing import Dict, Any, Optional
from autocoder.common.v2.agent.agentic_edit_types import WriteToFileTool, ToolResult
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from loguru import logger
from autocoder.common import AutoCoderArgs
from autocoder.common.auto_coder_lang import get_message_with_format
from autocoder.common.file_checkpoint.models import FileChange as CheckpointFileChange
from autocoder.common.file_checkpoint.manager import FileChangeManager as CheckpointFileChangeManager
import typing

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit

class WriteToFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: WriteToFileTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: WriteToFileTool = tool  # For type hinting
        self.args = args
        self.shadow_manager = self.agent.shadow_manager if self.agent else None
        self.shadow_linter = self.agent.shadow_linter if self.agent else None
        
    def _format_lint_issues(self, lint_result):
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

    def write_file_with_shadow(self, file_path: str, content: str, source_dir: str, abs_project_dir: str, abs_file_path: str) -> ToolResult:
        """Write file using shadow manager for path translation"""
        try:
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
            
            # 新增：执行代码质量检查
            lint_results = None
            lint_message = ""
            formatted_issues = ""
            has_lint_issues = False
            
            # 检查是否启用了Lint功能
            enable_lint = self.args.enable_auto_fix_lint
            
            if enable_lint:
                try:
                    if self.shadow_linter and self.shadow_manager:
                        # 对新创建的文件进行 lint 检查
                        shadow_path = self.shadow_manager.to_shadow_path(abs_file_path)
                        lint_results = self.shadow_linter.lint_shadow_file(shadow_path)
                        
                        if lint_results and lint_results.issues:
                            has_lint_issues = True
                            # 格式化 lint 问题
                            formatted_issues = self._format_lint_issues(lint_results)
                            lint_message = f"\n\n代码质量检查发现 {len(lint_results.issues)} 个问题:\n{formatted_issues}"
                        else:
                            lint_message = "\n\n代码质量检查通过，未发现问题。"
                except Exception as e:
                    logger.error(f"Lint 检查失败: {str(e)}")
                    lint_message = "\n\n尝试进行代码质量检查时出错。"
            else:
                logger.info("代码质量检查已禁用")
            
            # 构建包含 lint 结果的返回消息
            message = f"Successfully wrote to file (shadow): {file_path}"
            
            # 将 lint 消息添加到结果中，如果启用了Lint
            if enable_lint:
                message += lint_message
            
            # 附加 lint 结果到返回内容
            result_content = {
                "content": content,
            }
            
            # 只有在启用Lint时才添加Lint结果
            if enable_lint:
                result_content["lint_results"] = {
                    "has_issues": has_lint_issues,
                    "issues": formatted_issues if has_lint_issues else None
                }
            
            return ToolResult(success=True, message=message, content=result_content)
        except Exception as e:
            logger.error(f"Error writing to shadow file '{file_path}': {str(e)}")
            return ToolResult(success=False, message=f"An error occurred while writing to the shadow file: {str(e)}")

    def write_file_normal(self, file_path: str, content: str, source_dir: str, abs_project_dir: str, abs_file_path: str) -> ToolResult:
        """Write file directly without using shadow manager"""
        try:
            os.makedirs(os.path.dirname(abs_file_path), exist_ok=True)            

            if self.agent:
                rel_path = os.path.relpath(abs_file_path, abs_project_dir)
                self.agent.record_file_change(rel_path, "added", diff=None, content=content)

            if self.agent and self.agent.checkpoint_manager:
                changes = {
                    file_path: CheckpointFileChange(
                        file_path=file_path,
                        content=content,
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
                    f.write(content)
            logger.info(f"Successfully wrote to file: {file_path}")    
            
            # 新增：执行代码质量检查
            lint_results = None
            lint_message = ""
            formatted_issues = ""
            has_lint_issues = False
            
            # 检查是否启用了Lint功能
            enable_lint = self.args.enable_auto_fix_lint
            
            if enable_lint:
                try:
                    if self.shadow_linter and self.shadow_manager:
                        # 对新创建的文件进行 lint 检查
                        # 由于没有shadow系统，需要先创建shadow文件
                        shadow_path = self.shadow_manager.to_shadow_path(abs_file_path)
                        os.makedirs(os.path.dirname(shadow_path), exist_ok=True)
                        with open(shadow_path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        
                        lint_results = self.shadow_linter.lint_shadow_file(shadow_path)
                        
                        if lint_results and lint_results.issues:
                            has_lint_issues = True
                            # 格式化 lint 问题
                            formatted_issues = self._format_lint_issues(lint_results)
                            lint_message = f"\n\n代码质量检查发现 {len(lint_results.issues)} 个问题:\n{formatted_issues}"
                        else:
                            lint_message = "\n\n代码质量检查通过，未发现问题。"
                    if self.agent.linter:
                        lint_results = self.agent.linter.lint_file(file_path)
                        if lint_results and lint_results.issues:
                            has_lint_issues = True
                            # 格式化 lint 问题
                            formatted_issues = self._format_lint_issues(lint_results)
                            lint_message = f"\n\n代码质量检查发现 {len(lint_results.issues)} 个问题:\n{formatted_issues}"
                except Exception as e:
                    logger.error(f"Lint 检查失败: {str(e)}")
                    lint_message = "\n\n尝试进行代码质量检查时出错。"
            else:
                logger.info("代码质量检查已禁用")
            
            # 构建包含 lint 结果的返回消息
            message = f"{file_path}"
            
            # 将 lint 消息添加到结果中，如果启用了Lint
            if enable_lint:
                message += lint_message
            
            # 附加 lint 结果到返回内容
            result_content = {
                "content": content,
            }
            
            # 只有在启用Lint时才添加Lint结果
            if enable_lint:
                result_content["lint_results"] = {
                    "has_issues": has_lint_issues,
                    "issues": formatted_issues if has_lint_issues else None
                }
            
            return ToolResult(success=True, message=message, content=result_content)
        except Exception as e:
            logger.error(f"Error writing to file '{file_path}': {str(e)}")
            return ToolResult(success=False, message=f"An error occurred while writing to the file: {str(e)}")

    def resolve(self) -> ToolResult:
        """Resolve the write file tool by calling the appropriate implementation"""
        file_path = self.tool.path
        content = self.tool.content
        source_dir = self.args.source_dir or "."
        abs_project_dir = os.path.abspath(source_dir)
        abs_file_path = os.path.abspath(os.path.join(source_dir, file_path))

        # Security check: ensure the path is within the source directory
        if not abs_file_path.startswith(abs_project_dir):
            return ToolResult(success=False, message=f"Error: Access denied. Attempted to write file outside the project directory: {file_path}")

        # Choose the appropriate implementation based on whether shadow_manager is available
        if self.shadow_manager:
            return self.write_file_with_shadow(file_path, content, source_dir, abs_project_dir, abs_file_path)
        else:
            return self.write_file_normal(file_path, content, source_dir, abs_project_dir, abs_file_path)