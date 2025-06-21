












"""
Auto-Coder SDK 会话类

处理单个会话的创建、查询和保存功能。
"""

import uuid
from typing import List, Optional
from datetime import datetime

from ..models.options import AutoCodeOptions
from ..models.messages import Message, MessageBatch
from ..models.responses import SessionInfo
from ..exceptions import SessionNotFoundError


class Session:
    """简化的会话类，仅用于 Python API"""
    
    def __init__(self, session_id: str = None, options: AutoCodeOptions = None):
        """
        初始化会话
        
        Args:
            session_id: 会话ID，如果为None则自动生成
            options: 配置选项
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.options = options or AutoCodeOptions()
        self._core = None
    
    @property
    def core(self):
        """延迟初始化核心组件"""
        if self._core is None:
            from ..core.auto_coder_core import AutoCoderCore
            self._core = AutoCoderCore(self.options)
        return self._core
    
    async def query(self, prompt: str) -> str:
        """
        异步查询 - 通过核心模块实现
        
        Args:
            prompt: 查询提示
            
        Returns:
            str: 响应内容
        """
        final_prompt = f"/id {self.session_id} {prompt}"
        response_content = ""
        async for message in self.core.query_stream(final_prompt):
            if message.role == "assistant" and hasattr(message, 'metadata') and message.metadata.get('is_final'):
                response_content = message.content
                break
            elif message.role == "assistant" and not hasattr(message, 'metadata'):
                response_content += message.content
        return response_content
    
    def query_sync(self, prompt: str) -> str:
        """
        同步查询 - 通过核心模块实现
        
        Args:
            prompt: 查询提示
            
        Returns:
            str: 响应内容
        """
        final_prompt = f"/id {self.session_id} {prompt}"
        return self.core.query_sync(final_prompt)
    
    def get_history(self) -> List[Message]:
        """
        获取对话历史 - 简化实现
        
        Returns:
            List[Message]: 消息历史
        """
        # 从底层系统获取历史记录
        return []












