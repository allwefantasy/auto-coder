"""
PersistConversationManager 数据模型定义
"""

import time
import uuid
from typing import Union, Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ConversationMessage:
    """对话消息数据模型"""
    
    role: str
    content: Union[str, dict, list]
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Optional[dict] = None
    
    def __post_init__(self):
        """数据验证"""
        self._validate()
    
    def _validate(self):
        """验证消息数据"""
        # 验证角色
        valid_roles = ["system", "user", "assistant"]
        if not self.role or self.role not in valid_roles:
            raise ValueError(f"无效的消息角色: {self.role}，有效角色: {valid_roles}")
        
        # 验证内容
        if self.content is None or (isinstance(self.content, str) and len(self.content) == 0):
            raise ValueError("消息内容不能为空")
        
        # 验证时间戳
        if not isinstance(self.timestamp, (int, float)) or self.timestamp <= 0:
            raise ValueError("无效的时间戳")
        
        # 验证消息ID
        if not isinstance(self.message_id, str) or len(self.message_id) == 0:
            raise ValueError("消息ID不能为空")
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp,
            "message_id": self.message_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "ConversationMessage":
        """从字典反序列化"""
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=data["timestamp"],
            message_id=data["message_id"],
            metadata=data.get("metadata")
        )


@dataclass
class Conversation:
    """对话数据模型"""
    
    name: str
    conversation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: Optional[str] = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    messages: List[dict] = field(default_factory=list)
    metadata: Optional[dict] = None
    version: int = 1
    
    def __post_init__(self):
        """数据验证"""
        self._validate()
    
    def _validate(self):
        """验证对话数据"""
        # 验证名称
        if not self.name or (isinstance(self.name, str) and len(self.name) == 0):
            raise ValueError("对话名称不能为空")
        
        # 验证版本号
        if not isinstance(self.version, int) or self.version <= 0:
            raise ValueError("版本号必须是正整数")
        
        # 验证时间戳
        if not isinstance(self.created_at, (int, float)) or self.created_at <= 0:
            raise ValueError("无效的创建时间戳")
        
        if not isinstance(self.updated_at, (int, float)) or self.updated_at < self.created_at:
            raise ValueError("无效的更新时间戳")
        
        # 验证对话ID
        if not isinstance(self.conversation_id, str) or len(self.conversation_id) == 0:
            raise ValueError("对话ID不能为空")
        
        # 验证消息列表
        if not isinstance(self.messages, list):
            raise ValueError("消息列表必须是列表类型")
    
    def add_message(self, message: ConversationMessage):
        """添加消息到对话"""
        self.messages.append(message.to_dict())
        self.updated_at = time.time()
    
    def remove_message(self, message_id: str) -> bool:
        """从对话中删除消息"""
        for i, msg in enumerate(self.messages):
            if msg.get("message_id") == message_id:
                del self.messages[i]
                self.updated_at = time.time()
                return True
        return False
    
    def get_message(self, message_id: str) -> Optional[dict]:
        """从对话中获取消息"""
        for msg in self.messages:
            if msg.get("message_id") == message_id:
                return msg
        return None
    
    def to_dict(self) -> dict:
        """序列化为字典"""
        return {
            "conversation_id": self.conversation_id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "messages": self.messages,
            "metadata": self.metadata,
            "version": self.version
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Conversation":
        """从字典反序列化"""
        return cls(
            conversation_id=data["conversation_id"],
            name=data["name"],
            description=data.get("description"),
            created_at=data["created_at"],
            updated_at=data["updated_at"],
            messages=data.get("messages", []),
            metadata=data.get("metadata"),
            version=data.get("version", 1)
        ) 