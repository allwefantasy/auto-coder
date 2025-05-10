from pydantic import BaseModel
from typing import List, Dict, Any, Callable, Optional, Type
from pydantic import SkipValidation

# Result class used by Tool Resolvers
class ToolResult(BaseModel):
    success: bool
    message: str
    content: Any = None # Can store file content, command output, etc.

# Pydantic Models for Tools
class BaseTool(BaseModel):
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

class ListCodeDefinitionNamesTool(BaseTool):
    path: str

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

class ListPackageInfoTool(BaseTool):
    path: str  # 源码包目录，相对路径或绝对路径

# Event Types for Rich Output Streaming
class LLMOutputEvent(BaseModel):
    """Represents plain text output from the LLM."""
    text: str

class LLMThinkingEvent(BaseModel):
    """Represents text within <thinking> tags from the LLM."""
    text: str

class ToolCallEvent(BaseModel):
    """Represents the LLM deciding to call a tool."""
    tool: SkipValidation[BaseTool] # Use SkipValidation as BaseTool itself is complex
    tool_xml: str

class ToolResultEvent(BaseModel):
    """Represents the result of executing a tool."""
    tool_name: str
    result: ToolResult

class TokenUsageEvent(BaseModel):
    """Represents the result of executing a tool."""
    usage: Any

class PlanModeRespondEvent(BaseModel):
    """Represents the LLM attempting to complete the task."""
    completion: SkipValidation[PlanModeRespondTool] # Skip validation
    completion_xml: str

class CompletionEvent(BaseModel):
    """Represents the LLM attempting to complete the task."""
    completion: SkipValidation[AttemptCompletionTool] # Skip validation
    completion_xml: str

class ErrorEvent(BaseModel):
    """Represents an error during the process."""
    message: str

class WindowLengthChangeEvent(BaseModel):
    """Represents the token usage in the conversation window."""
    tokens_used: int

# Deprecated: Will be replaced by specific Event types
# class PlainTextOutput(BaseModel):
#     text: str


# Mapping from tool tag names to Pydantic models
TOOL_MODEL_MAP: Dict[str, Type[BaseTool]] = {
    "execute_command": ExecuteCommandTool,
    "read_file": ReadFileTool,
    "write_to_file": WriteToFileTool,
    "replace_in_file": ReplaceInFileTool,
    "search_files": SearchFilesTool,
    "list_files": ListFilesTool,
    "list_code_definition_names": ListCodeDefinitionNamesTool,
    "ask_followup_question": AskFollowupQuestionTool,
    "attempt_completion": AttemptCompletionTool,
    "plan_mode_respond": PlanModeRespondTool,
    "use_mcp_tool": UseMcpTool,
    "list_package_info": ListPackageInfoTool,    
}

class FileChangeEntry(BaseModel):
    type: str  # 'added' or 'modified'
    diffs: List[str] = []
    content: Optional[str] = None


class AgenticEditRequest(BaseModel):
    user_input: str


class FileOperation(BaseModel):
    path: str
    operation: str  # e.g., "MODIFY", "REFERENCE", "ADD", "REMOVE"
class MemoryConfig(BaseModel):
    """
    A model to encapsulate memory configuration and operations.
    """

    memory: Dict[str, Any]
    save_memory_func: SkipValidation[Callable]

    class Config:
        arbitrary_types_allowed = True


class CommandConfig(BaseModel):
    coding: SkipValidation[Callable]
    chat: SkipValidation[Callable]
    add_files: SkipValidation[Callable]
    remove_files: SkipValidation[Callable]
    index_build: SkipValidation[Callable]
    index_query: SkipValidation[Callable]
    list_files: SkipValidation[Callable]
    ask: SkipValidation[Callable]
    revert: SkipValidation[Callable]
    commit: SkipValidation[Callable]
    help: SkipValidation[Callable]
    exclude_dirs: SkipValidation[Callable]
    summon: SkipValidation[Callable]
    design: SkipValidation[Callable]
    mcp: SkipValidation[Callable]
    models: SkipValidation[Callable]
    lib: SkipValidation[Callable]
    execute_shell_command: SkipValidation[Callable]
    generate_shell_command: SkipValidation[Callable]
    conf_export: SkipValidation[Callable]
    conf_import: SkipValidation[Callable]
    index_export: SkipValidation[Callable]
    index_import: SkipValidation[Callable]
    exclude_files: SkipValidation[Callable]

