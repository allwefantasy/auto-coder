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
    summon: SkipValidation[Callable]
    design: SkipValidation[Callable]
    mcp: SkipValidation[Callable]
    models: SkipValidation[Callable]

    
class CommandAutoTuner:
    def __init__(self, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM],
        memory_config:MemoryConfig, command_config:CommandConfig):
        self.llm = llm
        self.printer = Printer()
        self.memory_config = memory_config
        self.commmand_config = command_config

    def command_readme(self) -> str:
        """
        # 命令说明
        ## /chat: 进入配置对话模式
        ## /coding: 进入代码生成模式
        ## /add_files: 添加文件
        ## /remove_files: 删除文件
        ## /index_build: 构建索引
        ## /index_query: 查询索引
        ## /list_files: 列出文件
        ## /exclude_dirs: 排除目录
        ## /commit: 提交代码
        ## /revert: 回滚代码
        ## /ask: 询问问题
        ## /summon: 召唤模型
        ## /design: 设计代码
        ## /mcp: 多文件代码生成
        ## /models: 查看模型列表        
        """
        
        
    @byzerllm.prompt()
    def _generate_command_str(self, request: AutoCommandRequest) -> str:
        """
        根据用户请求和历史对话，生成推荐命令的JSON结构：

        可用命令列表: {{ available_commands }}
        当前文件列表: {{ current_files|length }}个文件
        
        用户输入: {{ user_input }}
        历史对话: 
        {% for msg in conversation_history %}
        {{ msg.role }}: {{ msg.content }}
        {% endfor %}

        请生成最适合完成用户请求的命令序列，按置信度排序。输出 json 格式如下：

        ```json
        {
            "suggestions": [
                {
                    "command": "命令名称",
                    "parameters": "命令参数",
                    "confidence": 置信度
                }
            ],
            "reasoning": "推理过程"
        }
        ```



        请遵循以下规则：
        1. 优先使用已有命令，不要创造新命令
        2. 参数格式必须符合目标命令的要求
        3. 对文件操作命令需要检查文件是否存在
        4. 复杂任务分解为多个命令序列
        5. 需要用户确认危险操作
        """

    def analyze(self, request: AutoCommandRequest) -> AutoCommandResponse:
        try:
            generated = self._generate_command_str(request)
            return AutoCommandResponse.model_validate_json(generated)
        except Exception as e:
            self.printer.print_in_terminal("auto_command_error", style="red", error=str(e))
            return AutoCommandResponse(suggestions=[], reasoning="Failed to generate commands")

    def execute_auto_command(self, command: str, params: dict):
            
        printer = Printer()
        
        # 安全检查
        DANGEROUS_COMMANDS = ["rm", "drop", "shell"]
        
        if any(cmd in command for cmd in DANGEROUS_COMMANDS):
            printer.print_in_terminal("auto_command_dangerous", style="red", command=command)
            return
        
        
from typing import List, Dict, Any
from pydantic import BaseModel, Field
from autocoder.common.printer import Printer
from autocoder.utils.llms import get_single_llm

class CommandSuggestion(BaseModel):
    command: str = Field(..., description="建议的命令")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="命令参数")
    confidence: float = Field(..., description="置信度")
    reasoning: str = Field(..., description="推荐理由")

class AutoCommandRequest(BaseModel):
    user_input: str = Field(..., description="用户输入")
    conversation_history: List[Dict[str, Any]] = Field(default_factory=list, description="对话历史")
    current_files: List[str] = Field(default_factory=list, description="当前文件列表")
    available_commands: List[str] = Field(default_factory=list, description="可用命令列表")

class AutoCommandResponse(BaseModel):
    suggestions: List[CommandSuggestion] = Field(default_factory=list, description="建议列表")
    reasoning: str = Field("No suggestions", description="整体推理说明")

class CommandAutoTuner:
    def __init__(self, llm):
        self.llm = llm
        self.printer = Printer()

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

        请分析用户意图，推荐1-3个最合适的命令，并给出推荐理由。
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
        from autocoder.chat_auto_coder import (
            add_files, remove_files, list_files, configure,
            revert, commit, help, exclude_dirs, ask, chat,
            coding, design, summon, lib_command, mcp
        )

        command_map = {
            "add_files": add_files,
            "remove_files": remove_files,
            "list_files": list_files,
            "conf": configure,
            "revert": revert,
            "commit": commit,
            "help": help,
            "exclude_dirs": exclude_dirs,
            "ask": ask,
            "chat": chat,
            "coding": coding,
            "design": design,
            "summon": summon,
            "lib": lib_command,
            "mcp": mcp
        }

        if command not in command_map:
            self.printer.print_in_terminal("auto_command_not_found", style="red", command=command)
            return

        try:
            # 将参数字典转换为命令所需的格式
            if parameters:
                args = []
                for k, v in parameters.items():
                    if isinstance(v, bool):
                        if v:
                            args.append(f"--{k}")
                    else:
                        args.append(f"--{k}")
                        args.append(str(v))
            else:
                args = []

            # 执行命令
            command_map[command](args)
            self.printer.print_in_terminal("auto_command_success", style="green", command=command)

        except Exception as e:
            self.printer.print_in_terminal("auto_command_failed", style="red", command=command, error=str(e))