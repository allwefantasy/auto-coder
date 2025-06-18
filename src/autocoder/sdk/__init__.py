"""
Auto-Coder SDK

一个为第三方开发者提供的 Python SDK，允许通过命令行工具和 Python API 两种方式使用 Auto-Coder 的核心功能。
"""

from .models.options import AutoCodeOptions
from .models.messages import Message
from .models.responses import CLIResult
from .core.auto_coder_core import AutoCoderCore
from .session.session import Session
from .exceptions import (
    AutoCoderSDKError,
    SessionNotFoundError,
    InvalidOptionsError,
    BridgeError
)

# 主要的公共API
async def query(prompt: str, options: AutoCodeOptions = None):
    """
    异步查询接口
    
    Args:
        prompt: 查询提示
        options: 配置选项
        
    Yields:
        Message: 响应消息流
    """
    from typing import AsyncIterator
    
    if options is None:
        options = AutoCodeOptions()
    
    core = AutoCoderCore(options)
    async for message in core.query_stream(prompt):
        yield message


def query_sync(prompt: str, options: AutoCodeOptions = None) -> str:
    """
    同步查询接口
    
    Args:
        prompt: 查询提示
        options: 配置选项
        
    Returns:
        str: 响应内容
    """
    if options is None:
        options = AutoCodeOptions()
    
    core = AutoCoderCore(options)
    return core.query_sync(prompt)


__version__ = "0.1.0"
__all__ = [
    "query",
    "query_sync", 
    "AutoCodeOptions",
    "Message",
    "CLIResult",
    "Session",
    "AutoCoderSDKError",
    "SessionNotFoundError", 
    "InvalidOptionsError",
    "BridgeError"
]
