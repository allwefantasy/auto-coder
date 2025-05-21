import os
import subprocess
from typing import Dict, Any, Optional
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.agent.base_agentic.types import ExecuteCommandTool, ToolResult # Import ToolResult from types
from autocoder.common.printer import Printer
from loguru import logger
import typing
from autocoder.common import AutoCoderArgs
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.run_context import get_run_context
from autocoder.common.run_cmd import run_cmd_subprocess
if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent

class ExecuteCommandToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['BaseAgent'], tool: ExecuteCommandTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: ExecuteCommandTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        command = self.tool.command
        requires_approval = self.tool.requires_approval
        source_dir = self.args.source_dir or "."

        # Basic security check (can be expanded)
        if ";" in command or "&&" in command or "|" in command or "`" in command:
             # Allow && for cd chaining, but be cautious
             if not command.strip().startswith("cd ") and " && " in command:
                 pass # Allow cd chaining like 'cd subdir && command'
             else:
                return ToolResult(success=False, message=f"Command '{command}' contains potentially unsafe characters.")

        # Approval mechanism (simplified)
        if requires_approval:
             # In a real scenario, this would involve user interaction
             logger.info(f"Command requires approval: {command}")
             # For now, let's assume approval is granted in non-interactive mode or handled elsewhere
             pass

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
            
            exit_code, output = run_cmd_subprocess(command, verbose=True, cwd=source_dir)

            logger.info(f"Command executed: {command}")
            logger.info(f"Return Code: {exit_code}")
            if output:
                logger.info(f"Output:\n{output}")

            if exit_code == 0:
                return ToolResult(success=True, message="Command executed successfully.", content=output)
            else:
                error_message = f"Command failed with return code {exit_code}.\nOutput:\n{output}"
                return ToolResult(success=False, message=error_message, content={"output": output, "returncode": exit_code})

        except FileNotFoundError:
            return ToolResult(success=False, message=f"Error: The command '{command.split()[0]}' was not found. Please ensure it is installed and in the system's PATH.")
        except PermissionError:
            return ToolResult(success=False, message=f"Error: Permission denied when trying to execute '{command}'.")
        except Exception as e:
            logger.error(f"Error executing command '{command}': {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred while executing the command: {str(e)}")
