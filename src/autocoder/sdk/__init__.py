"""
Auto-Coder SDK

为第三方开发者提供的 Python SDK，允许通过命令行工具和 Python API 两种方式使用 Auto-Coder 的核心功能。
"""

from typing import AsyncIterator, Iterator, Optional
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
from autocoder.auto_coder_runner import (
    configure as configure_buildin,
    load_tokenizer,
    start as start_engine,
    commit as commit_buildin
)
from autocoder.rag.variable_holder import VariableHolder
from autocoder.utils.llms import get_single_llm

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


async def query_with_events(
    prompt: str, 
    options: Optional[AutoCodeOptions] = None,
    show_terminal: bool = False
) -> AsyncIterator[StreamEvent]:
    """
    异步流式查询接口，返回原始事件流
    
    Args:
        prompt: 查询提示
        options: 配置选项
        show_terminal: 是否在终端显示友好的渲染输出（默认为False，避免重复显示）
        
    Yields:
        StreamEvent: 原始事件流，包含详细的执行过程信息
        
    Example:
        >>> import asyncio
        >>> from autocoder.sdk import query_with_events, AutoCodeOptions
        >>> 
        >>> async def main():
        ...     options = AutoCodeOptions(max_turns=3)
        ...     async for event in query_with_events("Write a hello world function", options):
        ...         print(f"[{event.event_type}] {event.data}")
        >>> 
        >>> asyncio.run(main())
    """
    if options is None:
        options = AutoCodeOptions()
    core = AutoCoderCore(options)
    
    # 使用桥接层直接获取事件流
    import asyncio
    loop = asyncio.get_event_loop()
    
    # 在线程池中执行同步调用
    event_stream = await loop.run_in_executor(
        core._executor,
        core._sync_run_auto_command,
        f"/new {prompt}"
    )
    
    # 直接返回事件流
    for event in event_stream:
        # 可选择性地渲染到终端
        if show_terminal:
            core._render_stream_event(event, show_terminal)
        yield event


def query_with_events_sync(
    prompt: str, 
    options: Optional[AutoCodeOptions] = None,
    show_terminal: bool = False
) -> Iterator[StreamEvent]:
    """
    同步查询接口，返回原始事件流生成器
    
    Args:
        prompt: 查询提示
        options: 配置选项
        show_terminal: 是否在终端显示友好的渲染输出（默认为False，避免重复显示）
        
    Returns:
        Iterator[StreamEvent]: 原始事件流生成器，包含详细的执行过程信息
        
    Example:
        >>> from autocoder.sdk import query_with_events_sync, AutoCodeOptions
        >>> 
        >>> options = AutoCodeOptions(max_turns=1)
        >>> for event in query_with_events_sync("Write a simple calculator function", options):
        ...     print(f"[{event.event_type}] {event.data}")
    """
    if options is None:
        options = AutoCodeOptions()
    core = AutoCoderCore(options)
    
    # 直接调用同步方法获取事件流
    event_stream = core._sync_run_auto_command(f"/new {prompt}")
    
    # 直接返回事件流
    for event in event_stream:
        # 可选择性地渲染到终端
        if show_terminal:
            core._render_stream_event(event, show_terminal)
        yield event


def init_project_if_required(target_dir: str,project_type = ".py,.ts"):    
    init_project_if_required_buildin(target_dir,project_type)
    if not VariableHolder.TOKENIZER_MODEL:
        load_tokenizer()
    start_engine()


def configure(key:str,value:str):
    configure_buildin(f"{key}:{value}")


def get_llm(model:str,product_mode:str="lite"):
    return get_single_llm(model,product_mode)

def commit(query: Optional[str] = None):
    commit_buildin(query)


__version__ = "1.0.0"
__all__ = [
    "query",
    "query_sync",
    "query_with_events",
    "query_with_events_sync",
    "get_llm",
    "configure",
    "init_project_if_required",
    "AutoCodeOptions",
    "Message",
    "StreamEvent",
    "CodeModificationResult",
    "Session",
    "SessionManager",
    "AutoCoderSDKError",
    "SessionNotFoundError",
    "InvalidOptionsError",
    "BridgeError",
    "ValidationError",
    "commit",
]    