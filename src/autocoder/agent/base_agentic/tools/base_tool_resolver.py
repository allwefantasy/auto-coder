from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, TYPE_CHECKING
from autocoder.common import AutoCoderArgs

if TYPE_CHECKING:
    from autocoder.agent.base_agentic.base_agent import BaseAgent
    from autocoder.agent.base_agentic.types import BaseTool, ToolResult


class BaseToolResolver(ABC):
    """
    工具解析器的基类，所有工具解析器都应该继承此类
    """
    def __init__(self, agent: Optional['BaseAgent'], tool: 'BaseTool', args: AutoCoderArgs):
        """
        初始化解析器

        Args:
            agent: 代理实例，可能为None
            tool: 工具实例
            args: 其他需要的参数，如项目目录等
        """
        self.agent = agent
        self.tool = tool
        self.args = args

    @abstractmethod
    def resolve(self) -> 'ToolResult':
        """
        执行工具逻辑，返回结果

        Returns:
            ToolResult对象，表示成功或失败以及消息
        """
        pass 