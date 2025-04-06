"""
Event type definitions for the event system.
"""

from enum import Enum, auto
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field
import uuid
import time
import json
from pydantic import BaseModel

class EventType(Enum):
    """Event types supported by the system"""
    RESULT = auto()  # 结果数据
    STREAM = auto()  # 流式数据
    ASK_USER = auto()  # 请求用户输入
    USER_RESPONSE = auto()  # 用户响应    
    ERROR = auto()  # 错误事件
    COMPLETION = auto()  # 完成事件


@dataclass
class Event:
    """
    Base event class for all events in the system.
    """
    event_type: EventType
    timestamp: float = field(default_factory=time.time)
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization"""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.name,
            "timestamp": self.timestamp,
            "content": self.content,
            "metadata": self.metadata
        }
    
    def to_json(self) -> str:
        """Convert event to JSON string"""
        return json.dumps(self.to_dict(),ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create event from dictionary"""
        event_type = EventType[data["event_type"]]
        return cls(
            event_type=event_type,
            event_id=data.get("event_id", str(uuid.uuid4())),
            timestamp=data.get("timestamp", time.time()),
            content=data.get("content", {}),
            metadata=data.get("metadata", {})
        )
    
    @classmethod
    def from_json(cls, json_str: str) -> "Event":
        """Create event from JSON string"""
        return cls.from_dict(json.loads(json_str))


class EventMetadata(BaseModel):
    action_file: str = field(default="") # 关联 auto-coder 中的action文件
    stream_out_type: str = field(default="") # 标记，比如当前这个流式是用于什么场景的，比如用于产生命令的还是啥
    is_streaming: bool = field(default=False) # 是否是流式输出
    output: str = field(default="") # result or delta, 在流式里，我们也可能会输出 ResultContent 类型
    path: str = field(default="") # 唯一路径，比如 /agent/edit/tool/call

    def to_dict(self) -> Dict[str, Any]:
        """Convert event metadata to dictionary for serialization"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """Convert event metadata to JSON string"""
        return json.dumps(self.to_dict(),ensure_ascii=False)

@dataclass
class ResponseEvent(Event):
    """
    Event representing a response to another event.
    """
    response_to: str = field(default="")  # event_id of the event this is responding to
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response event to dictionary for serialization"""
        data = super().to_dict()
        data["response_to"] = self.response_to
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ResponseEvent":
        """Create response event from dictionary"""
        event = super().from_dict(data)
        return cls(
            event_type=event.event_type,
            event_id=event.event_id,
            timestamp=event.timestamp,
            content=event.content,
            response_to=data.get("response_to", "")
        ) 