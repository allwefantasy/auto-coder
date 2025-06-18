


"""
Auto-Coder SDK 消息模型

定义Message类和相关的消息处理功能。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from ..constants import MESSAGE_ROLES


@dataclass
class Message:
    """消息数据模型"""
    
    role: str
    content: str
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
        
        # 验证role
        if self.role not in MESSAGE_ROLES:
            raise ValueError(f"Invalid role: {self.role}. Must be one of: {', '.join(MESSAGE_ROLES.keys())}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """从字典创建Message实例"""
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])
        
        return cls(
            role=data["role"],
            content=data["content"],
            timestamp=timestamp,
            metadata=data.get("metadata", {})
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "Message":
        """从JSON字符串创建Message实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def add_metadata(self, key: str, value: Any) -> None:
        """添加元数据"""
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """获取元数据"""
        return self.metadata.get(key, default)
    
    def is_user_message(self) -> bool:
        """判断是否为用户消息"""
        return self.role == "user"
    
    def is_assistant_message(self) -> bool:
        """判断是否为助手消息"""
        return self.role == "assistant"
    
    def is_system_message(self) -> bool:
        """判断是否为系统消息"""
        return self.role == "system"
    
    def __str__(self) -> str:
        """字符串表示"""
        return f"Message(role={self.role}, content={self.content[:50]}...)"
    
    def __repr__(self) -> str:
        """详细字符串表示"""
        return f"Message(role='{self.role}', content='{self.content}', timestamp={self.timestamp})"


@dataclass
class MessageBatch:
    """消息批次，用于处理多个消息"""
    
    messages: List[Message] = field(default_factory=list)
    batch_id: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        
        if self.batch_id is None:
            self.batch_id = f"batch_{int(self.created_at.timestamp())}"
    
    def add_message(self, message: Message) -> None:
        """添加消息"""
        self.messages.append(message)
    
    def add_user_message(self, content: str, metadata: Dict[str, Any] = None) -> Message:
        """添加用户消息"""
        message = Message(
            role="user",
            content=content,
            metadata=metadata or {}
        )
        self.add_message(message)
        return message
    
    def add_assistant_message(self, content: str, metadata: Dict[str, Any] = None) -> Message:
        """添加助手消息"""
        message = Message(
            role="assistant",
            content=content,
            metadata=metadata or {}
        )
        self.add_message(message)
        return message
    
    def add_system_message(self, content: str, metadata: Dict[str, Any] = None) -> Message:
        """添加系统消息"""
        message = Message(
            role="system",
            content=content,
            metadata=metadata or {}
        )
        self.add_message(message)
        return message
    
    def get_messages_by_role(self, role: str) -> List[Message]:
        """根据角色获取消息"""
        return [msg for msg in self.messages if msg.role == role]
    
    def get_user_messages(self) -> List[Message]:
        """获取用户消息"""
        return self.get_messages_by_role("user")
    
    def get_assistant_messages(self) -> List[Message]:
        """获取助手消息"""
        return self.get_messages_by_role("assistant")
    
    def get_system_messages(self) -> List[Message]:
        """获取系统消息"""
        return self.get_messages_by_role("system")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "batch_id": self.batch_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "messages": [msg.to_dict() for msg in self.messages]
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MessageBatch":
        """从字典创建MessageBatch实例"""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        messages = [Message.from_dict(msg_data) for msg_data in data.get("messages", [])]
        
        return cls(
            batch_id=data.get("batch_id"),
            created_at=created_at,
            messages=messages
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "MessageBatch":
        """从JSON字符串创建MessageBatch实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)
    
    def __len__(self) -> int:
        """返回消息数量"""
        return len(self.messages)
    
    def __iter__(self):
        """迭代消息"""
        return iter(self.messages)
    
    def __getitem__(self, index: int) -> Message:
        """根据索引获取消息"""
        return self.messages[index]


