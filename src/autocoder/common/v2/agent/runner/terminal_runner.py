"""
TerminalRunner 提供在终端环境中运行代理的功能，支持格式化输出和交互式显示。

这个模块使用 Rich 库来提供格式化的终端输出，包括颜色、样式和布局。
它处理各种代理事件并以用户友好的方式在终端中显示。
"""

import os
import json
import time
import logging
from typing import Any, Dict, Optional, List

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax

from autocoder.common.auto_coder_lang import get_message
from autocoder.utils import llms as llm_utils
from autocoder.common.v2.agent.agentic_edit_types import (
    AgenticEditRequest, AgentEvent, CompletionEvent, 
    LLMOutputEvent, LLMThinkingEvent, ToolCallEvent, 
    ToolResultEvent, TokenUsageEvent, ErrorEvent,
    WindowLengthChangeEvent, ConversationIdEvent,
    PlanModeRespondEvent, SingleOutputMeta, AttemptCompletionTool
)
from .tool_display import get_tool_display_message
from .base_runner import BaseRunner

logger = logging.getLogger(__name__)

class TerminalRunner(BaseRunner):
    """
    在终端环境中运行代理，提供格式化输出和交互式显示。
    
    这个运行器使用 Rich 库来格式化终端输出，处理各种代理事件，
    并以用户友好的方式在终端中显示。
    """
    
    def run(self, request: AgenticEditRequest) -> None:
        """
        Runs the agentic edit process based on the request and displays
        the interaction streamingly in the terminal using Rich.
        """
        import json
        console = Console()
        project_name = os.path.basename(os.path.abspath(self.args.source_dir))

        if self.conversation_config.action == "list":
            conversations = self.agent.conversation_manager.list_conversations()
            # 只保留 conversation_id 和 name 字段
            filtered_conversations = []
            for conv in conversations:
                filtered_conv = {
                    "conversation_id": conv.get("conversation_id"),
                    "name": conv.get("name")
                }
                filtered_conversations.append(filtered_conv)
            
            # 格式化 JSON 输出，使用 JSON 格式渲染而不是 Markdown
            json_str = json.dumps(filtered_conversations, ensure_ascii=False, indent=4)
            console.print(Panel(json_str,
                                  title="🏁 Task Completion", border_style="green", title_align="left"))
            return
        

        if self.conversation_config.action == "new" and not request.user_input.strip():
            console.print(Panel(Markdown(f"New conversation created: {self.agent.conversation_manager.get_current_conversation_id()}"),
                                  title="🏁 Task Completion", border_style="green", title_align="left"))
            return

        console.rule(f"[bold cyan]Starting Agentic Edit: {project_name}[/]")
        console.print(Panel(
            f"[bold]{get_message('/agent/edit/user_query')}:[/bold]\n{request.user_input}", title=get_message("/agent/edit/objective"), border_style="blue"))

        # 用于累计TokenUsageEvent数据
        accumulated_token_usage = {
            "model_name": "",
            "input_tokens": 0,
            "output_tokens": 0,
            "input_cost": 0.0,
            "output_cost": 0.0
        }

        try:
            self.apply_pre_changes()
            event_stream = self.analyze(request)
            for event in event_stream:
                if isinstance(event, ConversationIdEvent):
                    console.print(f"[dim]Conversation ID: {event.conversation_id}[/dim]")
                    continue
                if isinstance(event, TokenUsageEvent):
                    last_meta: SingleOutputMeta = event.usage
                    # Get model info for pricing
                    model_name = ",".join(llm_utils.get_llm_names(self.llm))
                    model_info = llm_utils.get_model_info(
                        model_name, self.args.product_mode) or {}
                    input_price = model_info.get(
                        "input_price", 0.0) if model_info else 0.0
                    output_price = model_info.get(
                        "output_price", 0.0) if model_info else 0.0

                    # Calculate costs
                    input_cost = (last_meta.input_tokens_count *
                                  input_price) / 1000000  # Convert to millions
                    # Convert to millions
                    output_cost = (
                        last_meta.generated_tokens_count * output_price) / 1000000

                    # 添加日志记录
                    logger.info(f"Token Usage: Model={model_name}, Input Tokens={last_meta.input_tokens_count}, Output Tokens={last_meta.generated_tokens_count}, Input Cost=${input_cost:.6f}, Output Cost=${output_cost:.6f}")

                    # 累计token使用情况
                    accumulated_token_usage["model_name"] = model_name
                    accumulated_token_usage["input_tokens"] += last_meta.input_tokens_count
                    accumulated_token_usage["output_tokens"] += last_meta.generated_tokens_count
                    accumulated_token_usage["input_cost"] += input_cost
                    accumulated_token_usage["output_cost"] += output_cost
                    
                elif isinstance(event, WindowLengthChangeEvent):
                    # 显示当前会话的token数量
                    logger.info(f"当前会话总 tokens: {event.tokens_used}")
                    console.print(f"[dim]当前会话总 tokens: {event.tokens_used}[/dim]")
                    
                elif isinstance(event, LLMThinkingEvent):
                    # Render thinking within a less prominent style, maybe grey?
                    console.print(f"[grey50]{event.text}[/grey50]", end="")
                elif isinstance(event, LLMOutputEvent):
                    # Print regular LLM output, potentially as markdown if needed later
                    console.print(event.text, end="")
                elif isinstance(event, ToolCallEvent):
                    # Skip displaying AttemptCompletionTool's tool call
                    if isinstance(event.tool, AttemptCompletionTool):
                        continue  # Do not display AttemptCompletionTool tool call

                    tool_name = type(event.tool).__name__
                    # Use the new internationalized display function
                    display_content = get_tool_display_message(event.tool)
                    console.print(Panel(
                        display_content, title=f"🔧 Action: {tool_name}", border_style="blue", title_align="left"))
                    
                elif isinstance(event, ToolResultEvent):
                    # Skip displaying AttemptCompletionTool's result
                    if event.tool_name == "AttemptCompletionTool":
                        continue  # Do not display AttemptCompletionTool result

                    if event.tool_name == "PlanModeRespondTool":
                        continue

                    result = event.result
                    title = f"✅ Tool Result: {event.tool_name}" if result.success else f"❌ Tool Result: {event.tool_name}"
                    border_style = "green" if result.success else "red"
                    base_content = f"[bold]Status:[/bold] {'Success' if result.success else 'Failure'}\n"
                    base_content += f"[bold]Message:[/bold] {result.message}\n"

                    def _format_content(content):
                        if len(content) > 200:
                            return f"{content[:100]}\n...\n{content[-100:]}"
                        else:
                            return content

                    # Prepare panel for base info first
                    panel_content = [base_content]
                    syntax_content = None

                    if result.content is not None:
                        content_str = ""
                        try:
                            if isinstance(result.content, (dict, list)):
                                import json
                                content_str = json.dumps(
                                    result.content, indent=2, ensure_ascii=False)
                                syntax_content = Syntax(
                                    content_str, "json", theme="default", line_numbers=False)
                            elif isinstance(result.content, str) and ('\n' in result.content or result.content.strip().startswith('<')):
                                # Heuristic for code or XML/HTML
                                lexer = "python"  # Default guess
                                if event.tool_name == "ReadFileTool" and isinstance(event.result.message, str):
                                    # Try to guess lexer from file extension in message
                                    if ".py" in event.result.message:
                                        lexer = "python"
                                    elif ".js" in event.result.message:
                                        lexer = "javascript"
                                    elif ".ts" in event.result.message:
                                        lexer = "typescript"
                                    elif ".html" in event.result.message:
                                        lexer = "html"
                                    elif ".css" in event.result.message:
                                        lexer = "css"
                                    elif ".json" in event.result.message:
                                        lexer = "json"
                                    elif ".xml" in event.result.message:
                                        lexer = "xml"
                                    elif ".md" in event.result.message:
                                        lexer = "markdown"
                                    else:
                                        lexer = "text"  # Fallback lexer
                                elif event.tool_name == "ExecuteCommandTool":
                                    lexer = "shell"
                                else:
                                    lexer = "text"

                                syntax_content = Syntax(
                                    _format_content(result.content), lexer, theme="default", line_numbers=True)
                            else:
                                content_str = str(result.content)
                                # Append simple string content directly
                                panel_content.append(
                                    _format_content(content_str))
                        except Exception as e:
                            logger.warning(
                                f"Error formatting tool result content: {e}")
                            panel_content.append(
                                # Fallback
                                _format_content(str(result.content)))

                    # Print the base info panel
                    console.print(Panel("\n".join(
                        panel_content), title=title, border_style=border_style, title_align="left"))
                    # Print syntax highlighted content separately if it exists
                    if syntax_content:
                        console.print(syntax_content)
                            
                elif isinstance(event, PlanModeRespondEvent):
                    console.print(Panel(Markdown(event.completion.response),
                                  title="🏁 Task Completion", border_style="green", title_align="left"))

                elif isinstance(event, CompletionEvent):
                    # 在这里完成实际合并
                    try:
                        self.apply_changes()
                    except Exception as e:
                        logger.exception(
                            f"Error merging shadow changes to project: {e}")

                    console.print(Panel(Markdown(event.completion.result),
                                  title="🏁 Task Completion", border_style="green", title_align="left"))
                    if event.completion.command:
                        console.print(
                            f"[dim]Suggested command:[/dim] [bold cyan]{event.completion.command}[/]")
                elif isinstance(event, ErrorEvent):
                    console.print(Panel(
                        f"[bold red]Error:[/bold red] {event.message}", title="🔥 Error", border_style="red", title_align="left"))

                time.sleep(0.1)  # Small delay for better visual flow

            # 在处理完所有事件后打印累计的token使用情况
            if accumulated_token_usage["input_tokens"] > 0:
                self.printer.print_in_terminal(
                    "code_generation_complete",
                    duration=0.0,
                    input_tokens=accumulated_token_usage["input_tokens"],
                    output_tokens=accumulated_token_usage["output_tokens"],
                    input_cost=accumulated_token_usage["input_cost"],
                    output_cost=accumulated_token_usage["output_cost"],
                    speed=0.0,
                    model_names=accumulated_token_usage["model_name"],
                    sampling_count=1
                )
                
        except Exception as e:
            # 在处理异常时也打印累计的token使用情况
            if accumulated_token_usage["input_tokens"] > 0:
                self.printer.print_in_terminal(
                    "code_generation_complete",
                    duration=0.0,
                    input_tokens=accumulated_token_usage["input_tokens"],
                    output_tokens=accumulated_token_usage["output_tokens"],
                    input_cost=accumulated_token_usage["input_cost"],
                    output_cost=accumulated_token_usage["output_cost"],
                    speed=0.0,
                    model_names=accumulated_token_usage["model_name"],
                    sampling_count=1
                )
                
            logger.exception(
                "An unexpected error occurred during agent execution:")
            console.print(Panel(
                f"[bold red]FATAL ERROR:[/bold red]\n{str(e)}", title="🔥 System Error", border_style="red"))
            raise e
        finally:
            console.rule("[bold cyan]Agentic Edit Finished[/]")
