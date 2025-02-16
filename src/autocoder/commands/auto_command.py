import json
import os
import time
from pydantic import BaseModel, Field
import byzerllm
from typing import List, Dict, Any, Union, Callable
from autocoder.common.printer import Printer
from pydantic import SkipValidation


class CommandMessage(BaseModel):
    role: str
    content: str


class ExtendedCommandMessage(BaseModel):
    message: CommandMessage
    timestamp: str


class CommandConversation(BaseModel):
    history: Dict[str, ExtendedCommandMessage]
    current_conversation: List[CommandMessage]


def save_to_memory_file(query: str, response: str):
    """Save command conversation to memory file using CommandConversation structure"""
    memory_dir = os.path.join(".auto-coder", "memory")
    os.makedirs(memory_dir, exist_ok=True)
    file_path = os.path.join(memory_dir, "command_chat_history.json")

    # Create new message objects
    user_msg = CommandMessage(role="user", content=query)
    assistant_msg = CommandMessage(role="assistant", content=response)

    extended_user_msg = ExtendedCommandMessage(
        message=user_msg,
        timestamp=str(int(time.time()))
    )
    extended_assistant_msg = ExtendedCommandMessage(
        message=assistant_msg,
        timestamp=str(int(time.time()))
    )

    # Load existing conversation or create new
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                existing_conv = CommandConversation.model_validate_json(
                    f.read())
            except Exception:
                existing_conv = CommandConversation(
                    history={},
                    current_conversation=[]
                )
    else:
        existing_conv = CommandConversation(
            history={},
            current_conversation=[]
        )

    existing_conv.current_conversation.append(extended_user_msg)
    existing_conv.current_conversation.append(extended_assistant_msg)
    # Save updated conversation
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(existing_conv.model_dump_json(indent=2))


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
    def _analyze(self, request: AutoCommandRequest) -> AutoCommandResponse:
        """
        根据用户输入和当前上下文，分析并推荐最合适的命令。

        用户输入: {{ user_input }}

        {% if current_files %}
        当前文件列表: 
        {% for file in current_files %}
        - {{ file }}
        {% endfor %}
        {% endif %}
        
        可用命令列表:
        {% for cmd in available_commands %}
        - {{ cmd }}
        {% endfor %}

        {% if conversation_history %}
        历史对话:
        {% for conv in conversation_history %}
        {{ conv.role }}: {{ conv.content }}
        {% endfor %}
        {% endif %}

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
        return {
            "user_input": request.user_input,
            "current_files": request.current_files,
            "conversation_history": request.conversation_history,
            "available_commands": ""
        }

    def analyze(self, request: AutoCommandRequest) -> AutoCommandResponse:
        response = self._analyze.with_llm(self.llm).with_return_type(AutoCommandResponse).run(request)
        save_to_memory_file(
            query=request.user_input,
            response=response.model_dump_json(indent=2)
        )
        return response
    
    @byzerllm.prompt()
    def _command_readme(self) -> str:
        '''
        # 命令说明
        <commands>
        
        <command>
        <name>add_files</name>
        <description>添加文件到当前会话。支持通过模式匹配添加文件。</description>
        <parameters>
        <parameter>
        <name>/refresh</name>
        <description>刷新文件列表</description>
        </parameter>
        <parameter>
        <name>/group</name>
        <description>文件分组管理，支持子指令：
        /add &lt;组名&gt; - 创建新组
        /drop &lt;组名&gt; - 删除组
        /set &lt;组名&gt; - 设置组描述
        /list - 列出所有组
        /reset - 重置当前活跃组
        </description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>remove_files</name>
        <description>从当前会话中移除文件</description>
        <parameters>
        <parameter>
        <name>/all</name>
        <description>移除所有文件</description>
        </parameter>
        <parameter>
        <name>file_names</name>
        <description>要移除的文件名列表，用逗号分隔</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>list_files</name>
        <description>列出当前会话中的所有文件</description>
        </command>

        <command>
        <name>conf</name>
        <description>配置管理命令</description>
        <parameters>
        <parameter>
        <name>/drop &lt;key&gt;</name>
        <description>删除指定配置项</description>
        </parameter>
        <parameter>
        <name>&lt;key&gt;:&lt;value&gt;</name>
        <description>设置配置项</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>revert</name>
        <description>撤销最后一次代码修改</description>
        </command>

        <command>
        <name>commit</name>
        <description>提交代码更改</description>
        </command>

        <command>
        <name>help</name>
        <description>显示帮助信息</description>
        </command>

        <command>
        <name>exclude_dirs</name>
        <description>设置排除目录</description>
        <parameters>
        <parameter>
        <name>dir_names</name>
        <description>要排除的目录列表，用逗号分隔</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>ask</name>
        <description>向AI提问</description>
        <parameters>
        <parameter>
        <name>query</name>
        <description>问题内容</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>chat</name>
        <description>进入聊天模式</description>
        <parameters>
        <parameter>
        <name>query</name>
        <description>聊天内容</description>
        </parameter>
        <parameter>
        <name>/new</name>
        <description>开启新的聊天会话</description>
        </parameter>
        <parameter>
        <name>/no_context</name>
        <description>不使用上下文</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>coding</name>
        <description>代码生成命令</description>
        <parameters>
        <parameter>
        <name>query</name>
        <description>代码生成需求描述</description>
        </parameter>
        <parameter>
        <name>/apply</name>
        <description>应用上次生成的代码</description>
        </parameter>
        <parameter>
        <name>/next</name>
        <description>预测下一步任务</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>design</name>
        <description>设计相关命令</description>
        <parameters>
        <parameter>
        <name>query</name>
        <description>设计需求描述</description>
        </parameter>
        <parameter>
        <name>/svg</name>
        <description>生成SVG设计</description>
        </parameter>
        <parameter>
        <name>/sd</name>
        <description>生成Stable Diffusion设计</description>
        </parameter>
        <parameter>
        <name>/logo</name>
        <description>生成Logo设计</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>summon</name>
        <description>调用AI工具</description>
        <parameters>
        <parameter>
        <name>query</name>
        <description>工具调用需求描述</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>lib</name>
        <description>库管理命令</description>
        <parameters>
        <parameter>
        <name>/add &lt;库名&gt;</name>
        <description>添加新库</description>
        </parameter>
        <parameter>
        <name>/remove &lt;库名&gt;</name>
        <description>移除库</description>
        </parameter>
        <parameter>
        <name>/list</name>
        <description>列出所有库</description>
        </parameter>
        <parameter>
        <name>/set-proxy &lt;代理地址&gt;</name>
        <description>设置库下载代理</description>
        </parameter>
        <parameter>
        <name>/refresh</name>
        <description>刷新库列表</description>
        </parameter>
        <parameter>
        <name>/get &lt;包名&gt;</name>
        <description>获取包的文档</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>mcp</name>
        <description>模型控制面板命令</description>
        <parameters>
        <parameter>
        <name>/add &lt;模型配置&gt;</name>
        <description>添加新模型</description>
        </parameter>
        <parameter>
        <name>/remove &lt;模型名&gt;</name>
        <description>移除模型</description>
        </parameter>
        <parameter>
        <name>/list</name>
        <description>列出所有模型</description>
        </parameter>
        <parameter>
        <name>/list_running</name>
        <description>列出正在运行的模型</description>
        </parameter>
        <parameter>
        <name>/refresh &lt;模型名&gt;</name>
        <description>刷新模型</description>
        </parameter>
        </parameters>
        </command>

        </commands>
        '''


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
            "lib": self.commmand_config.lib,
            "mcp": self.commmand_config.mcp
        }

        if command not in command_map:
            self.printer.print_in_terminal(
                "auto_command_not_found", style="red", command=command)
            return

        try:
            # 将参数字典转换为命令所需的格式
            if parameters:
                command_map[command](**parameters)
            else:
                command_map[command]()            

        except Exception as e:
            error_msg = str(e)
            self.printer.print_in_terminal(
                "auto_command_failed", style="red", command=command, error=error_msg)

            # Save failed command execution
            save_to_memory_file(
                query=f"Command: {command} Parameters: {json.dumps(parameters) if parameters else 'None'}",
                response=f"Command execution failed: {error_msg}"
            )
