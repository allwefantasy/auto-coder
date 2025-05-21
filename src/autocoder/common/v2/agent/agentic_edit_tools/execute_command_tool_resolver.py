import subprocess
import os
from typing import Dict, Any, Optional
from autocoder.common.run_cmd import run_cmd_subprocess
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import ExecuteCommandTool, ToolResult # Import ToolResult from types
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
        if self.agent and hasattr(self.agent, 'llm') and self.agent.llm and self.args:
            self.context_pruner = PruneContext(max_tokens=self.args.max_input_tokens, args=self.args, llm=self.agent.llm)
        else:
            self.context_pruner = None
            logger.warning("Agent, LLM, or args not fully available for PruneContext initialization in ExecuteCommandToolResolver. Command output pruning will be disabled.")

    def resolve(self) -> ToolResult:
        printer = Printer()
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
             printer.print_str_in_terminal(f"Command requires approval: {command}")
             # For now, let's assume approval is granted in non-interactive mode or handled elsewhere
             pass

        printer.print_str_in_terminal(f"Executing command: {command} in {os.path.abspath(source_dir)}")
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
                logger.info(f"Original Output (length: {len(output)} chars)") # Avoid logging potentially huge output directly

            final_output = output  # Initialize with original output

            if self.context_pruner and output and isinstance(output, str) and output.strip():
                output_source = SourceCode(module_name="command_output", source_code=output)
                current_tokens = count_tokens(output)
                max_tokens_for_output = self.context_pruner.max_tokens

                if current_tokens > max_tokens_for_output:
                    printer.print_in_terminal(
                        "command_output_pruning_needed",
                        tokens=current_tokens,
                        max_tokens=max_tokens_for_output,
                    )
                    try:
                        conversations_for_pruning = []
                        if self.agent and hasattr(self.agent, 'conversations'):
                            conversations_for_pruning = self.agent.conversations
                        
                        pruned_sources = self.context_pruner.handle_overflow(
                            file_sources=[output_source],
                            conversations=conversations_for_pruning,
                            strategy=self.args.context_prune_strategy if self.args.context_prune_strategy else "score"
                        )
                        if pruned_sources and pruned_sources[0].source_code is not None:
                            final_output = pruned_sources[0].source_code
                            pruned_token_count = count_tokens(final_output)
                            printer.print_in_terminal(
                                "command_output_pruned",
                                original_tokens=current_tokens,
                                pruned_tokens=pruned_token_count,
                            )
                            logger.info(f"Command output pruned. Original tokens: {current_tokens}, Pruned tokens: {pruned_token_count}")
                        else:
                            final_output = "Command output was too large and pruned, resulting in no content or an issue during pruning."
                            printer.print_in_terminal(
                                "command_output_pruned_empty",
                                original_tokens=current_tokens,
                            )
                            logger.warning(f"Command output pruned from {current_tokens} tokens, resulting in empty or problematic content.")
                    except Exception as e:
                        # final_output remains original output on error
                        printer.print_in_terminal(
                            "command_output_pruning_error",
                            error_message=str(e)
                        )
                        logger.error(f"Error during command output pruning: {str(e)}. Using original output.")
                        logger.exception(e)
                else:
                    if output and isinstance(output, str) and output.strip(): # Log only if there was actual content
                        logger.info(f"Command output ({current_tokens} tokens) is within limits ({max_tokens_for_output} tokens).")
            elif not self.context_pruner:
                logger.info("Context pruner not available for command output. Pruning skipped.")
            elif not (output and isinstance(output, str) and output.strip()):
                logger.info("No command output or output is not a non-empty string. Pruning skipped.")


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
