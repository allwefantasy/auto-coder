from typing import Optional
from autocoder.common import AutoCoderArgs
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.agent.base_agentic.types import BaseTool, ToolResult
from pydantic import BaseModel
import typing

if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent


# 首先定义工具模型
class ExampleTool(BaseTool):
    """示例工具，只是一个演示"""
    message: str
    times: int = 1


# 然后定义对应的解析器
class ExampleToolResolver(BaseToolResolver):
    """示例工具解析器"""
    def __init__(self, agent: Optional['BaseAgent'], tool: ExampleTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: ExampleTool = tool  # 类型提示

    def resolve(self) -> ToolResult:
        """
        执行工具逻辑

        Returns:
            工具执行结果
        """
        try:
            # 简单示例：重复消息N次
            result = self.tool.message * self.tool.times
            return ToolResult(
                success=True,
                message="成功执行示例工具",
                content=result
            )
        except Exception as e:
            return ToolResult(
                success=False,
                message=f"执行示例工具时出错: {str(e)}",
                content=None
            ) 