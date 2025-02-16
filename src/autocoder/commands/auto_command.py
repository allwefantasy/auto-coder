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
        <usage>
         该方法接受一个参数 file_names，是一个列表，列表的元素是字符串。下面是常见的子指令：

         ## /all 移除所有文件
         移除所有当前会话中的文件，同时清空活跃组列表。
         使用例子：

         /remove_files /all

         ## 移除指定文件
         可以指定一个或多个文件，文件名之间用逗号分隔。
         使用例子：

         /remove_files file1.py,file2.py
         /remove_files /path/to/file1.py,file2.py

        </usage>
        </command>

        <command>
        <name>list_files</name>
        <description>列出当前会话中的所有文件，显示相对于项目根目录的路径。</description>
        <usage>
         该命令不需要任何参数，直接使用即可。
         使用例子：

         /list_files

         输出示例：
         Current Files
         ├── src/main.py
         ├── tests/test_main.py
         └── README.md
        </usage>
        </command>

        <command>
        <name>conf</name>
        <description>配置管理命令，用于设置和管理系统配置项。</description>
        <usage>
         该命令支持两种操作模式：设置配置和删除配置。

         ## 设置配置
         使用 key:value 格式设置配置项
         使用例子：

         /conf model:v3_chat
         /conf auto_merge:editblock
         /conf skip_build_index:true

         支持的主要配置项：
         - model: 设置默认使用的模型
         - chat_model: 设置聊天使用的模型
         - code_model: 设置代码生成使用的模型
         - auto_merge: 代码合并方式(editblock/diff/wholefile)
         - editblock_similarity: 编辑块相似度阈值(0-1)
         - skip_build_index: 是否跳过索引构建(true/false)
         - skip_filter_index: 是否跳过索引过滤(true/false)
         - human_as_model: 是否将人类作为模型(true/false)

         ## 删除配置
         使用 /drop 删除指定配置项
         使用例子：

         /conf /drop model
         /conf /drop auto_merge

         ## 查看当前配置
         直接使用 /conf 命令不带参数
         使用例子：

         /conf
        </usage>
        </command>

        <command>
        <name>revert</name>
        <description>撤销最后一次代码修改，恢复到修改前的状态。同时会删除对应的操作记录文件。</description>
        <usage>
         该命令不需要任何参数，直接使用即可。会撤销最近一次的代码修改操作。
         使用例子：

         /revert

         注意：
         - 只能撤销最后一次的修改
         - 撤销后会同时删除对应的操作记录文件
         - 如果没有可撤销的操作会提示错误
        </usage>
        </command>

        <command>
        <name>commit</name>
        <description>提交代码更改到版本控制系统。系统会自动生成合适的提交信息，并创建提交记录。</description>
        <usage>
         该命令支持直接使用或带参数使用。

         ## 直接提交
         系统会自动分析变更并生成提交信息
         使用例子：

         /commit

         ## 带说明提交
         可以提供额外的说明信息
         使用例子：

         /commit 优化了性能并修复了内存泄漏问题

         注意：
         - 需要项目已经初始化了Git仓库
         - 会自动检测未提交的变更
         - 使用AI生成规范的提交信息
        </usage>
        </command>

        <command>
        <name>help</name>
        <description>显示帮助信息。可以加上具体的查询内容获取特定帮助，例如：/help auto_merge</description>
        <usage>
         该命令支持两种使用方式：

         ## 显示通用帮助
         不带参数显示所有可用命令的概览
         使用例子：

         /help

         ## 显示特定功能帮助
         指定具体的功能或配置项获取详细说明
         使用例子：

         /help auto_merge
         /help editblock_similarity
         /help coding
        </usage>
        </command>

        <command>
        <name>exclude_dirs</name>
        <description>设置要排除的目录，这些目录下的文件将不会被索引和处理。</description>
        <usage>
         该命令接受一个或多个目录名，多个目录用逗号分隔。

         ## 添加排除目录
         使用例子：

         /exclude_dirs node_modules,dist,build
         /exclude_dirs .git

         注意：
         - 默认已排除：.git, node_modules, dist, build, __pycache__
         - 排除的目录不会被索引和处理
         - 支持相对路径和绝对路径
         - 更改后需要重新构建索引才能生效
        </usage>
        </command>

        <command>
        <name>ask</name>
        <description>向AI提问，获取关于代码或项目的解答。会考虑当前会话中的文件作为上下文。</description>
        <usage>
         该命令需要提供问题内容，支持多种引用方式。

         ## 基础提问
         直接提出问题
         使用例子：

         /ask 这个项目的主要功能是什么？

         ## 引用特定文件
         使用@语法引用文件
         使用例子：

         /ask @main.py 中的 process_data 函数是做什么的？

         ## 引用特定符号
         使用@@语法引用函数或类
         使用例子：

         /ask @@process_data 这个函数的参数类型是什么？

         注意：
         - 会自动分析当前会话中的文件作为上下文
         - 支持多轮对话，保持上下文连贯
         - 可以同时引用多个文件或符号
        </usage>
        </command>

        <command>
        <name>chat</name>
        <description>进入聊天模式，与AI进行交互对话。支持多轮对话和上下文理解。</description>
        <usage>
         该命令支持多种交互方式和特殊功能。

         ## 基础对话
         直接输入对话内容
         使用例子：

         /chat 这个项目使用了什么技术栈？

         ## 新会话
         使用 /new 开启新对话
         使用例子：

         /chat /new 让我们讨论新的话题

         ## 代码审查
         使用 /review 请求代码审查
         使用例子：

         /chat /review @main.py

         ## 特殊功能
         - /no_context：不使用当前文件上下文
         - /mcp：使用模型控制面板
         - /rag：使用检索增强生成
         - /copy：复制生成内容
         - /save：保存对话内容

         ## 引用语法
         - @文件名：引用特定文件
         - @@符号：引用函数或类
         - <img>图片路径</img>：引入图片

         使用例子：

         /chat @utils.py 这个文件的主要功能是什么？
         /chat @@process_data 这个函数的实现有什么问题？
         /chat <img>screenshots/error.png</img> 这个错误如何解决？
        </usage>
        </command>

        <command>
        <name>coding</name>
        <description>代码生成命令，用于生成、修改和重构代码。</description>
        <usage>
         该命令支持多种代码生成和修改场景。

         ## 基础代码生成
         直接描述需求
         使用例子：

         /coding 创建一个处理用户登录的函数

         ## 应用上次生成
         使用 /apply 应用上次生成的代码
         使用例子：

         /coding /apply 在上次的基础上添加密码加密

         ## 预测下一步
         使用 /next 分析并建议后续步骤
         使用例子：

         /coding /next

         ## 引用语法
         - @文件名：引用特定文件
         - @@符号：引用函数或类
         - <img>图片路径</img>：引入图片

         使用例子：

         /coding @auth.py 添加JWT认证
         /coding @@login 优化错误处理
         /coding <img>design/flow.png</img> 实现这个流程图的功能

         注意：
         - 支持多文件联动修改
         - 自动处理代码依赖关系
         - 保持代码风格一致性
         - 生成代码会进行自动测试
        </usage>
        </command>

        <command>
        <name>design</name>
        <description>设计相关命令，用于生成各类设计资源。</description>
        <usage>
         该命令支持多种设计资源的生成。

         ## SVG设计
         使用 /svg 生成矢量图
         使用例子：

         /design /svg 创建一个简洁的登录图标

         ## 图片设计
         使用 /sd 生成图片
         使用例子：

         /design /sd 生成一张科技风格的背景图

         ## Logo设计
         使用 /logo 生成标志
         使用例子：

         /design /logo 设计一个代表AI编程的logo

         注意：
         - 需要详细描述设计需求
         - 可以指定具体的风格和要求
         - 支持多种输出格式
         - 可以进行反复调整
        </usage>
        </command>

        <command>
        <name>summon</name>
        <description>调用AI工具，执行特定任务。会考虑当前会话中的文件作为上下文。</description>
        <usage>
         该命令用于调用特定的AI工具完成任务。

         ## 基础调用
         描述需要完成的任务
         使用例子：

         /summon 分析当前代码的性能瓶颈
         /summon 生成项目的类图
         /summon 检查代码中的安全漏洞

         注意：
         - 会自动选择最适合的AI工具
         - 考虑当前会话文件作为上下文
         - 可以组合多个工具协同工作
         - 支持自定义工具链
        </usage>
        </command>

        <command>
        <name>lib</name>
        <description>库管理命令，用于管理项目依赖和文档。</description>
        <usage>
         该命令用于管理项目的依赖库和相关文档。

         ## 添加库
         使用 /add 添加新库
         使用例子：

         /lib /add requests
         /lib /add numpy,pandas

         ## 移除库
         使用 /remove 移除库
         使用例子：

         /lib /remove requests

         ## 查看库列表
         使用 /list 查看已添加的库
         使用例子：

         /lib /list

         ## 设置代理
         使用 /set-proxy 设置下载代理
         使用例子：

         /lib /set-proxy http://proxy.example.com:8080

         ## 刷新文档
         使用 /refresh 更新文档
         使用例子：

         /lib /refresh

         ## 获取文档
         使用 /get 获取特定包的文档
         使用例子：

         /lib /get requests

         注意：
         - 自动处理依赖关系
         - 自动下载相关文档
         - 支持版本管理
         - 可以设置代理加速下载
        </usage>
        </command>

        <command>
        <name>mcp</name>
        <description>模型控制面板命令，用于管理和控制AI模型。</description>
        <usage>
         该命令用于管理和控制AI模型的配置和运行。

         ## 添加模型
         使用 /add 添加新模型
         使用例子：

         /mcp /add name=gpt4 base_url=https://api.example.com api_key=xxx

         ## 移除模型
         使用 /remove 移除模型
         使用例子：

         /mcp /remove gpt4

         ## 查看模型列表
         使用 /list 查看所有可用模型
         使用例子：

         /mcp /list

         ## 查看运行中的模型
         使用 /list_running 查看正在运行的模型
         使用例子：

         /mcp /list_running

         ## 刷新模型状态
         使用 /refresh 刷新指定模型
         使用例子：

         /mcp /refresh gpt4

         注意：
         - 支持多种模型类型
         - 自动管理模型生命周期
         - 支持模型热切换
         - 提供性能监控
        </usage>
        </command>

        </commands>
        '''
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
