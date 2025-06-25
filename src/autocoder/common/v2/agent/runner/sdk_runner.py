"""
SdkRunner 提供生成器接口，适用于SDK环境下的代理运行。

这个模块提供了一个简单的生成器接口，允许外部代码迭代处理代理事件。
它是三种运行模式中最轻量级的一种，适合集成到其他应用程序中。
"""

import logging
from typing import Generator, Any

from autocoder.common.v2.agent.agentic_edit_types import (
    AgenticEditRequest, AgentEvent, CompletionEvent
)
from .base_runner import BaseRunner

logger = logging.getLogger(__name__)

class SdkRunner(BaseRunner):
    """
    提供生成器接口的代理运行器，适用于SDK环境。
    
    这个运行器返回一个事件生成器，允许外部代码迭代处理代理事件。
    它是三种运行模式中最轻量级的一种，适合集成到其他应用程序中。
    """
    
    def run(self, request: AgenticEditRequest) -> Generator[AgentEvent, None, None]:
        """
        Runs the agentic edit process and yields events for external processing.
        """
        try:
            event_stream = self.analyze(request)
            for agent_event in event_stream:
                if isinstance(agent_event, CompletionEvent):
                    self.apply_changes()
                yield agent_event
                
        except Exception as e:
            logger.exception(
                "An unexpected error occurred during agent execution: {e}")           
            raise e
