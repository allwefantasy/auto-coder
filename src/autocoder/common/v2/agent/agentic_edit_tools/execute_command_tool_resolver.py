import subprocess
import os
from typing import Dict, Any, Optional
from autocoder.common.run_cmd import run_cmd_subprocess
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import ExecuteCommandTool, ToolResult # Import ToolResult from types
from autocoder.common.v2.agent.agentic_edit_tools.dangerous_command_checker import DangerousCommandChecker
from autocoder.common import shells
from autocoder.common.printer import Printer
from loguru import logger
import typing   
from autocoder.common.context_pruner import PruneContext
from autocoder.rag.token_counter import count_tokens
from autocoder.common import SourceCode
from autocoder.common import AutoCoderArgs
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.run_context import get_run_context
if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit

class ExecuteCommandToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: ExecuteCommandTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: ExecuteCommandTool = tool # For type hinting
        self.context_pruner = PruneContext(
            max_tokens=self.args.context_prune_safe_zone_tokens,
            args=self.args,
            llm=self.agent.context_prune_llm
        )
        # 初始化危险命令检查器
        self.danger_checker = DangerousCommandChecker()

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

    def resolve(self) -> ToolResult:        
        command = self.tool.command
        requires_approval = self.tool.requires_approval
        source_dir = self.args.source_dir or "."
        
        if self.args.enable_agentic_dangerous_command_check:
            # 使用新的危险命令检查器进行安全检查
            is_safe, danger_reason = self.danger_checker.check_command_safety(command, allow_whitelist_bypass=True)
            
            if not is_safe:
                # 获取安全建议
                recommendations = self.danger_checker.get_safety_recommendations(command)
                
                error_message = f"检测到危险命令: {danger_reason}"
                if recommendations:
                    error_message += f"\n安全建议:\n" + "\n".join(f"- {rec}" for rec in recommendations)
                
                logger.warning(f"阻止执行危险命令: {command}, 原因: {danger_reason}")
                return ToolResult(success=False, message=error_message)

        # Approval mechanism (simplified)
        if not self.args.enable_agentic_auto_approve and requires_approval:
            logger.info(f"Executing command: {command} in {os.path.abspath(source_dir)}")
            try:            
                # 使用封装的run_cmd方法执行命令
                if get_run_context().is_web():
                    answer = get_event_manager(
                        self.args.event_file).ask_user(prompt=f"Allow to execute the `{command}`?",options=["yes","no"])
                    if answer == "yes":
                        pass
                    else:
                        return ToolResult(success=False, message=f"Command '{command}' execution denied by user.")
            except Exception as e:
                logger.error(f"Error when ask the user to approve the command '{command}': {str(e)}")
                return ToolResult(success=False, message=f"An unexpected error occurred while asking the user to approve the command: {str(e)}")
                
        try:    
            exit_code, output = run_cmd_subprocess(command, verbose=True, cwd=source_dir)

            logger.info(f"Command executed: {command}")
            logger.info(f"Return Code: {exit_code}")
            if output:
                logger.info(f"Original Output (length: {len(output)} chars)") # Avoid logging potentially huge output directly

            final_output = self._prune_file_content(output, "command_output")

            if exit_code == 0:
                return ToolResult(success=True, message="Command executed successfully.", content=final_output)
            else:
                # For the human-readable error message, we might prefer the original full output.
                # For the agent-consumable content, we provide the (potentially pruned) final_output.
                error_message_for_human = f"Command failed with return code {exit_code}.\nOutput:\n{output}"
                return ToolResult(success=False, message=error_message_for_human, content={"output": final_output, "returncode": exit_code})

        except FileNotFoundError:
            return ToolResult(success=False, message=f"Error: The command '{command.split()[0]}' was not found. Please ensure it is installed and in the system's PATH.")
        except PermissionError:
            return ToolResult(success=False, message=f"Error: Permission denied when trying to execute '{command}'.")
        except Exception as e:
            logger.error(f"Error executing command '{command}': {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred while executing the command: {str(e)}")
