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
        <description>添加文件到当前会话。支持通过模式匹配添加文件，支持 glob 语法，例如 *.py。可以使用相对路径或绝对路径。</description>
        <usage>
         该方法只有一个参数 args，args 是一个列表，列表的元素是字符串。会包含子指令，例如 
         
         add_files(args=["/refresh"]) 
        
         会刷新文件列表。下面是常见的子指令：

         ## /refresh 刷新文件列表
         刷新文件列表

         ## /group 文件分组管理 

         ### /add 
         创建新组并将当前文件列表保存到该组。
         使用例子：

         /group /add my_group

         ### /drop
         删除指定组及其文件列表
         使用例子：

         /group /drop my_group

         ### /set
         设置组的描述信息，用于说明该组的用途
         使用例子：

         /group /set my_group "用于说明该组的用途"

         ### /list
         列出所有已定义的组及其文件
         使用例子：

         /group /list

         ### /reset
         重置当前活跃组，但保留文件列表
         使用例子：         
         /group /reset

        </usage>        
        </command>

        <command>
        <name>remove_files</name>
        <description>从当前会话中移除文件。可以指定多个文件，支持文件名或完整路径。</description>
        <parameters>
        <parameter>
        <name>/all</name>
        <description>移除所有当前会话中的文件，同时清空活跃组列表。</description>
        </parameter>
        <parameter>
        <name>file_names</name>
        <description>要移除的文件名列表，多个文件用逗号分隔。可以使用文件名或完整路径。</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>list_files</name>
        <description>列出当前会话中的所有文件，显示相对于项目根目录的路径。</description>
        </command>

        <command>
        <name>conf</name>
        <description>配置管理命令，用于设置和管理系统配置项。</description>
        <parameters>
        <parameter>
        <name>/drop key</name>
        <description>删除指定配置项。例如：/conf /drop model 删除模型配置。</description>
        </parameter>
        <parameter>
        <name>key:value</name>
        <description>设置配置项。支持以下关键配置：
        - model: 设置默认使用的模型，例如：model:v3_chat
        - chat_model: 设置聊天使用的模型
        - code_model: 设置代码生成使用的模型
        - auto_merge: 代码合并方式(editblock/diff/wholefile)
        - editblock_similarity: 编辑块相似度阈值(0-1)
        - skip_build_index: 是否跳过索引构建(true/false)
        - skip_filter_index: 是否跳过索引过滤(true/false)
        - human_as_model: 是否将人类作为模型(true/false)
        </description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>revert</name>
        <description>撤销最后一次代码修改，恢复到修改前的状态。同时会删除对应的操作记录文件。</description>
        </command>

        <command>
        <name>commit</name>
        <description>提交代码更改到版本控制系统。系统会自动生成合适的提交信息，并创建提交记录。</description>
        </command>

        <command>
        <name>help</name>
        <description>显示帮助信息。可以加上具体的查询内容获取特定帮助，例如：/help auto_merge</description>
        </command>

        <command>
        <name>exclude_dirs</name>
        <description>设置要排除的目录，这些目录下的文件将不会被索引和处理。</description>
        <parameters>
        <parameter>
        <name>dir_names</name>
        <description>要排除的目录列表，多个目录用逗号分隔。例如：node_modules,dist,build</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>ask</name>
        <description>向AI提问，获取关于代码或项目的解答。会考虑当前会话中的文件作为上下文。</description>
        <parameters>
        <parameter>
        <name>query</name>
        <description>问题内容。可以使用@文件名引用特定文件，使用@@符号引用函数或类。</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>chat</name>
        <description>进入聊天模式，与AI进行交互对话。支持多轮对话和上下文理解。</description>
        <parameters>
        <parameter>
        <name>query</name>
        <description>聊天内容。支持以下特殊语法：
        - @文件名：引用特定文件
        - @@符号：引用函数或类
        - <img>图片路径</img>：引入图片内容
        </description>
        </parameter>
        <parameter>
        <name>/new</name>
        <description>开启新的聊天会话，清除之前的对话历史。</description>
        </parameter>
        <parameter>
        <name>/no_context</name>
        <description>不使用当前的文件上下文进行对话。</description>
        </parameter>
        <parameter>
        <name>/review</name>
        <description>请求代码审查，会对指定代码进行全面检查。</description>
        </parameter>
        <parameter>
        <name>/mcp</name>
        <description>使用模型控制面板功能。</description>
        </parameter>
        <parameter>
        <name>/rag</name>
        <description>使用检索增强生成功能。</description>
        </parameter>
        <parameter>
        <name>/copy</name>
        <description>复制生成的内容。</description>
        </parameter>
        <parameter>
        <name>/save</name>
        <description>保存对话内容。</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>coding</name>
        <description>代码生成命令，用于生成、修改和重构代码。</description>
        <parameters>
        <parameter>
        <name>query</name>
        <description>代码生成需求描述。支持：
        - @文件名：引用特定文件
        - @@符号：引用函数或类
        - <img>图片路径</img>：引入图片内容
        </description>
        </parameter>
        <parameter>
        <name>/apply</name>
        <description>应用上次生成的代码，并保留相关上下文。</description>
        </parameter>
        <parameter>
        <name>/next</name>
        <description>预测下一步任务，系统会分析当前状态并建议后续开发步骤。</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>design</name>
        <description>设计相关命令，用于生成各类设计资源。</description>
        <parameters>
        <parameter>
        <name>query</name>
        <description>设计需求描述，需要详细说明设计要求。</description>
        </parameter>
        <parameter>
        <name>/svg</name>
        <description>生成SVG格式的矢量图设计。</description>
        </parameter>
        <parameter>
        <name>/sd</name>
        <description>使用Stable Diffusion生成图片设计。</description>
        </parameter>
        <parameter>
        <name>/logo</name>
        <description>生成Logo设计，支持多种风格。</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>summon</name>
        <description>调用AI工具，执行特定任务。会考虑当前会话中的文件作为上下文。</description>
        <parameters>
        <parameter>
        <name>query</name>
        <description>工具调用需求描述，需要明确指出要使用的工具和具体任务。</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>lib</name>
        <description>库管理命令，用于管理项目依赖和文档。</description>
        <parameters>
        <parameter>
        <name>/add <库名></name>
        <description>添加新库到项目。会自动获取相关文档。</description>
        </parameter>
        <parameter>
        <name>/remove <库名></name>
        <description>从项目中移除指定库及其文档。</description>
        </parameter>
        <parameter>
        <name>/list</name>
        <description>列出项目中所有已添加的库。</description>
        </parameter>
        <parameter>
        <name>/set-proxy <代理地址></name>
        <description>设置库文档下载的代理地址。</description>
        </parameter>
        <parameter>
        <name>/refresh</name>
        <description>刷新库文档，获取最新版本。</description>
        </parameter>
        <parameter>
        <name>/get <包名></name>
        <description>获取指定包的详细文档信息。</description>
        </parameter>
        </parameters>
        </command>

        <command>
        <name>mcp</name>
        <description>模型控制面板命令，用于管理和控制AI模型。</description>
        <parameters>
        <parameter>
        <name>/add <模型配置></name>
        <description>添加新的AI模型。配置格式：name=模型名 base_url=地址 api_key=密钥</description>
        </parameter>
        <parameter>
        <name>/remove <模型名></name>
        <description>移除指定的AI模型。</description>
        </parameter>
        <parameter>
        <name>/list</name>
        <description>列出所有可用的AI模型。</description>
        </parameter>
        <parameter>
        <name>/list_running</name>
        <description>列出当前正在运行的AI模型。</description>
        </parameter>
        <parameter>
        <name>/refresh <模型名></name>
        <description>刷新指定模型的状态和配置。</description>
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
