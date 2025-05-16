import os
from typing import Dict, Any, Optional,List
from autocoder.agent.base_agentic.types import WriteToFileTool, ToolResult  # Import ToolResult from types
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from loguru import logger
from autocoder.common import AutoCoderArgs
from autocoder.common.file_checkpoint.models import FileChange as CheckpointFileChange
from autocoder.common.file_checkpoint.manager import FileChangeManager as CheckpointFileChangeManager
from autocoder.linters.models import IssueSeverity, FileLintResult
import typing

if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent

class WriteToFileToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['BaseAgent'], tool: WriteToFileTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: WriteToFileTool = tool  # For type hinting
        self.args = args
        self.shadow_manager = self.agent.shadow_manager if self.agent else None
        self.shadow_linter = self.agent.shadow_linter if self.agent else None
        
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
        filtered_result.error_count = sum(1 for issue in filtered_issues if issue.severity == IssueSeverity.ERROR)
        filtered_result.warning_count = sum(1 for issue in filtered_issues if issue.severity == IssueSeverity.WARNING)
        filtered_result.info_count = sum(1 for issue in filtered_issues if issue.severity == IssueSeverity.INFO)
        
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
            message = f"{file_path}"
                        
            
            # 附加 lint 结果到返回内容
            result_content = {
                "content": content,
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
                
        return self.write_file_normal(file_path, content, source_dir, abs_project_dir, abs_file_path)