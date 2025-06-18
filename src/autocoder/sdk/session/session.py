












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
    """会话类"""
    
    def __init__(self, session_id: str = None, options: AutoCodeOptions = None):
        """
        初始化会话
        
        Args:
            session_id: 会话ID，如果为None则自动生成
            options: 配置选项
        """
        self.session_id = session_id or str(uuid.uuid4())
        self.options = options or AutoCodeOptions()
        self.message_batch = MessageBatch()
        self.created_at = datetime.now()
        self.last_updated = self.created_at
        self.name: Optional[str] = None
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
        在会话中进行查询
        
        Args:
            prompt: 查询提示
            
        Returns:
            str: 响应内容
        """
        # 添加用户消息到历史
        self.message_batch.add_user_message(prompt)
        
        # 执行查询
        response_content = ""
        async for message in self.core.query_stream(prompt):
            if message.is_assistant_message():
                response_content = message.content
                # 添加助手响应到历史
                self.message_batch.add_message(message)
        
        self.last_updated = datetime.now()
        return response_content
    
    def query_sync(self, prompt: str) -> str:
        """
        同步查询
        
        Args:
            prompt: 查询提示
            
        Returns:
            str: 响应内容
        """
        # 添加用户消息到历史
        self.message_batch.add_user_message(prompt)
        
        # 执行同步查询
        response_content = self.core.query_sync(prompt)
        
        # 添加助手响应到历史
        self.message_batch.add_assistant_message(response_content)
        
        self.last_updated = datetime.now()
        return response_content
    
    def continue_conversation(self, prompt: str) -> str:
        """
        继续对话
        
        Args:
            prompt: 新的提示
            
        Returns:
            str: 响应内容
        """
        # 继续对话实际上就是普通查询，但会保持历史上下文
        return self.query_sync(prompt)
    
    async def save(self, name: str = None) -> None:
        """
        保存会话
        
        Args:
            name: 会话名称，可选
        """
        if name:
            self.name = name
        
        # 这里将实现会话保存逻辑
        # 在阶段3中完成具体实现
        pass
    
    @classmethod
    async def load(cls, session_name: str) -> "Session":
        """
        加载会话
        
        Args:
            session_name: 会话名称或ID
            
        Returns:
            Session: 加载的会话实例
            
        Raises:
            SessionNotFoundError: 会话不存在
        """
        # 这里将实现会话加载逻辑
        # 在阶段3中完成具体实现
        raise SessionNotFoundError(session_name)
    
    def get_history(self) -> List[Message]:
        """
        获取对话历史
        
        Returns:
            List[Message]: 消息历史
        """
        return self.message_batch.messages.copy()
    
    def get_session_info(self) -> SessionInfo:
        """
        获取会话信息
        
        Returns:
            SessionInfo: 会话信息
        """
        return SessionInfo(
            session_id=self.session_id,
            name=self.name,
            created_at=self.created_at,
            last_updated=self.last_updated,
            message_count=len(self.message_batch.messages),
            status="active"
        )
    
    def clear_history(self) -> None:
        """清空对话历史"""
        self.message_batch = MessageBatch()
        self.last_updated = datetime.now()
    
    def add_system_message(self, content: str) -> None:
        """
        添加系统消息
        
        Args:
            content: 系统消息内容
        """
        self.message_batch.add_system_message(content)
        self.last_updated = datetime.now()
    
    def get_context_summary(self) -> str:
        """
        获取上下文摘要
        
        Returns:
            str: 上下文摘要
        """
        messages = self.get_history()
        if not messages:
            return "Empty conversation"
        
        summary_parts = []
        for msg in messages[-5:]:  # 只显示最近5条消息
            role_emoji = {"user": "👤", "assistant": "🤖", "system": "⚙️"}.get(msg.role, "❓")
            content_preview = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
            summary_parts.append(f"{role_emoji} {content_preview}")
        
        return "\n".join(summary_parts)
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Session(id={self.session_id[:8]}..., messages={len(self.message_batch.messages)})"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return (f"Session(session_id='{self.session_id}', "
                f"name='{self.name}', "
                f"message_count={len(self.message_batch.messages)}, "
                f"created_at={self.created_at})")












