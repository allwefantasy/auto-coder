from pydantic import BaseModel, SkipValidation
from typing import List, Dict, Any, Optional, Type, Union, Tuple, Generator, Literal


# 工具结果类，由工具解析器使用
class ToolResult(BaseModel):
    """
    工具执行结果
    """
    success: bool = False  # 执行是否成功
    message: str = ""  # 结果消息
    content: Any = None  # 返回内容，可以是任何类型


# 工具的基本Pydantic模型
class BaseTool(BaseModel):
    """
    代理工具的基类，所有工具类都应继承此类
    """
    pass


class ExecuteCommandTool(BaseTool):
    command: str
    requires_approval: bool

class ReadFileTool(BaseTool):
    path: str

class WriteToFileTool(BaseTool):
    path: str
    content: str

class ReplaceInFileTool(BaseTool):
    path: str
    diff: str

class SearchFilesTool(BaseTool):
    path: str
    regex: str
    file_pattern: Optional[str] = None

class ListFilesTool(BaseTool):
    path: str
    recursive: Optional[bool] = False

class AskFollowupQuestionTool(BaseTool):
    question: str
    options: Optional[List[str]] = None

class AttemptCompletionTool(BaseTool):
    result: str
    command: Optional[str] = None

class PlanModeRespondTool(BaseTool):
    response: str
    options: Optional[List[str]] = None

class UseMcpTool(BaseTool):
    server_name: str
    tool_name: str
    query:str  

class TalkToTool(BaseTool):
    agent_name: str
    content: str
    mentions: List[str] = []
    print_conversation: bool = False

class TalkToGroupTool(BaseTool):
    group_name: str
    content: str
    mentions: List[str] = []
    print_conversation: bool = False


# 工具指南相关类型
class ToolDescription(BaseModel):
    """
    工具描述
    """
    description: str  # 工具描述内容    


class ToolExample(BaseModel):
    """
    工具使用示例
    """
    title: str  # 示例标题
    body: str   # 示例内容


class RoleDescription(BaseModel):
    """
    代理角色描述
    """
    agent_type: str  # 代理类型
    description: str  # 角色描述


# 事件类型，用于流式输出
class LLMOutputEvent(BaseModel):
    """表示来自LLM的纯文本输出"""
    text: str


class LLMThinkingEvent(BaseModel):
    """表示来自LLM的<thinking>标签内的文本"""
    text: str


class ToolCallEvent(BaseModel):
    """表示LLM决定调用工具"""
    tool: SkipValidation[BaseTool]  # 使用SkipValidation因为BaseTool本身很复杂
    tool_xml: str


class ToolResultEvent(BaseModel):
    """表示执行工具的结果"""
    tool_name: str
    result: ToolResult


class TokenUsageEvent(BaseModel):
    """表示Token使用情况"""
    usage: Any


class CompletionEvent(BaseModel):
    """表示LLM尝试完成任务"""
    completion: Any  # 完成的工具，使用Any以避免循环导入
    completion_xml: str


class ErrorEvent(BaseModel):
    """表示过程中的错误"""
    message: str

class PlanModeRespondEvent(BaseModel):
    """Represents the LLM attempting to complete the task."""
    completion: SkipValidation[PlanModeRespondTool] # Skip validation
    completion_xml: str    


# 工具执行中的事件类型联合
AgentEvent = Union[
    LLMOutputEvent,
    LLMThinkingEvent,
    ToolCallEvent,
    ToolResultEvent,
    TokenUsageEvent,
    CompletionEvent,
    ErrorEvent,
    PlanModeRespondEvent
]


# 文件变更记录
class FileChangeEntry(BaseModel):
    """
    文件变更条目，用于记录文件的变更信息
    """
    type: str  # 'added' 或 'modified'
    diffs: List[str] = []  # 使用 replace_in_file 时，记录 diff 内容
    content: Optional[str] = None  # 使用 write_to_file 时，记录文件内容


# 代理编辑请求
class AgentRequest(BaseModel):
    """
    代理请求
    """
    user_input: str 


class Message(BaseModel):
    sender: str
    content: str
    mentions: List[str] = []
    is_group: bool = False
    group_name: Optional[str] = None
    reply_config: Dict[str, Any] = {}

class ReplyDecision(BaseModel):
    content: str
    strategy: Literal["broadcast", "private", "ignore"] 
    mentions: List[str] = []
    priority: int = 0
    reason: str = ""