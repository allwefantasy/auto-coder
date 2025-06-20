
# run_auto_command 集成方案设计

## 概述

本方案设计描述如何将 `auto_coder_runner.py` 中的 `run_auto_command` 方法集成到 Auto-Coder SDK 中，通过 `bridge.py` 和 `auto_coder_core.py` 对外提供代码修改能力，满足 SDK 的 API 使用要求。

## 1. 需求分析

### 1.1 核心需求

- 使用 `auto_coder_runner.py` 中的 `run_auto_command` 方法作为核心代码修改引擎
- 通过 `bridge.py` 桥接层适配现有功能
- 在 `auto_coder_core.py` 中提供统一的对外接口
- 满足 SDK README 中定义的 API 使用要求
- 支持同步和异步调用模式
- 支持流式和非流式响应

### 1.2 现有组件分析

#### auto_coder_runner.py 关键功能
- `run_auto_command(query: str, pre_commit: bool=False, extra_args: Dict[str,Any]={})` - 核心代码修改方法
- `get_memory()` - 获取项目内存状态
- `save_memory()` - 保存项目内存状态
- `get_final_config()` - 获取最终配置
- 支持 AgenticEdit 模式和传统命令模式

#### bridge.py 现状
- 基础桥接框架已存在
- 需要实现具体的 `run_auto_command` 调用逻辑
- 需要处理参数转换和结果封装

#### auto_coder_core.py 现状
- 提供了基础的查询接口框架
- 需要集成 `run_auto_command` 功能
- 需要支持流式响应

## 2. 架构设计

### 2.1 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Auto-Coder SDK                          │
├─────────────────────────────────────────────────────────────┤
│  Python API        │  CLI Interface                        │
│  - query()         │  - auto-coder.run                     │
│  - query_sync()    │  - 命令行参数解析                        │
│  - Session         │  - 输出格式化                           │
└─────────────────────┴───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                AutoCoderCore                               │
│  - query_stream()                                          │
│  - query_sync()                                            │
│  - 统一接口封装                                              │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│                AutoCoderBridge                             │
│  - call_run_auto_command()                                 │
│  - 参数转换和适配                                            │
│  - 结果封装和流式处理                                         │
└─────────────────────┬───────────────────────────────────────┘
                      │
┌─────────────────────▼───────────────────────────────────────┐
│            auto_coder_runner.py                           │
│  - run_auto_command()                                      │
│  - AgenticEdit 模式                                        │
│  - 传统命令模式                                              │
└─────────────────────────────────────────────────────────────┘
```

### 2.2 数据流设计

```
用户请求 → AutoCoderCore → AutoCoderBridge → run_auto_command → 事件流 → 响应封装 → 用户
```

## 3. 详细实现方案

### 3.1 AutoCoderBridge 增强

#### 3.1.1 新增 run_auto_command 桥接方法

```python
# src/autocoder/sdk/core/bridge.py

import os
import sys
from typing import Any, Dict, Optional, Iterator, AsyncIterator
from pathlib import Path

# 添加 auto_coder_runner 路径到系统路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from autocoder.auto_coder_runner import (
    run_auto_command,
    get_memory,
    save_memory,
    get_final_config,
    start,
    stop,
    project_root
)
from ..exceptions import BridgeError
from ..models.messages import Message
from ..models.responses import StreamEvent


class AutoCoderBridge:
    """桥接层，连接现有功能"""
    
    def __init__(self, project_root: str):
        """
        初始化桥接层
        
        Args:
            project_root: 项目根目录
        """
        self.project_root = project_root or os.getcwd()
        self._setup_environment()
    
    def _setup_environment(self):
        """设置环境和内存"""
        try:
            # 切换到项目根目录
            original_cwd = os.getcwd()
            os.chdir(self.project_root)
            
            # 初始化 auto_coder_runner 环境
            start()
            
            # 恢复原始工作目录
            os.chdir(original_cwd)
            
        except Exception as e:
            raise BridgeError(f"Failed to setup environment: {str(e)}", original_error=e)
    
    def call_run_auto_command(
        self, 
        query: str, 
        pre_commit: bool = False,
        extra_args: Optional[Dict[str, Any]] = None,
        stream: bool = True
    ) -> Iterator[StreamEvent]:
        """
        调用 run_auto_command 功能并返回事件流
        
        Args:
            query: 查询内容
            pre_commit: 是否预提交
            extra_args: 额外参数
            stream: 是否流式返回
            
        Yields:
            StreamEvent: 事件流
            
        Raises:
            BridgeError: 桥接层错误
        """
        try:
            # 切换到项目根目录
            original_cwd = os.getcwd()
            os.chdir(self.project_root)
            
            # 准备参数
            extra_args = extra_args or {}
            
            # 发送开始事件
            yield StreamEvent(
                event_type="start",
                data={"query": query, "pre_commit": pre_commit},
                timestamp=None
            )
            
            try:
                # 调用 run_auto_command
                events = run_auto_command(
                    query=query,
                    pre_commit=pre_commit,
                    extra_args=extra_args
                )
                
                # 如果返回的是生成器，逐个处理事件
                if hasattr(events, '__iter__') and not isinstance(events, (str, bytes)):
                    for event in events:
                        # 转换事件格式
                        stream_event = self._convert_event_to_stream_event(event)
                        yield stream_event
                else:
                    # 如果不是生成器，包装成单个事件
                    yield StreamEvent(
                        event_type="content",
                        data={"content": str(events)},
                        timestamp=None
                    )
                
                # 发送完成事件
                yield StreamEvent(
                    event_type="end",
                    data={"status": "completed"},
                    timestamp=None
                )
                
            except Exception as e:
                # 发送错误事件
                yield StreamEvent(
                    event_type="error",
                    data={"error": str(e), "error_type": type(e).__name__},
                    timestamp=None
                )
                raise
                
        except Exception as e:
            raise BridgeError(f"run_auto_command failed: {str(e)}", original_error=e)
        finally:
            # 恢复原始工作目录
            os.chdir(original_cwd)
    
    def _convert_event_to_stream_event(self, event: Any) -> StreamEvent:
        """
        将 run_auto_command 的事件转换为 StreamEvent
        
        Args:
            event: 原始事件
            
        Returns:
            StreamEvent: 转换后的事件
        """
        # 根据事件类型进行转换
        if hasattr(event, 'event_type'):
            return StreamEvent(
                event_type=event.event_type,
                data=getattr(event, 'data', {}),
                timestamp=getattr(event, 'timestamp', None)
            )
        else:
            # 如果是字符串或其他类型，包装成内容事件
            return StreamEvent(
                event_type="content",
                data={"content": str(event)},
                timestamp=None
            )
    
    def get_memory(self) -> Dict[str, Any]:
        """
        获取当前内存状态
        
        Returns:
            Dict[str, Any]: 内存数据
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(self.project_root)
            
            memory_data = get_memory()
            return memory_data
            
        except Exception as e:
            raise BridgeError(f"Failed to get memory: {str(e)}", original_error=e)
        finally:
            os.chdir(original_cwd)
    
    def save_memory(self, memory_data: Dict[str, Any]) -> None:
        """
        保存内存状态
        
        Args:
            memory_data: 要保存的内存数据
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(self.project_root)
            
            # 注意：auto_coder_runner 的 save_memory 不接受参数
            # 它保存的是全局 memory 变量
            # 如果需要设置特定内存数据，需要先更新全局 memory
            from autocoder.auto_coder_runner import memory
            memory.update(memory_data)
            save_memory()
            
        except Exception as e:
            raise BridgeError(f"Failed to save memory: {str(e)}", original_error=e)
        finally:
            os.chdir(original_cwd)
    
    def get_project_config(self) -> Dict[str, Any]:
        """
        获取项目配置
        
        Returns:
            Dict[str, Any]: 项目配置
        """
        try:
            original_cwd = os.getcwd()
            os.chdir(self.project_root)
            
            config = get_final_config()
            return config.__dict__ if hasattr(config, '__dict__') else {}
            
        except Exception as e:
            raise BridgeError(f"Failed to get project config: {str(e)}", original_error=e)
        finally:
            os.chdir(original_cwd)
    
    def setup_project_context(self) -> None:
        """设置项目上下文"""
        try:
            # 确保项目环境已正确初始化
            self._setup_environment()
        except Exception as e:
            raise BridgeError(f"Failed to setup project context: {str(e)}", original_error=e)
    
    def cleanup(self) -> None:
        """清理资源"""
        try:
            original_cwd = os.getcwd()
            os.chdir(self.project_root)
            
            # 停止 auto_coder_runner 相关服务
            stop()
            
        except Exception as e:
            # 清理失败不应该阻止程序继续运行，只记录错误
            print(f"Warning: Failed to cleanup resources: {str(e)}")
        finally:
            os.chdir(original_cwd)
    
    def __enter__(self):
        """上下文管理器入口"""
        self.setup_project_context()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """上下文管理器出口"""
        self.cleanup()
```

### 3.2 数据模型增强

#### 3.2.1 新增 StreamEvent 模型

```python
# src/autocoder/sdk/models/responses.py

from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from datetime import datetime
import json


@dataclass
class StreamEvent:
    """流式事件数据模型"""
    event_type: str  # start, content, end, error
    data: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamEvent":
        """从字典创建实例"""
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])
        
        return cls(
            event_type=data["event_type"],
            data=data.get("data", {}),
            timestamp=timestamp
        )


@dataclass
class CodeModificationResult:
    """代码修改结果"""
    success: bool
    message: str
    modified_files: list[str] = field(default_factory=list)
    created_files: list[str] = field(default_factory=list)
    deleted_files: list[str] = field(default_factory=list)
    error_details: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "success": self.success,
            "message": self.message,
            "modified_files": self.modified_files,
            "created_files": self.created_files,
            "deleted_files": self.deleted_files,
            "error_details": self.error_details,
            "metadata": self.metadata
        }
```

### 3.3 AutoCoderCore 增强

#### 3.3.1 集成 run_auto_command 功能

```python
# src/autocoder/sdk/core/auto_coder_core.py

"""
Auto-Coder SDK 核心封装类

提供统一的查询接口，处理同步和异步调用。
"""

from typing import AsyncIterator, Optional, Dict, Any, Iterator
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..models.options import AutoCodeOptions
from ..models.messages import Message
from ..models.responses import StreamEvent, CodeModificationResult
from ..exceptions import BridgeError
from .bridge import AutoCoderBridge


class AutoCoderCore:
    """AutoCoder核心封装类"""
    
    def __init__(self, options: AutoCodeOptions):
        """
        初始化AutoCoderCore
        
        Args:
            options: 配置选项
        """
        self.options = options
        self.bridge = AutoCoderBridge(options.cwd)
        self._executor = ThreadPoolExecutor(max_workers=1)
    
    async def query_stream(self, prompt: str) -> AsyncIterator[Message]:
        """
        异步流式查询 - 使用 run_auto_command
        
        Args:
            prompt: 查询提示
            
        Yields:
            Message: 响应消息流
            
        Raises:
            BridgeError: 桥接层错误
        """
        try:
            # 先返回用户消息
            user_message = Message(role="user", content=prompt)
            yield user_message
            
            # 在线程池中执行同步调用
            loop = asyncio.get_event_loop()
            
            # 使用 run_auto_command 进行代码修改
            event_stream = await loop.run_in_executor(
                self._executor,
                self._sync_run_auto_command,
                prompt
            )
            
            # 处理事件流并转换为消息
            assistant_content = ""
            for event in event_stream:
                if event.event_type == "content":
                    content = event.data.get("content", "")
                    assistant_content += content
                    
                    # 返回增量消息
                    yield Message(
                        role="assistant",
                        content=content,
                        metadata={
                            "event_type": event.event_type,
                            "model": self.options.model,
                            "temperature": self.options.temperature,
                            "is_incremental": True
                        }
                    )
                elif event.event_type == "end":
                    # 返回最终完整消息
                    yield Message(
                        role="assistant",
                        content=assistant_content,
                        metadata={
                            "event_type": event.event_type,
                            "model": self.options.model,
                            "temperature": self.options.temperature,
                            "is_final": True,
                            "status": event.data.get("status", "completed")
                        }
                    )
                elif event.event_type == "error":
                    # 返回错误消息
                    yield Message(
                        role="assistant",
                        content=f"Error: {event.data.get('error', 'Unknown error')}",
                        metadata={
                            "event_type": event.event_type,
                            "error_type": event.data.get("error_type", "Unknown"),
                            "is_error": True
                        }
                    )
            
        except Exception as e:
            raise BridgeError(f"Query stream failed: {str(e)}", original_error=e)
    
    def query_sync(self, prompt: str) -> str:
        """
        同步查询 - 使用 run_auto_command
        
        Args:
            prompt: 查询提示
            
        Returns:
            str: 响应内容
            
        Raises:
            BridgeError: 桥接层错误
        """
        try:
            event_stream = self._sync_run_auto_command(prompt)
            
            # 收集所有内容
            content_parts = []
            for event in event_stream:
                if event.event_type == "content":
                    content_parts.append(event.data.get("content", ""))
                elif event.event_type == "error":
                    raise BridgeError(f"Query failed: {event.data.get('error', 'Unknown error')}")
            
            return "".join(content_parts)
            
        except Exception as e:
            raise BridgeError(f"Sync query failed: {str(e)}", original_error=e)
    
    def modify_code(
        self, 
        prompt: str, 
        pre_commit: bool = False,
        extra_args: Optional[Dict[str, Any]] = None
    ) -> CodeModificationResult:
        """
        代码修改接口 - 直接使用 run_auto_command
        
        Args:
            prompt: 修改提示
            pre_commit: 是否预提交
            extra_args: 额外参数
            
        Returns:
            CodeModificationResult: 修改结果
        """
        try:
            event_stream = self._sync_run_auto_command(
                prompt, 
                pre_commit=pre_commit, 
                extra_args=extra_args
            )
            
            # 分析事件流，提取修改结果
            modified_files = []
            created_files = []
            deleted_files = []
            messages = []
            success = True
            error_details = None
            
            for event in event_stream:
                if event.event_type == "content":
                    messages.append(event.data.get("content", ""))
                elif event.event_type == "error":
                    success = False
                    error_details = event.data.get("error", "Unknown error")
                elif event.event_type == "file_modified":
                    modified_files.extend(event.data.get("files", []))
                elif event.event_type == "file_created":
                    created_files.extend(event.data.get("files", []))
                elif event.event_type == "file_deleted":
                    deleted_files.extend(event.data.get("files", []))
            
            return CodeModificationResult(
                success=success,
                message="".join(messages),
                modified_files=modified_files,
                created_files=created_files,
                deleted_files=deleted_files,
                error_details=error_details,
                metadata={
                    "pre_commit": pre_commit,
                    "extra_args": extra_args or {}
                }
            )
            
        except Exception as e:
            return CodeModificationResult(
                success=False,
                message="",
                error_details=str(e),
                metadata={"exception_type": type(e).__name__}
            )
    
    async def modify_code_stream(
        self, 
        prompt: str, 
        pre_commit: bool = False,
        extra_args: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[StreamEvent]:
        """
        异步流式代码修改接口
        
        Args:
            prompt: 修改提示
            pre_commit: 是否预提交
            extra_args: 额外参数
            
        Yields:
            StreamEvent: 修改事件流
        """
        try:
            loop = asyncio.get_event_loop()
            
            # 在线程池中执行同步调用
            event_stream = await loop.run_in_executor(
                self._executor,
                self._sync_run_auto_command,
                prompt,
                pre_commit,
                extra_args
            )
            
            # 直接转发事件流
            for event in event_stream:
                yield event
                
        except Exception as e:
            yield StreamEvent(
                event_type="error",
                data={"error": str(e), "error_type": type(e).__name__}
            )
    
    def _sync_run_auto_command(
        self, 
        prompt: str, 
        pre_commit: bool = False,
        extra_args: Optional[Dict[str, Any]] = None
    ) -> Iterator[StreamEvent]:
        """
        内部同步调用 run_auto_command
        
        Args:
            prompt: 查询提示
            pre_commit: 是否预提交
            extra_args: 额外参数
            
        Returns:
            Iterator[StreamEvent]: 事件流
        """
        return self.bridge.call_run_auto_command(
            query=prompt,
            pre_commit=pre_commit,
            extra_args=extra_args or {},
            stream=True
        )
    
    def get_session_manager(self):
        """
        获取会话管理器
        
        Returns:
            SessionManager: 会话管理器实例
        """
        from ..session.session_manager import SessionManager
        return SessionManager(self.options.cwd)
    
    def get_project_memory(self) -> Dict[str, Any]:
        """
        获取项目内存状态
        
        Returns:
            Dict[str, Any]: 项目内存数据
        """
        return self.bridge.get_memory()
    
    def save_project_memory(self, memory_data: Dict[str, Any]) -> None:
        """
        保存项目内存状态
        
        Args:
            memory_data: 内存数据
        """
        self.bridge.save_memory(memory_data)
    
    def get_project_config(self) -> Dict[str, Any]:
        """
        获取项目配置
        
        Returns:
            Dict[str, Any]: 项目配置
        """
        return self.bridge.get_project_config()
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)
```

### 3.4 SDK 主入口更新

#### 3.4.1 更新 __init__.py

```python
# src/autocoder/sdk/__init__.py

"""
Auto-Coder SDK

为第三方开发者提供的 Python SDK，允许通过命令行工具和 Python API 两种方式使用 Auto-Coder 的核心功能。
"""

from typing import AsyncIterator, Optional, Dict, Any

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

__version__ = "1.0.0"
__all__ = [
    # 核心功能
    "query",
    "query_sync",
    "modify_code",
    "modify_code_stream",
    
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
    options: Optional[AutoCodeOptions] = None
) -> AsyncIterator[Message]:
    """
    异步流式查询接口
    
    Args:
        prompt: 查询提示
        options: 配置选项
        
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
    core = AutoCoderCore(options or AutoCodeOptions())
    async for message in core.query_stream(prompt):
        yield message


def query_sync(
    prompt: str, 
    options: Optional[AutoCodeOptions] = None
) -> str:
    """
    同步查询接口
    
    Args:
        prompt: 查询提示
        options: 配置选项
        
    Returns:
        str: 响应内容
        
    Example:
        >>> from autocoder.sdk import query_sync, AutoCodeOptions
        >>> 
        >>> options = AutoCodeOptions(max_turns=1)
        >>> response = query_sync("Write a simple calculator function", options)
        >>> print(response)
    """
    core = AutoCoderCore(options or AutoCodeOptions())
    return core.query_sync(prompt)


def modify_code(
    prompt: str,
    pre_commit: bool = False,
    extra_args: Optional[Dict[str, Any]] = None,
    options: Optional[AutoCodeOptions] = None
) -> CodeModificationResult:
    """
    代码修改接口
    
    Args:
        prompt: 修改提示
        pre_commit: 是否预提交
        extra_args: 额外参数
        options: 配置选项
        
    Returns:
        CodeModificationResult: 修改结果
        
    Example:
        >>> from autocoder.sdk import modify_code, AutoCodeOptions
        >>> 
        >>> options = AutoCodeOptions(cwd="/path/to/project")
        >>> result = modify_code(
        ...     "Add error handling to the main function",
        ...     pre_commit=False,
        ...     options=options
        ... )
        >>> 
        >>> if result.success:
        ...     print(f"Modified files: {result.modified_files}")
        ... else:
        ...     print(f"Error: {result.error_details}")
    """
    core = AutoCoderCore(options or AutoCodeOptions())
    return core.modify_code(prompt, pre_commit, extra_args)


async def modify_code_stream(
    prompt: str,
    pre_commit: bool = False,
    extra_args: Optional[Dict[str, Any]] = None,
    options: Optional[AutoCodeOptions] = None
) -> AsyncIterator[StreamEvent]:
    """
    异步流式代码修改接口
    
    Args:
        prompt: 修改提示
        pre_commit: 是否预提交
        extra_args: 额外参数
        options: 配置选项
        
    Yields:
        StreamEvent: 修改事件流
        
    Example:
        >>> import asyncio
        >>> from autocoder.sdk import modify_code_stream, AutoCodeOptions
        >>> 
        >>> async def main():
        ...     options = AutoCodeOptions(cwd="/path/to/project")
        ...     async for event in modify_code_stream(
        ...         "Refactor the user authentication module",
        ...         options=options
        ...     ):
        ...         print(f"[{event.event_type}] {event.data}")
        >>> 
        >>> asyncio.run(main())
    """
    core = AutoCoderCore(options or AutoCodeOptions())
    async for event in core.modify_code_stream(prompt, pre_commit, extra_args):
        yield event
```

## 4. 使用示例

### 4.1 Python API 使用示例

#### 4.1.1 基础代码修改

```python
from autocoder.sdk import modify_code, AutoCodeOptions

# 基础代码修改
options = AutoCodeOptions(
    cwd="/path/to/project",
    max_turns=3,
    model="gpt-4"
)

result = modify_code(
    "Add input validation to the user registration function",
    pre_commit=False,
    options=options
)

if result.success:
    print(f"Successfully modified {len(result.modified_files)} files")
    for file in result.modified_files:
        print(f"  - {file}")
else:
    print(f"Modification failed: {result.error_details}")
```

#### 4.1.2 流式代码修改

```python
import asyncio
from autocoder.sdk import modify_code_stream, AutoCodeOptions

async def stream_modify():
    options = AutoCodeOptions(cwd="/path/to/project")
    
    async for event in modify_code_stream(
        "Implement user authentication with JWT tokens",
        pre_commit=False,
        options=options
    ):
        if event.event_type == "start":
            print("Starting code modification...")
        elif event.event_type == "content":
            print(f"Progress: {event.data.get('content', '')}")
        elif event.event_type == "end":
            print("Code modification completed!")
        elif event.event_type == "error":
            print(f"Error: {event.data.get('error', '')}")

asyncio.run(stream_modify())
```

#### 4.1.3 会话管理

```python
import asyncio
from autocoder.sdk import Session, AutoCodeOptions

async def session_example():
    options = AutoCodeOptions(
        cwd="/path/to/project",
        max_turns=10
    )
    
    # 创建新会话
    session = Session(options=options)
    
    # 进行多轮代码修改对话
    result1 = await session.modify_code("Create a user model with SQLAlchemy")
    print(f"Step 1: {result1.message}")
    
    result2 = await session.modify_code("Add validation methods to the user model")
    print(f"Step 2: {result2.message}")
    
    result3 = await session.modify_code("Create unit tests for the user model")
    print(f"Step 3: {result3.message}")
    
    # 保存会话
    await session.save("user_model_development")

asyncio.run(session_example())
```

### 4.2 CLI 使用示例

#### 4.2.1 基础命令行使用

```bash
# 单次代码修改
auto-coder.run -p "Add error handling to the main function"

# 指定项目目录
auto-coder.run -p "Implement user authentication" --cwd /path/to/project

# JSON 输出格式
auto-coder.run -p "Refactor the database layer" --output-format json

# 流式 JSON 输出
auto-coder.run -p "Add logging to all API endpoints" --output-format stream-json
```

#### 4.2.2 会话模式

```bash
# 继续最近的会话
auto-coder.run --continue "Now add unit tests for the new features"

# 恢复特定会话
auto-coder.run --resume 550e8400-e29b-41d4-a716-446655440000 "Update the documentation"

# 详细输出模式
auto-coder.run -p "Optimize the search algorithm" --verbose
```

## 5. 测试策略

### 5.1 单元测试

```python
import pytest
from unittest.mock import Mock, patch
from autocoder.sdk import modify_code, AutoCodeOptions
from autocoder.sdk.core.bridge import AutoCoderBridge
from autocoder.sdk.models.responses import StreamEvent, CodeModificationResult

class TestRunAutoCommandIntegration:
    
    @pytest.fixture
    def bridge(self):
        return AutoCoderBridge("/test/project")
    
    @pytest.fixture
    def options(self):
        return AutoCodeOptions(cwd="/test/project")
    
    def test_bridge_call_run_auto_command(self, bridge):
        """测试桥接层调用 run_auto_command"""
        with patch('autocoder.sdk.core.bridge.run_auto_command') as mock_run:
            # 模拟返回事件流
            mock_events = [
                StreamEvent("start", {"query": "test"}),
                StreamEvent("content", {"content": "Processing..."}),
                StreamEvent("end", {"status": "completed"})
            ]
            mock_run.return_value = iter(mock_events)
            
            events = list(bridge.call_run_auto_command("test query"))
            
            assert len(events) >= 3  # start + content + end
            assert events[0].event_type == "start"
            assert any(e.event_type == "content" for e in events)
            assert events[-1].event_type == "end"
    
    def test_modify_code_success(self, options):
        """测试成功的代码修改"""
        with patch('autocoder.sdk.core.bridge.run_auto_command') as mock_run:
            mock_events = [
                StreamEvent("start", {"query": "test"}),
                StreamEvent("content", {"content": "Modified file.py"}),
                StreamEvent("file_modified", {"files": ["file.py"]}),
                StreamEvent("end", {"status": "completed"})
            ]
            mock_run.return_value = iter(mock_events)
            
            result = modify_code("Add function", options=options)
            
            assert result.success is True
            assert "file.py" in result.modified_files
            assert "Modified file.py" in result.message
    
    def test_modify_code_error(self, options):
        """测试代码修改错误处理"""
        with patch('autocoder.sdk.core.bridge.run_auto_command') as mock_run:
            mock_events = [
                StreamEvent("start", {"query": "test"}),
                StreamEvent("error", {"error": "File not found", "error_type": "FileNotFoundError"}),
            ]
            mock_run.return_value = iter(mock_events)
            
            result = modify_code("Add function", options=options)
            
            assert result.success is False
            assert "File not found" in result.error_details
```

### 5.2 集成测试

```python
import pytest
import tempfile
import os
from autocoder.sdk import modify_code, AutoCodeOptions

class TestEndToEndIntegration:
    
    @pytest.fixture
    def temp_project(self):
        """创建临时项目目录"""
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建基本项目结构
            os.makedirs(os.path.join(temp_dir, ".auto-coder"))
            
            # 创建测试文件
            test_file = os.path.join(temp_dir, "test.py")
            with open(test_file, "w") as f:
                f.write("def hello():\n    print('Hello')\n")
            
            yield temp_dir
    
    def test_real_code_modification(self, temp_project):
        """测试真实的代码修改流程"""
        options = AutoCodeOptions(cwd=temp_project)
        
        result = modify_code(
            "Add a docstring to the hello function",
            options=options
        )
        
        # 验证修改结果
        assert result.success is True
        
        # 检查文件是否被修改
        test_file = os.path.join(temp_project, "test.py")
        with open(test_file, "r") as f:
            content = f.read()
            assert "docstring" in content.lower() or '"""' in content
```

## 6. 部署和发布

### 6.1 打包配置

```python
# setup.py 更新
from setuptools import setup, find_packages

setup(
    name="autocoder-sdk",
    version="1.0.0",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    install_requires=[
        "autocoder>=1.0.0",  # 依赖主项目
        "asyncio",
        "typing-extensions",
        "dataclasses; python_version<'3.7'",
    ],
    entry_points={
        "console_scripts": [
            "auto-coder.run=autocoder.sdk.cli.main:main",
        ],
    },
    python_requires=">=3.7",
    author="AutoCoder Team",
    description="Auto-Coder SDK for third-party integration",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/allwefantasy/auto-coder",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
```

### 6.2 文档更新

更新 `src/autocoder/sdk/README.md` 以包含新的代码修改功能：

```markdown
## 代码修改功能

### 基础代码修改

```python
from autocoder.sdk import modify_code, AutoCodeOptions

options = AutoCodeOptions(cwd="/path/to/project")
result = modify_code("Add input validation to user registration", options=options)

if result.success:
    print(f"Modified files: {result.modified_files}")
else:
    print(f"Error: {result.error_details}")
```

### 流式代码修改

```python
import asyncio
from autocoder.sdk import modify_code_stream

async def stream_modify():
    async for event in modify_code_stream("Implement JWT authentication"):
        print(f"[{event.event_type}] {event.data}")

asyncio.run(stream_modify())
```
```

## 7. 实施计划

### 第一阶段（第1-2周）：基础桥接实现
1. 实现 `AutoCoderBridge.call_run_auto_command` 方法
2. 创建 `StreamEvent` 和 `CodeModificationResult` 数据模型
3. 编写基础桥接层测试

### 第二阶段（第3-4周）：核心功能集成
1. 在 `AutoCoderCore` 中集成 `run_auto_command` 功能
2. 实现 `modify_code` 和 `modify_code_stream` 接口
3. 更新主入口文件和导出接口

### 第三阶段（第5-6周）：CLI 和会话支持
1. 更新 CLI 工具支持代码修改功能
2. 在会话管理中集成代码修改能力
3. 完善错误处理和用户体验

### 第四阶段（第7-8周）：测试和文档
1. 编写完整的单元测试和集成测试
2. 更新文档和使用示例
3. 性能优化和稳定性改进

### 第五阶段（第9-10周）：发布准备
1. 代码审查和质量检查
2. 打包配置和依赖管理
3. 发布到 PyPI 和文档站点

## 8. 风险评估和缓解策略

### 8.1 技术风险

**风险：** `run_auto_command` 接口变更
**缓解：** 在桥接层实现版本兼容性检查和适配逻辑

**风险：** 异步/同步转换性能问题
**缓解：** 使用线程池优化，实现连接复用

**风险：** 事件流格式不兼容
**缓解：** 实现灵活的事件转换器，支持多种格式

### 8.2 集成风险

**风险：** 项目环境设置复杂
**缓解：** 提供详细的环境检查和自动修复功能

**风险：** 内存状态管理冲突
**缓解：** 实现隔离的内存管理机制

### 8.3 用户体验风险

**风险：** API 学习成本高
**缓解：** 提供丰富的示例和渐进式文档

**风险：** 错误信息不清晰
**缓解：** 实现结构化错误处理和友好的错误提示

## 9. 成功标准

1. **功能完整性**：所有 SDK API 功能正常工作
2. **性能要求**：代码修改响应时间 < 5秒（小型项目）
3. **稳定性**：错误率 < 1%，无内存泄漏
4. **易用性**：新用户可在30分钟内完成基础使用
5. **兼容性**：支持 Python 3.7+ 和主流操作系统
6. **测试覆盖率**：单元测试覆盖率 > 90%，集成测试覆盖率 > 80%

通过这个方案设计，我们可以成功地将 `run_auto_command` 功能集成到 Auto-Coder SDK 中，为第三方开发者提供强大的代码修改能力。
