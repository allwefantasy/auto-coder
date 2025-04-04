"""
Predefined event content models using Pydantic.
These models provide structured data definitions for different event types.
"""

from typing import Dict, List, Optional, Any, Union
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict
import json


class ContentType(str, Enum):
    """内容类型枚举"""
    TEXT = "text"
    CODE = "code"
    IMAGE = "image"
    JSON = "json"
    HTML = "html"
    MARKDOWN = "markdown"


class StreamState(str, Enum):
    """流式内容的状态"""
    THINKING = "thinking"  # 思考中的内容
    CONTENT = "content"    # 正式的内容
    COMPLETE = "complete"  # 完成的标记


class BaseEventContent(BaseModel):
    """所有事件内容的基础模型"""
    timestamp: float = Field(default_factory=lambda: datetime.now().timestamp()) 
    metadata: Dict[str, Any] = Field(default_factory=dict)   
    
    model_config = ConfigDict(
        extra="allow",  # 允许额外的字段
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json()


class StreamContent(BaseEventContent):
    """
    流式内容模型
    用于表示流式传输的内容，如思考过程和正式输出
    """
    state: StreamState = StreamState.CONTENT
    content: str = ""
    content_type: ContentType = ContentType.TEXT
    sequence: int = 0  # 序列号，用于排序
    is_thinking: bool = Field(default=False, description="是否是思考过程")
    
    @field_validator('is_thinking')
    @classmethod
    def set_is_thinking(cls, v, info):
        """根据state自动设置is_thinking字段"""
        values = info.data
        if 'state' in values:
            return values['state'] == StreamState.THINKING
        return v

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "state": "content",
                "content": "正在处理请求...",
                "content_type": "text",
                "sequence": 1,
                "timestamp": 1626888000.0
            }
        }
    )


class ResultContent(BaseEventContent):
    """
    结果内容模型
    用于表示处理完成的结果
    """
    content: Any
    content_type: ContentType = ContentType.TEXT    
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "处理已完成",
                "content_type": "text",
                "metadata": {"processing_time": 1.23, "status": "success"},
                "timestamp": 1626888000.0
            }
        }
    )

## begin===============================
class ResultTokenStatContent(BaseModel):
    model_name:str = ""
    elapsed_time:float = 0.0
    first_token_time:float = 0.0
    input_tokens:int = 0
    output_tokens:int = 0
    input_cost:float = 0.0
    output_cost:float = 0.0
    speed:float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json()

class IndexBuildStartContent(BaseModel):
    file_number:int = 0
    total_files:int = 0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json()

class IndexBuildEndContent(BaseModel):
    updated_files:int = 0
    removed_files:int = 0
    input_tokens:int = 0
    output_tokens:int = 0
    input_cost:float = 0.0
    output_cost:float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json()
    


class ResultCommandPrepareStatContent(BaseModel):
    command:str = ""
    parameters:Dict[str,Any] = {}    

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json()

class ResultCommandExecuteStatContent(BaseModel):    
    command:str = ""
    content:str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json()

class ResultContextUsedContent(BaseModel):
    files:List[str] = []
    title:str = ""
    description:str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json()
    

## 最后总结性消息内容
class ResultSummaryContent(BaseModel):
    summary:str = ""    

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return self.model_dump()
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return self.model_dump_json()
    
## ResultContent.content 字段的类型
## end===============================

class MarkDownResultContent(ResultContent):
    """
    Markdown结果内容模型
    用于表示Markdown格式的处理结果
    """
    content_type: ContentType = ContentType.MARKDOWN
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "content": "# 处理结果\n处理已完成，详情如下...",
                "content_type": "markdown",
                "metadata": {"processing_time": 1.23, "status": "success"},
                "timestamp": 1626888000.0
            }
        }
    )


class AskUserContent(BaseEventContent):
    """
    询问用户的内容模型
    用于请求用户提供输入
    """
    prompt: str
    options: Optional[List[str]] = None
    default_option: Optional[str] = None
    required: bool = True
    timeout: Optional[float] = None  # 超时时间（秒）
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "prompt": "您想继续吗?",
                "options": ["是", "否"],
                "default_option": "是",
                "required": True,
                "timeout": 60.0,
                "timestamp": 1626888000.0
            }
        }
    )


class UserResponseContent(BaseEventContent):
    """
    用户响应的内容模型
    用于表示用户对询问的回应
    """
    response: str
    response_time: float = Field(default_factory=lambda: datetime.now().timestamp())
    original_prompt: Optional[str] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "response": "是",
                "response_time": 1626888030.0,
                "original_prompt": "您想继续吗?",
                "timestamp": 1626888030.0
            }
        }
    )


# 扩展的内容类型

class CodeContent(StreamContent):
    """代码内容模型"""
    content_type: ContentType = ContentType.CODE
    language: str = "python"  # 代码语言
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "state": "content",
                "content": "def hello():\n    print('Hello, world!')",
                "content_type": "code",
                "language": "python",
                "sequence": 1,
                "timestamp": 1626888000.0
            }
        }
    )


class MarkdownContent(StreamContent):
    """Markdown内容模型"""
    content_type: ContentType = ContentType.MARKDOWN
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "state": "content",
                "content": "# 标题\n这是一段Markdown内容",
                "content_type": "markdown",
                "sequence": 1,
                "timestamp": 1626888000.0
            }
        }
    )


class ErrorContent(BaseEventContent):
    """错误内容模型"""
    error_code: str
    error_message: str
    details: Optional[Dict[str, Any]] = None
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error_code": "E1001",
                "error_message": "处理失败",
                "details": {"location": "process_data", "reason": "invalid input"},
                "timestamp": 1626888000.0
            }
        }
    )


class CompletionContent(BaseEventContent):
    """
    完成内容模型
    用于表示事件或操作正常完成的情况
    """
    success_code: str
    success_message: str
    result: Optional[Any] = None
    details: Optional[Dict[str, Any]] = None
    completion_time: float = Field(default_factory=lambda: datetime.now().timestamp())
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success_code": "S1001",
                "success_message": "操作成功完成",
                "result": {"items_processed": 50, "warnings": 0},
                "details": {"operation": "data_sync", "duration": 120.5},
                "timestamp": 1626888000.0,
                "completion_time": 1626888000.0
            }
        }
    )


# 工厂函数，便于创建各种内容
def create_stream_thinking(content: str, sequence: int = 0, metadata: Dict[str, Any] = {}) -> StreamContent:
    """创建思考中的流式内容"""
    return StreamContent(
        state=StreamState.THINKING,
        content=content,
        sequence=sequence,
        is_thinking=True,
        metadata=metadata
    )


def create_stream_content(content: str, sequence: int = 0, metadata: Dict[str, Any] = {}) -> StreamContent:
    """创建正式的流式内容"""
    return StreamContent(
        state=StreamState.CONTENT,
        content=content,
        sequence=sequence,
        is_thinking=False,
        metadata=metadata
    )


def create_result(content: Any, metadata: Dict[str, Any] = None) -> ResultContent:
    """创建结果内容"""
    return ResultContent(
        content=content,
        metadata=metadata or {}
    )


def create_markdown_result(content: str, metadata: Dict[str, Any] = None) -> MarkDownResultContent:
    """
    创建Markdown结果内容
    
    Args:
        content: Markdown格式的内容
        metadata: 元数据信息
        
    Returns:
        MarkDownResultContent 实例
    """
    return MarkDownResultContent(
        content=content,
        metadata=metadata or {}
    )


def create_ask_user(prompt: str, options: List[str] = None) -> AskUserContent:
    """创建询问用户的内容"""
    return AskUserContent(
        prompt=prompt,
        options=options
    )


def create_user_response(response: str, original_prompt: str = None) -> UserResponseContent:
    """创建用户响应的内容"""
    return UserResponseContent(
        response=response,
        original_prompt=original_prompt
    )


def create_completion(success_code: str, success_message: str, result: Any = None, details: Dict[str, Any] = None) -> CompletionContent:
    """
    创建完成内容
    
    Args:
        success_code: 成功代码
        success_message: 成功信息
        result: 操作结果
        details: 详细信息
        
    Returns:
        CompletionContent 实例
    """
    return CompletionContent(
        success_code=success_code,
        success_message=success_message,
        result=result,
        details=details or {}
    )


def create_error(error_code: str, error_message: str, details: Dict[str, Any] = None) -> ErrorContent:
    """
    创建错误内容
    
    Args:
        error_code: 错误代码
        error_message: 错误信息
        details: 详细错误信息
        
    Returns:
        ErrorContent 实例
    """
    return ErrorContent(
        error_code=error_code,
        error_message=error_message,
        details=details or {}
    ) 