"""
Auto-Coder SDK

为第三方开发者提供的 Python SDK，允许通过命令行工具和 Python API 两种方式使用 Auto-Coder 的核心功能。
"""

from typing import AsyncIterator, Optional, Dict, Any
import os
import subprocess
from .core.auto_coder_core import AutoCoderCore
from .models.options import AutoCodeOptions
from .models.messages import Message
from .models.responses import StreamEvent, CodeModificationResult
from .session.session import Session
from .session.session_manager import SessionManager
from .exceptions import (
    AutoCoderSDKError,
    SessionNotFoundError,
    InvalidOptionsError,
    BridgeError,
    ValidationError
)
from autocoder.auto_coder_runner import init_project_if_required as init_project_if_required_buildin

__version__ = "1.0.0"
__all__ = [
    # 核心功能
    "query",
    "query_sync",    
    
    # 数据模型
    "AutoCodeOptions",
    "Message",
    "StreamEvent",
    "CodeModificationResult",
    
    # 会话管理
    "Session",
    "SessionManager",
    
    # 异常
    "AutoCoderSDKError",
    "SessionNotFoundError",
    "InvalidOptionsError",
    "BridgeError",
    "ValidationError",
]


async def query(
    prompt: str, 
    options: Optional[AutoCodeOptions] = None,
    show_terminal: bool = True
) -> AsyncIterator[Message]:
    """
    异步流式查询接口
    
    Args:
        prompt: 查询提示
        options: 配置选项
        show_terminal: 是否在终端显示友好的渲染输出
        
    Yields:
        Message: 响应消息流
        
    Example:
        >>> import asyncio
        >>> from autocoder.sdk import query, AutoCodeOptions
        >>> 
        >>> async def main():
        ...     options = AutoCodeOptions(max_turns=3)
        ...     async for message in query("Write a hello world function", options):
        ...         print(f"[{message.role}] {message.content}")
        >>> 
        >>> asyncio.run(main())
    """
    if options is None:
        options = AutoCodeOptions()
    core = AutoCoderCore(options)
    async for message in core.query_stream(f"/new {prompt}", show_terminal):
        yield message


def query_sync(
    prompt: str, 
    options: Optional[AutoCodeOptions] = None,
    show_terminal: bool = True
) -> str:
    """
    同步查询接口
    
    Args:
        prompt: 查询提示
        options: 配置选项
        show_terminal: 是否在终端显示友好的渲染输出
        
    Returns:
        str: 响应内容
        
    Example:
        >>> from autocoder.sdk import query_sync, AutoCodeOptions
        >>> 
        >>> options = AutoCodeOptions(max_turns=1)
        >>> response = query_sync("Write a simple calculator function", options)
        >>> print(response)
    """
    if options is None:
        options = AutoCodeOptions()
    core = AutoCoderCore(options)
    return core.query_sync(f"/new {prompt}", show_terminal)

def init_project_if_required(target_dir: str,project_type = ".py,.ts"):
    init_project_if_required_buildin(target_dir,project_type)