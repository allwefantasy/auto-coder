"""
Runner 模块提供了多种运行模式，用于在不同环境下执行 AgenticEdit 代理。

这个模块包含三种主要的运行器:
1. TerminalRunner: 在终端环境中运行代理，提供格式化输出
2. EventRunner: 将代理事件转换为标准事件系统格式
3. SdkRunner: 提供生成器接口，适用于SDK环境

使用示例:
```python
from autocoder.common.v2.agent.runner import TerminalRunner
from autocoder.common.v2.agent.agentic_edit_types import AgenticEditRequest

runner = TerminalRunner(llm=llm, args=args, ...)
runner.run(AgenticEditRequest(user_input="请帮我实现一个HTTP服务器"))
```
"""

from .base_runner import BaseRunner
from .terminal_runner import TerminalRunner
from .event_runner import EventRunner
from .sdk_runner import SdkRunner
from .tool_display import get_tool_display_message

__all__ = [
    "BaseRunner",
    "TerminalRunner",
    "EventRunner",
    "SdkRunner",
    "get_tool_display_message"
]
