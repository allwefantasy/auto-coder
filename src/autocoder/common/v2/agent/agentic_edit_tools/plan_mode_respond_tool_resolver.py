from typing import Dict, Any, Optional
import typing
from autocoder.common import AutoCoderArgs
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import PlanModeRespondTool, ToolResult # Import ToolResult from types
from loguru import logger

if typing.TYPE_CHECKING:
    from autocoder.common.v2.agent.agentic_edit import AgenticEdit

class PlanModeRespondToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticEdit'], tool: PlanModeRespondTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: PlanModeRespondTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        """
        Packages the response and options for Plan Mode interaction.
        """
        response_text = self.tool.response
        options = self.tool.options        
        logger.info(f"Resolving PlanModeRespondTool: Response='{response_text[:100]}...', Options={options}")

        if not response_text:
             return ToolResult(success=False, message="Error: Plan mode response cannot be empty.")

        # The actual presentation happens outside the resolver.
        result_content = {
            "response": response_text,
            "options": options
        }

        # Indicate success in preparing the plan mode response data
        return ToolResult(success=True, message="Plan mode response prepared.", content=result_content)
