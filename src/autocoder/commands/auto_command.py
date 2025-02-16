import json
import os
import time
from pydantic import BaseModel, Field
import byzerllm
from typing import List, Dict, Any, Union, Callable
from autocoder.common.printer import Printer
from pydantic import SkipValidation

from autocoder.common.result_manager import ResultManager
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from byzerllm.utils.str2model import to_model
from autocoder.common import git_utils


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
    reasoning: str

class AutoCommandResponse(BaseModel):
    suggestions: List[CommandSuggestion]
    reasoning: str


class AutoCommandRequest(BaseModel):
    user_input: str     


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
    def _analyze(self, request: AutoCommandRequest) -> str:
        """
        根据用户输入和当前上下文，分析并推荐最合适的函数。

        用户输入: {{ user_input }}

        {% if current_files %}
        当前文件列表: 
        {% for file in current_files %}
        - {{ file }}
        {% endfor %}
        {% endif %}

        
        可用命令列表:
        {{ available_commands }}

        {% if conversation_history %}
        历史对话:
        {% for conv in conversation_history %}
        {{ conv.role }}: {{ conv.content }}
        {% endfor %}
        {% endif %}

        请分析用户意图，返回一个命令并给出推荐理由。
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

        注意，只能返回一个命令。我后续会把每个命令的执行结果告诉你。你继续确定下一步该执行什么命令，直到
        满足需求。
        """
        return {
            "user_input": request.user_input,
            "current_files": self.memory_config.memory["current_files"]["files"],            
            "conversation_history": [],
            "available_commands": self._command_readme.prompt(),
            "current_conf": json.dumps(self.memory_config.memory["conf"], indent=2),        
        }
    
    @byzerllm.prompt()
    def _execute_command_result(self, result:str) -> str:
        '''
        根据函数执行结果，返回下一个函数。

        下面是我们上一个函数执行结果: 
        
        <function_result>
        {{ result }}
        </function_result>

        请分析命令执行结果，返回下一个函数。如果已经满足要求，则不要返回任何函数,确保 suggestions 为空。
        注意，你最多尝试10次，如果10次都没有满足要求，则不要返回任何函数，确保 suggestions 为空。
        '''
    
    def analyze(self, request: AutoCommandRequest) -> AutoCommandResponse:
        # 获取 prompt 内容
        prompt = self._analyze.prompt(request)
        
        # 构造对话上下文
        conversations = [{"role": "user", "content": prompt}]
        
        # 使用 stream_out 进行输出
        printer = Printer()
        title = printer.get_message_from_key("auto_command_analyzing")
        result, _ = stream_out(
            self.llm.stream_chat_oai(conversations=conversations, delta_mode=True),
            model_name=self.llm.default_model_name,
            title=title        
        )
        conversations.append({"role": "assistant", "content": result})    
        # 提取 JSON 并转换为 AutoCommandResponse            
        response = to_model(result, AutoCommandResponse)         
        
        # 保存对话记录
        save_to_memory_file(
            query=request.user_input,
            response=response.model_dump_json(indent=2)
        )
        result_manager = ResultManager()
        
        while True:
            # 执行命令
            command = response.suggestions[0].command
            parameters = response.suggestions[0].parameters
            self.execute_auto_command(command, parameters)            
            content = ""
            last_result = result_manager.get_last()
            if last_result:
                if last_result.meta["action"] == "coding":                    
                    # 如果上一步是 coding，则需要把上一步的更改前和更改后的内容作为上下文
                    changes = git_utils.get_changes_by_commit_message("", last_result.meta["commit_message"])
                    if changes.success:
                        for file_path, change in changes.changes.items():
                            if change.before:
                                content += f"## File:\n {file_path}[更改前]\n{change.before}\n\nFile:\n {file_path}\n\n[更改后]\n{change.after}\n\n"
                else:
                    content = last_result.content

                conversations.append({"role": "user", "content": content})
                title = printer.get_message_from_key("auto_command_analyzing")
                print(conversations)
                result, _ = stream_out(
                    self.llm.stream_chat_oai(conversations=conversations, delta_mode=True),
                    model_name=self.llm.default_model_name,
                    title=title        
                )
                conversations.append({"role": "assistant", "content": result})    
                # 提取 JSON 并转换为 AutoCommandResponse            
                response = to_model(result, AutoCommandResponse)  
                if not response or  not response.suggestions:
                    break                
                # 保存对话记录
                save_to_memory_file(
                    query=request.user_input,
                    response=response.model_dump_json(indent=2)
                )

            else:
                self.printer.print_in_terminal("auto_command_break", style="yellow", command=command)
                break            
        
        return response        
    
    @byzerllm.prompt()
    def _command_readme(self) -> str:
        '''
        你有如下函数可供使用：
        
        <commands>
        
        <command>
        <name>add_files</name>
        <description>
          添加文件到一个活跃区，活跃区当你使用 chat,coding 函数时，活跃区的文件会被他们使用。
          支持通过模式匹配添加文件，支持 glob 语法，例如 *.py。可以使用相对路径或绝对路径。
        </description>
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
        <description>从活跃区移除文件。可以指定多个文件，支持文件名或完整路径。</description>
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
        <description>通过add_files 添加的文件</description>
        <usage>
         该命令不需要任何参数，直接使用即可。
         使用例子：

         /list_files

        </usage>
        </command>        

        <command>
        <name>revert</name>
        <description>
        撤销最后一次代码修改，恢复到修改前的状态。同时会删除对应的操作记录文件，
        如果很明显你对上一次coding执行后的效果觉得不满意，可以使用该函数来撤销上一次的代码修改。
        </description>
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
        <name>help</name>
        <description>
         显示帮助信息,也可以执行一些配置需求。
        </description>
        <usage>
        该命令只有一个参数 query，query 为字符串，表示要执行的配置需求。

        如果query 为空，则显示一个通用帮助信息。

         ## 显示通用帮助
         不带参数显示所有可用命令的概览
         使用例子：

         /help

         ## 帮助用户执行特定的配置
         
         /help 关闭索引

         这条命令会触发:

         /conf skip_build_index:true

         的执行。

        常见的一些配置选项示例：

        # 配置项说明
        ## auto_merge: 代码合并方式，可选值为editblock、diff、wholefile.
        - editblock: 生成 SEARCH/REPLACE 块，然后根据 SEARCH块到对应的源码查找，如果相似度阈值大于 editblock_similarity， 那么则将
        找到的代码块替换为 REPLACE 块。大部分情况都推荐使用 editblock。        
        - wholefile: 重新生成整个文件，然后替换原来的文件。对于重构场景，推荐使用 wholefile。
        - diff: 生成标准 git diff 格式，适用于简单的代码修改。        

        ## editblock_similarity: editblock相似度阈值
        - editblock相似度阈值，取值范围为0-1，默认值为0.9。如果设置的太低，虽然能合并进去，但是会引入错误。推荐不要修改该值。

        ## generate_times_same_model: 相同模型生成次数
        当进行生成代码时，大模型会对同一个需求生成多份代码，然后会使用 generate_rerank_model 模型对多份代码进行重排序，
        然后选择得分最高的代码。一般次数越多，最终得到正确的代码概率越高。默认值为1，推荐设置为3。但是设置值越多，可能速度就越慢，消耗的token也越多。

        ## skip_filter_index: 是否跳过索引过滤
        是否跳过根据用户的query 自动查找上下文。推荐设置为 false
        
        ## skip_build_index: 是否跳过索引构建
        是否自动构建索引。推荐设置为 false。注意，如果该值设置为 true, 那么 skip_filter_index 设置不会生效。
        
        比如你想开启索引，则可以执行：

        /help 开启索引

        其中 query 参数为 "开启索引"                                                                              
                                        
        </usage>
        </command>

        <command>
        <name>exclude_dirs</name>
        <description>设置要排除的目录，这些目录下的文件被 @ 或者 @@ 不会触发对这些目录的提示。</description>
        <usage>
         该命令接受一个或多个目录名，多个目录用逗号分隔。

         ## 添加排除目录
         使用例子：

         /exclude_dirs node_modules,dist,build
         /exclude_dirs .git
         
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
         - /mcp：获取 MCP 服务内容
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
        <description>代码生成函数，用于生成、修改和重构代码。</description>
        <usage>
         该函数支持多种代码生成和修改场景。

         该函数支持一个参数 query，query 为字符串，表示要生成的代码需求。

         ## 基础代码生成
         直接描述需求
         使用例子：

         /coding 创建一个处理用户登录的函数
         
         此处的 query 参数为 "创建一个处理用户登录的函数".

         ## 和/chat 搭配使用
         当你用过 /chat 之后，继续使用 /coding 时，可以添加 /apply 来带上 /chat 的对话内容。         
         使用例子：

         /coding /apply 根据我们的历史对话实现代码,请不要遗漏任何细节。

         此处 query 参数为 "/apply 根据我们的历史对话实现代码,请不要遗漏任何细节。"

         ## 预测下一步
         使用 /next 分析并建议后续步骤
         使用例子：

         /coding /next

         此处 query 参数为 "/next"

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
        <name>lib</name>
        <description>库管理命令，用于管理项目依赖和文档。</description>
        <usage>
         该命令用于管理项目的依赖库和相关文档。

         ## 添加库
         使用 /add 添加新库
         使用例子：

         /lib /add byzer-llm
        

         ## 移除库
         使用 /remove 移除库
         使用例子：

         /lib /remove byzer-llm

         ## 查看库列表
         使用 /list 查看已添加的库
         使用例子：

         /lib /list

         ## 设置代理
         使用 /set-proxy 设置下载代理
         使用例子：

         /lib /set-proxy https://gitee.com/allwefantasy/llm_friendly_packages

         ## 刷新文档
         使用 /refresh 更新文档
         使用例子：

         /lib /refresh

         ## 获取文档
         使用 /get 获取特定包的文档
         使用例子：

         /lib /get byzer-llm

        目前仅支持用于大模型的 byzer-llm 包，用于数据分析的 byzer-sql 包。

        </usage>
        </command>

        <command>
        <name>models</name>
        <description>模型控制面板命令，用于管理和控制AI模型。</description>
        <usage>
        该命令用于管理和控制AI模型的配置和运行。 包含两个参数：
        1. params
        2. query
         
        罗列模型模板

        /models /list


        其中展示的结果中标注 * 好的模型表示目前已经激活（配置过api key)的。

        添加模型模板

        比如我想添加 open router 或者硅基流动的模型，则可以通过如下方式：
        
        /models /add_model name=openrouter-sonnet-3.5 base_url=https://openrouter.ai/api/v1
        
        这样就能添加自定义模型: openrouter-sonnet-3.5
        

        如果你想添加添加硅基流动deepseek 模型的方式为：

        /models /add_model name=siliconflow_ds_2.5  base_url=https://api.siliconflow.cn/v1 model_name=deepseek-ai/DeepSeek-V2.5

        name 为你取的一个名字，这意味着同一个模型，你可以添加多个，只要保证 name 不一样即可。
        base_url 是 硅基流动的 API 地址
        model_name 则为你在硅基流动选择的模型名

        添加完模型后，你还需要能够激活模型:

        /models /activate openrouter-sonnet-3.5 <YOUR_API_KEY>

        之后你就可以这样配置来使用激活的模型：

        /conf model:openrouter-sonnet-3.5 

        删除模型

        /models /remove openrouter-sonnet-3.5
        
        </usage>
        </command>

        <command>
        <name>tools</name>
        <description>提供各种实用工具函数，用于辅助开发和调试。</description>
        <usage>
        该命令提供以下工具函数：

        1. run_python_code: 运行Python代码
        使用示例：
        /tools run_python_code code="print('Hello World')"

        2. run_shell_code: 运行Shell脚本
        使用示例：
        /tools run_shell_code script="ls -l"

        3. auto_run_job: 自动拆解并执行任务
        使用示例：
        /tools auto_run_job job="编译项目"

        4. get_related_files_by_symbols: 根据符号获取相关文件
        使用示例：
        /tools get_related_files_by_symbols query="UserService类"

        5. get_project_related_files: 根据查询获取项目相关文件
        使用示例：
        /tools get_project_related_files query="用户认证模块"

        6. get_project_map: 获取项目结构映射
        使用示例：
        /tools get_project_map

        7. read_files: 读取指定文件内容
        使用示例：
        /tools read_files paths="src/main.py,src/utils.py"

        8. find_files_by_name: 根据文件名搜索文件
        使用示例：
        /tools find_files_by_name keyword="service"

        9. find_files_by_content: 根据文件内容搜索文件
        使用示例：
        /tools find_files_by_content keyword="UserService"
        </usage>
        </command>
        </commands>        
        '''

    def execute_auto_command(self, command: str, parameters: Dict[str, Any]) -> None:
        """
        执行自动生成的命令
        """
        command_map = {
            "add_files": self.command_config.add_files,
            "remove_files": self.command_config.remove_files,
            "list_files": self.command_config.list_files,            
            "revert": self.command_config.revert,
            "commit": self.command_config.commit,
            "help": self.command_config.help,
            "exclude_dirs": self.command_config.exclude_dirs,
            "ask": self.command_config.ask,
            "chat": self.command_config.chat,
            "coding": self.command_config.coding,
            "design": self.command_config.design,
            "summon": self.command_config.summon,
            "lib": self.command_config.lib,
            "models": self.command_config.models
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
