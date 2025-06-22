



"""
Auto-Coder SDK 响应模型

定义各种响应数据结构，包括CLI结果、会话信息等。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

from ..constants import CLI_EXIT_SUCCESS, CLI_EXIT_ERROR


@dataclass
class CLIResult:
    """CLI执行结果"""
    
    success: bool
    output: str
    error: Optional[str] = None
    exit_code: int = CLI_EXIT_SUCCESS
    debug_info: Optional[Dict[str, Any]] = None
    execution_time: Optional[float] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.success and self.exit_code == CLI_EXIT_SUCCESS:
            self.exit_code = CLI_EXIT_ERROR
    
    @classmethod
    def success_result(cls, output: str, debug_info: Optional[Dict[str, Any]] = None) -> "CLIResult":
        """创建成功结果"""
        return cls(
            success=True,
            output=output,
            debug_info=debug_info
        )
    
    @classmethod
    def error_result(cls, error: str, exit_code: int = CLI_EXIT_ERROR, debug_info: Optional[Dict[str, Any]] = None) -> "CLIResult":
        """创建错误结果"""
        return cls(
            success=False,
            output="",
            error=error,
            exit_code=exit_code,
            debug_info=debug_info
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error,
            "exit_code": self.exit_code,
            "debug_info": self.debug_info,
            "execution_time": self.execution_time
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class SessionInfo:
    """会话信息"""
    
    session_id: str
    name: Optional[str] = None
    created_at: Optional[datetime] = None
    last_updated: Optional[datetime] = None
    message_count: int = 0
    status: str = "active"  # active, archived, deleted
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        """初始化后处理"""
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.last_updated is None:
            self.last_updated = self.created_at
    
    def update_timestamp(self) -> None:
        """更新最后修改时间"""
        self.last_updated = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "session_id": self.session_id,
            "name": self.name,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "message_count": self.message_count,
            "status": self.status,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SessionInfo":
        """从字典创建SessionInfo实例"""
        created_at = None
        if data.get("created_at"):
            created_at = datetime.fromisoformat(data["created_at"])
        
        last_updated = None
        if data.get("last_updated"):
            last_updated = datetime.fromisoformat(data["last_updated"])
        
        return cls(
            session_id=data["session_id"],
            name=data.get("name"),
            created_at=created_at,
            last_updated=last_updated,
            message_count=data.get("message_count", 0),
            status=data.get("status", "active"),
            metadata=data.get("metadata", {})
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "SessionInfo":
        """从JSON字符串创建SessionInfo实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class QueryResult:
    """查询结果"""
    
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: Optional[datetime] = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "QueryResult":
        """从字典创建QueryResult实例"""
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])
        
        return cls(
            content=data["content"],
            metadata=data.get("metadata", {}),
            timestamp=timestamp,
            session_id=data.get("session_id")
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def from_json(cls, json_str: str) -> "QueryResult":
        """从JSON字符串创建QueryResult实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class StreamEvent:
    """流式事件"""
    
    event_type: str  # start, content, end, error
    data: Any
    timestamp: Optional[datetime] = None
    session_id: Optional[str] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.timestamp is None:
            self.timestamp = datetime.now()
    
    @classmethod
    def start_event(cls, session_id: Optional[str] = None) -> "StreamEvent":
        """创建开始事件"""
        return cls(
            event_type="start",
            data={"status": "started"},
            session_id=session_id
        )
    
    @classmethod
    def content_event(cls, content: str, session_id: Optional[str] = None) -> "StreamEvent":
        """创建内容事件"""
        return cls(
            event_type="content",
            data={"content": content},
            session_id=session_id
        )
    
    @classmethod
    def end_event(cls, session_id: Optional[str] = None) -> "StreamEvent":
        """创建结束事件"""
        return cls(
            event_type="end",
            data={"status": "completed"},
            session_id=session_id
        )
    
    @classmethod
    def error_event(cls, error: str, session_id: Optional[str] = None) -> "StreamEvent":
        """创建错误事件"""
        return cls(
            event_type="error",
            data={"error": error},
            session_id=session_id
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "session_id": self.session_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StreamEvent":
        """从字典创建StreamEvent实例"""
        timestamp = None
        if data.get("timestamp"):
            timestamp = datetime.fromisoformat(data["timestamp"])
        
        return cls(
            event_type=data["event_type"],
            data=data["data"],
            timestamp=timestamp,
            session_id=data.get("session_id")
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "StreamEvent":
        """从JSON字符串创建StreamEvent实例"""
        data = json.loads(json_str)
        return cls.from_dict(data)


@dataclass
class CodeModificationResult:
    """代码修改结果"""
    success: bool
    message: str
    modified_files: List[str] = field(default_factory=list)
    created_files: List[str] = field(default_factory=list)
    deleted_files: List[str] = field(default_factory=list)
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
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CodeModificationResult":
        """从字典创建实例"""
        return cls(
            success=data.get("success", False),
            message=data.get("message", ""),
            modified_files=data.get("modified_files", []),
            created_files=data.get("created_files", []),
            deleted_files=data.get("deleted_files", []),
            error_details=data.get("error_details"),
            metadata=data.get("metadata", {})
        )
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)



