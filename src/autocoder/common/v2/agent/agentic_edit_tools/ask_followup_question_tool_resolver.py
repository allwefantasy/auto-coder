from typing import Dict, Any, Optional
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import AskFollowupQuestionTool, ToolResult # Import ToolResult from types
from loguru import logger
import typing
from autocoder.common import AutoCoderArgs
from autocoder.run_context import get_run_context
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events import event_content as EventContentCreator
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from autocoder.common.result_manager import ResultManager
from autocoder.common.printer import Printer
if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit

class AskFollowupQuestionToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: AskFollowupQuestionTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: AskFollowupQuestionTool = tool # For type hinting
        self.result_manager = ResultManager()
        self.printer = Printer()

    def resolve(self) -> ToolResult:
        """
        Packages the question and options to be handled by the main loop/UI.
        This resolver doesn't directly ask the user but prepares the data for it.
        """
        question = self.tool.question
        options = self.tool.options or []
        options_text = "\n".join([f"{i+1}. {option}" for i, option in enumerate(options)])
        if get_run_context().is_web():
            answer = get_event_manager(
                self.args.event_file).ask_user(prompt=question)
            self.result_manager.append(content=answer + ("\n" + options_text if options_text else ""), meta={
                "action": "ask_user",
                "input": {
                    "question": question
                }
            })
            return ToolResult(success=True, message="Follow-up question prepared.", content=answer)

        console = Console()

        # 创建一个醒目的问题面板
        question_text = Text(question, style="bold cyan")
        question_panel = Panel(
            question_text,
            title="[bold yellow]auto-coder.chat's Question[/bold yellow]",
            border_style="blue",
            expand=False
        )

        # 显示问题面板
        console.print(question_panel)

        session = PromptSession(
            message=self.printer.get_message_from_key('tool_ask_user'))
        try:
            answer = session.prompt()
        except KeyboardInterrupt:
            answer = ""

        # The actual asking logic resides outside the resolver, typically in the agent's main loop
        # or UI interaction layer. The resolver's job is to validate and package the request.
        if not answer:
            return ToolResult(success=False, message="Error: Question not answered.")

        # Indicate success in preparing the question data
        return ToolResult(success=True, message="Follow-up question prepared.", content=answer)
