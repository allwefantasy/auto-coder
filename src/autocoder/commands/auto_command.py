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
        
        