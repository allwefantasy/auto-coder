"""
Entry Command Agent 模块

该模块包含各种入口命令的代理实现，用于处理不同类型的用户命令。

目前包含的代理：
- ChatAgent: 处理聊天命令的代理
"""

from .chat import ChatAgent

__all__ = ['ChatAgent']
