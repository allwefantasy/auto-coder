from pydantic import BaseModel, Field
import byzerllm
from typing import List, Dict, Any
from autocoder.common.printer import Printer

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

class CommandAutoTuner:
    def __init__(self, llm: byzerllm.ByzerLLM):
        self.llm = llm
        self.printer = Printer()
        
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

        请生成最适合完成用户请求的命令序列，按置信度排序。
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

def execute_auto_command(command: str, params: dict, memory: dict):
    """执行生成的命令"""
    from autocoder.chat_auto_coder import (
        coding, chat, add_files, remove_files, 
        index_build, index_query, list_files, 
        exclude_dirs, commit, revert, ask, 
        summon, design, mcp, models
    )
    
    command_map = {
        "coding": coding,
        "chat": chat,
        "add_files": add_files,
        "remove_files": remove_files,
        "index_build": index_build,
        "index_query": index_query,
        "list_files": list_files,
        "exclude_dirs": exclude_dirs,
        "commit": commit,
        "revert": revert,
        "ask": ask,
        "summon": summon,
        "design": design,
        "mcp": mcp,
        "models": models
    }
    
    printer = Printer()
    
    # 安全检查
    DANGEROUS_COMMANDS = ["rm", "drop", "shell"]
    if any(cmd in command for cmd in DANGEROUS_COMMANDS):
        printer.print_in_terminal("auto_command_dangerous", style="red", command=command)
        return
    
    if command in command_map:
        # 构造模拟参数
        args = " ".join([f"--{k} {v}" for k,v in params.items()])
        full_command = f"/{command} {args}"
        
        # 记录自动执行日志
        memory["conversation"].append({
            "role": "system",
            "content": f"Auto executing: {full_command}"
        })
        
        # 调用实际处理函数
        try:
            command_map[command](args.split())
            printer.print_in_terminal("auto_command_success", style="green", command=full_command)
        except Exception as e:
            printer.print_in_terminal("auto_command_execute_error", style="red", command=full_command, error=str(e))
    else:
        printer.print_in_terminal("auto_command_unknown", style="yellow", command=command)