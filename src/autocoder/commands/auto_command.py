from pydantic import BaseModel, Field
import byzerllm
from typing import List, Dict, Any, Union, Callable
from autocoder.common.printer import Printer
from pydantic import SkipValidation

class CommandSuggestion(BaseModel):
    command: str
    parameters: Dict[str, Any]
    confidence: float

class AutoCommandResponse(BaseModel):
    suggestions: List[CommandSuggestion]
    reasoning: str

class AutoCommandRequest(BaseModel):
    user_input: str
    conversation_history: List[Dict[str, str]]
    current_files: List[str]
    available_commands: List[str]

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
class CommandAutoTuner:
    def __init__(self, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM],
        memory_config: MemoryConfig, command_config: CommandConfig):
        self.llm = llm
        self.printer = Printer()
        self.memory_config = memory_config
        self.command_config = command_config

    @byzerllm.prompt()
    def analyze(self, request: AutoCommandRequest) -> AutoCommandResponse:
        """
        根据用户输入和当前上下文，分析并推荐最合适的命令。

        用户输入: {{ user_input }}
        当前文件列表: 
        {% for file in current_files %}
        - {{ file }}
        {% endfor %}

        可用命令列表:
        {% for cmd in available_commands %}
        - {{ cmd }}
        {% endfor %}

        历史对话:
        {% for conv in conversation_history %}
        {{ conv.role }}: {{ conv.content }}
        {% endfor %}

        请分析用户意图，一个命令执行序列，并给出推荐理由。
        返回格式必须是严格的JSON格式：
        ```json
        {
            "suggestions": [
                {
                    "command": "命令名称",
                    "parameters": {},
                    "confidence": 0.9,
                    "reasoning": "推荐理由"
                }
            ],
            "reasoning": "整体推理说明"
        }
        ```
        """

    def execute_auto_command(self, command: str, parameters: Dict[str, Any]) -> None:
        """
        执行自动生成的命令
        """    
        command_map = {
            "add_files": self.commmand_config.add_files,
            "remove_files": self.commmand_config.remove_files,
            "list_files": self.commmand_config.list_files,
            "conf": self.commmand_config.configure,
            "revert": self.commmand_config.revert,
            "commit": self.commmand_config.commit,
            "help": self.commmand_config.help,
            "exclude_dirs": self.commmand_config.exclude_dirs,
            "ask": self.commmand_config.ask,
            "chat": self.commmand_config.chat,
            "coding": self.commmand_config.coding,
            "design": self.commmand_config.design,
            "summon": self.commmand_config.summon,
            "lib": self.commmand_config.lib_command,
            "mcp": self.commmand_config.mcp
        }

        if command not in command_map:
            self.printer.print_in_terminal("auto_command_not_found", style="red", command=command)
            return

        try:
            # 将参数字典转换为命令所需的格式
            if parameters:
                command_map[command](**parameters)
            else:                
                command_map[command]()            

        except Exception as e:
            self.printer.print_in_terminal("auto_command_failed", style="red", command=command, error=str(e))