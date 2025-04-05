import subprocess
import os
from typing import Dict, Any, Optional
from .base_tool_resolver import BaseToolResolver
from autocoder.agent.agentic_edit_types import ExecuteCommandTool, ToolResult # Import ToolResult from types
from autocoder.common import shells
from autocoder.common.printer import Printer
from loguru import logger


class ExecuteCommandToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional[Any], tool: ExecuteCommandTool, args: Dict[str, Any]):
        super().__init__(agent, tool, args)
        self.tool: ExecuteCommandTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        printer = Printer()
        command = self.tool.command
        requires_approval = self.tool.requires_approval
        source_dir = self.args.get("source_dir", ".")

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
             printer.print_warning(f"Command requires approval: {command}")
             # For now, let's assume approval is granted in non-interactive mode or handled elsewhere
             pass

        printer.print_message(f"Executing command: {command} in {os.path.abspath(source_dir)}")
        try:
            # Determine shell based on OS
            shell = True
            executable = None
            if shells.is_windows():
                # Decide between cmd and powershell if needed, default is cmd
                pass # shell=True uses default shell
            else:
                # Use bash or zsh? Default is usually fine.
                pass # shell=True uses default shell

            # Execute the command
            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=source_dir,
                text=True,
                encoding=shells.get_terminal_encoding(),
                errors='replace' # Handle potential decoding errors
            )

            stdout, stderr = process.communicate()
            returncode = process.returncode

            logger.info(f"Command executed: {command}")
            logger.info(f"Return Code: {returncode}")
            if stdout:
                logger.info(f"stdout:\n{stdout}")
            if stderr:
                logger.info(f"stderr:\n{stderr}")


            if returncode == 0:
                return ToolResult(success=True, message="Command executed successfully.", content=stdout)
            else:
                error_message = f"Command failed with return code {returncode}.\nStderr:\n{stderr}\nStdout:\n{stdout}"
                return ToolResult(success=False, message=error_message, content={"stdout": stdout, "stderr": stderr, "returncode": returncode})

        except FileNotFoundError:
            return ToolResult(success=False, message=f"Error: The command '{command.split()[0]}' was not found. Please ensure it is installed and in the system's PATH.")
        except PermissionError:
            return ToolResult(success=False, message=f"Error: Permission denied when trying to execute '{command}'.")
        except Exception as e:
            logger.error(f"Error executing command '{command}': {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred while executing the command: {str(e)}")
