from typing import Dict, Any, Optional
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import AskFollowupQuestionTool, ToolResult # Import ToolResult from types
from loguru import logger
import typing
from autocoder.common import AutoCoderArgs

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit

class AskFollowupQuestionToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: AskFollowupQuestionTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: AskFollowupQuestionTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        """
        Packages the question and options to be handled by the main loop/UI.
        This resolver doesn't directly ask the user but prepares the data for it.
        """
        question = self.tool.question
        options = self.tool.options

        logger.info(f"Resolving AskFollowupQuestionTool: Question='{question}', Options={options}")

        # The actual asking logic resides outside the resolver, typically in the agent's main loop
        # or UI interaction layer. The resolver's job is to validate and package the request.
        if not question:
            return ToolResult(success=False, message="Error: Question cannot be empty.")

        result_content = {
            "question": question,
            "options": options
        }

        # Indicate success in preparing the question data
        return ToolResult(success=True, message="Follow-up question prepared.", content=result_content)
