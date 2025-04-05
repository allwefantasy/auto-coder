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
    arguments: Dict[str, Any]

class PlainTextOutput(BaseModel):
    text: str


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
}


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

