





"""
Auto-Coder SDK 核心封装类

提供统一的查询接口，处理同步和异步调用。
"""

from typing import AsyncIterator, Optional
import asyncio
from concurrent.futures import ThreadPoolExecutor

from ..models.options import AutoCodeOptions
from ..models.messages import Message
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
        异步流式查询
        
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
            response = await loop.run_in_executor(
                self._executor,
                self._sync_query,
                prompt
            )
            
            # 返回助手响应
            assistant_message = Message(
                role="assistant", 
                content=response,
                metadata={
                    "model": self.options.model,
                    "temperature": self.options.temperature
                }
            )
            yield assistant_message
            
        except Exception as e:
            raise BridgeError(f"Query stream failed: {str(e)}", original_error=e)
    
    def query_sync(self, prompt: str) -> str:
        """
        同步查询
        
        Args:
            prompt: 查询提示
            
        Returns:
            str: 响应内容
            
        Raises:
            BridgeError: 桥接层错误
        """
        try:
            return self._sync_query(prompt)
        except Exception as e:
            raise BridgeError(f"Sync query failed: {str(e)}", original_error=e)
    
    def _sync_query(self, prompt: str) -> str:
        """
        内部同步查询实现
        
        Args:
            prompt: 查询提示
            
        Returns:
            str: 响应内容
        """
        # 这里将调用桥接层的功能
        # 目前返回模拟响应，后续在阶段2中实现真正的桥接
        return f"[Mock Response] Processed query: {prompt}"
    
    def get_session_manager(self):
        """
        获取会话管理器
        
        Returns:
            SessionManager: 会话管理器实例
        """
        from ..session.session_manager import SessionManager
        return SessionManager(self.options.cwd)
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)





