from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from autocoder.agent.agentic_edit_types import BaseTool
class ToolResult:
    def __init__(self, success: bool, message: str, content: Any = None):
        self.success = success
        self.message = message
        self.content = content # Can store file content, command output, etc.

    def __str__(self):
        return f"Success: {self.success}, Message: {self.message}"

class BaseToolResolver(ABC):
    def __init__(self, agent: Optional[Any], tool: BaseTool, args: Dict[str, Any]):
        """
        Initializes the resolver.

        Args:
            agent: The AutoCoder agent instance.
            tool: The Pydantic model instance representing the tool call.
            args: Additional arguments needed for execution (e.g., source_dir).
        """
        self.agent = agent
        self.tool = tool
        self.args = args

    @abstractmethod
    def resolve(self) -> ToolResult:
        """
        Executes the tool's logic.

        Returns:
            A ToolResult object indicating success or failure and a message.
        """
        pass
