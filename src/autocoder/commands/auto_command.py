import json
import os
import time
from pydantic import BaseModel, Field
import byzerllm
from typing import List, Dict, Any, Union, Callable, Optional
from autocoder.common.printer import Printer
from rich.console import Console
from rich.panel import Panel
from pydantic import SkipValidation

from autocoder.common.result_manager import ResultManager
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from byzerllm.utils.str2model import to_model
from autocoder.common import git_utils
from autocoder.commands.tools import AutoCommandTools
from autocoder.auto_coder import AutoCoderArgs
from autocoder.common import detect_env
from autocoder.common import shells
from loguru import logger
from autocoder.utils import llms as llms_utils
from autocoder.rag.token_counter import count_tokens
from autocoder.common.global_cancel import global_cancel
from autocoder.common.auto_configure import config_readme
from autocoder.utils.auto_project_type import ProjectTypeAnalyzer
from rich.text import Text

class CommandMessage(BaseModel):
    role: str
    content: str


class ExtendedCommandMessage(BaseModel):
    message: CommandMessage
    timestamp: str


class CommandConversation(BaseModel):
    history: Dict[str, ExtendedCommandMessage]
    current_conversation: List[CommandMessage]


def load_memory_file() -> CommandConversation:
    """Load command conversations from memory file"""
    memory_dir = os.path.join(".auto-coder", "memory")
    file_path = os.path.join(memory_dir, "command_chat_history.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            try:
                return CommandConversation.model_validate_json(f.read())
            except Exception:
                return CommandConversation(history={}, current_conversation=[])
    return CommandConversation(history={}, current_conversation=[])


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
    reasoning: Optional[str] = None


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
    execute_shell_command: SkipValidation[Callable]
    generate_shell_command: SkipValidation[Callable]
    conf_export: SkipValidation[Callable]
    conf_import: SkipValidation[Callable]
    index_export: SkipValidation[Callable]
    index_import: SkipValidation[Callable]
    exclude_files: SkipValidation[Callable]

    

class CommandAutoTuner:
    def __init__(self, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM],
                 args: AutoCoderArgs,
                 memory_config: MemoryConfig, command_config: CommandConfig):
        self.llm = llm
        self.args = args
        self.printer = Printer()
        self.memory_config = memory_config
        self.command_config = command_config
        self.tools = AutoCommandTools(args=args, llm=self.llm)
        self.project_type_analyzer = ProjectTypeAnalyzer(args=args, llm=self.llm)        
    
    def get_conversations(self) -> List[CommandMessage]:
        """Get conversation history from memory file"""
        conversation = load_memory_file()
        return [extended_msg for extended_msg in conversation.current_conversation]

    @byzerllm.prompt()
    def _analyze(self, request: AutoCommandRequest) -> str:
        """
        当前用户环境信息如下:
        <os_info>
        操作系统: {{ env_info.os_name }} {{ env_info.os_version }}
        操作系统发行版: {{ os_distribution }}
        Python版本: {{ env_info.python_version }}
        终端类型: {{ env_info.shell_type }}
        终端编码: {{ env_info.shell_encoding }}
        当前用户: {{ current_user }}
        
        {%- if shell_type %}
        脚本类型：{{ shell_type }}
        {%- endif %}

        {%- if env_info.conda_env %}
        Conda环境: {{ env_info.conda_env }}
        {%- endif %}
        {%- if env_info.virtualenv %}
        虚拟环境: {{ env_info.virtualenv }}
        {%- endif %}   
        </os_info>
        
        我们的目标是根据用户输入和当前上下文，组合多个函数来完成用户的需求。
        
        {% if current_files %}
        当前活跃区文件列表：
        <current_files>
        {% for file in current_files %}
        - {{ file }}
        {% endfor %}
        </current_files>
        {% endif %}


        当前用户的配置选项如下:
        <current_conf>
        {{ current_conf }}
        </current_conf>
        
        可用函数列表:
        {{ available_commands }}

        函数组合说明：        
        <function_combination_readme>
        如果用户是一个编码需求，你可以先简单观察当前活跃区文件列表：
        0. 关注下当前软件的配置，诸如索引开启关闭。如果有觉得不合理的可以通过 help 函数来修改。
        1. 如果你觉得这些文件不够满足用户的需求，而当前的索引配置关闭的，那么你可以通过help("将skip_filter_index 和 skip_build_index 设置为 false") 让
        chat,coding 函数来获取更多文件，或者你也可以自己通过调用 get_project_structure 函数来获取项目结构，然后通过 get_project_map 函数来获取某个文件的用途，符号列表，以及
        文件大小（tokens数）,最后再通过 read_files/read_file_with_keyword_ranges 函数来读取文件内容, 最后通过 add_files 函数来添加文件到活跃区。
        确保 chat,coding 函数能够正常使用。
        2. 对于一个比较复杂的代码需求，你可以先通过 chat 函数来获得一些设计，根据chat返回的结果，你可以选择多次调用chat调整最后的设计。最后，当你满意后，可以通过 coding("/apply 根据历史对话实现代码，请不要有遗漏") 来完成最后的编码。
        3. 注意，为了防止对话过长，你可以使用 chat("/new") 来创新新的会话。然后接着正常再次调用 chat 函数。 即可
        4. 当用户询问项目，比如询问什么什么功能在哪里的时候，或者哪个文件实现了什么功能，推荐的工具组合是 get_project_map 和 get_project_structure。可以直通过 get_project_map 查看整个项目文件的索引（该索引包含了文件列表，每个文件的用途和符号列表），也可以
        通过 get_project_structure 来获取项目结构，然后通过 get_project_map 来获取你想看的某个文件的用途，符号列表，最后再通过 read_files/read_file_with_keyword_ranges 函数来读取文件内容,确认对应的功能是否在相关的文件里。
        5. 调用 coding 函数的时候，尽可能多的 @文件和@@符号，让需求更加清晰明了，建议多描述具体怎么完成对应的需求。
        6. 对于代码需求设计，尽可能使用 chat 函数。
        7. 如果成功执行了 coding 函数，最好再调用一次 chat("/review /commit")    
        8. 我们所有的对话不能超过 {{ conversation_safe_zone_tokens }} 个tokens,当你读取索引文件 (get_project_map) 的时候，你可以看到
        每个文件的tokens数，你可以根据这个信息来决定如何读取这个文件。比如对于很小的文件，那么可以直接全部读取，
        而对于分析一个超大文件推荐组合 read_files 带上 line_ranges 参数来读取，或者组合 read_file_withread_file_with_keyword_ranges 等来读取，
        每个函数你还可以使用多次来获取更多信息。
        9. 根据操作系统，终端类型，脚本类型等各种信息，在涉及到路径或者脚本的时候，需要考虑平台差异性。
        </function_combination_readme>



        {% if conversation_history %}
        历史对话:
        <conversation_history>
        {% for conv in conversation_history %}
        ({{ conv.role }}): {{ conv.content }}
        {% endfor %}
        </conversation_history>
        {% endif %}

        用户需求: 
        <user_input>
        {{ user_input }}
        </user_input>

        请分析用户意图，组合一个或者多个函数，帮助用户完成需求。
        返回格式必须是严格的JSON格式：
        
        ```json
        {
            "suggestions": [
                {
                    "command": "函数名称",
                    "parameters": {},
                    "confidence": 0.9,
                    "reasoning": "推荐理由"
                }
            ],
            "reasoning": "整体推理说明"
        }
        ```   

        注意，现在，请返回第一个函数。我后续会把每个函数的执行结果告诉你。你根据执行结果继续确定下一步该执行什新的函数，直到
        满足需求。
        """

        env_info = detect_env() 
        shell_type = "bash"
        if shells.is_running_in_cmd():
            shell_type = "cmd"
        elif shells.is_running_in_powershell():
            shell_type = "powershell"

        return {
            "user_input": request.user_input,
            "current_files": self.memory_config.memory["current_files"]["files"],            
            "conversation_history": self.get_conversations(),
            "available_commands": self._command_readme.prompt(),
            "current_conf": json.dumps(self.memory_config.memory["conf"], indent=2),        
            "env_info": env_info,
            "shell_type": shell_type,
            "shell_encoding": shells.get_terminal_encoding(),
            "conversation_safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens,
            "os_distribution": shells.get_os_distribution(),
            "current_user": shells.get_current_username()
        }
    
    @byzerllm.prompt()
    def _execute_command_result(self, result:str) -> str:
        '''
        根据函数执行结果，返回下一个函数。

        下面是我们上一个函数执行结果: 
        
        <function_result>
        {{ result }}
        </function_result>                

        请根据命令执行结果以及前面的对话，返回下一个函数。
        
        *** 非常非常重要的提示 ***
        1. 如果已经满足要求，则不要返回任何函数,确保 suggestions 为空。
        2. 你最多尝试 {{ auto_command_max_iterations }} 次，如果 {{ auto_command_max_iterations }} 次都没有满足要求，则不要返回任何函数，确保 suggestions 为空。
        '''   
        return {
            "auto_command_max_iterations": self.args.auto_command_max_iterations,
            "conversation_safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens
        } 
    
    def analyze(self, request: AutoCommandRequest) -> AutoCommandResponse:
        # 获取 prompt 内容
        prompt = self._analyze.prompt(request)
        
        # 构造对话上下文
        conversations = [{"role": "user", "content": prompt}]
        
        # 使用 stream_out 进行输出
        printer = Printer()
        title = printer.get_message_from_key("auto_command_analyzing")
        final_title = printer.get_message_from_key("auto_command_analyzed")

        def extract_command_response(content: str) -> str:
            # 提取 JSON 并转换为 AutoCommandResponse
            try:
                response = to_model(content, AutoCommandResponse)  
                if response.suggestions:                    
                    command = response.suggestions[0].command
                    parameters = response.suggestions[0].parameters                    
                    if parameters:
                        params_str = ", ".join([f"{k}={v}" for k, v in parameters.items()])
                    else:
                        params_str = ""                    
                    return f"{command}({params_str})"
                else:
                    return printer.get_message_from_key("satisfied_prompt")                    
            except Exception as e:                
                logger.error(f"Error extracting command response: {str(e)}")
                return content
            
        model_name = ",".join(llms_utils.get_llm_names(self.llm))
        start_time = time.monotonic()
        result, last_meta = stream_out(
            self.llm.stream_chat_oai(conversations=conversations, delta_mode=True),
            model_name=model_name,
            title=title,
            final_title=final_title,
            display_func= extract_command_response
        )
                
        if last_meta:
            elapsed_time = time.monotonic() - start_time            
            speed = last_meta.generated_tokens_count / elapsed_time
            
            # Get model info for pricing
            from autocoder.utils import llms as llm_utils
            model_info = llm_utils.get_model_info(model_name, self.args.product_mode) or {}
            input_price = model_info.get("input_price", 0.0) if model_info else 0.0
            output_price = model_info.get("output_price", 0.0) if model_info else 0.0
            
            # Calculate costs
            input_cost = (last_meta.input_tokens_count * input_price) / 1000000  # Convert to millions
            output_cost = (last_meta.generated_tokens_count * output_price) / 1000000  # Convert to millions
            
            printer.print_in_terminal("stream_out_stats", 
                                model_name=",".join(llms_utils.get_llm_names(self.llm)),
                                elapsed_time=elapsed_time,
                                first_token_time=last_meta.first_token_time,
                                input_tokens=last_meta.input_tokens_count,
                                output_tokens=last_meta.generated_tokens_count,
                                input_cost=round(input_cost, 4),
                                output_cost=round(output_cost, 4),
                                speed=round(speed, 2))

        ## 这里打印

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
            if global_cancel.requested:
                printer = Printer(console)
                printer.print_in_terminal("generation_cancelled")                    
                break
            # 执行命令
            command = response.suggestions[0].command
            parameters = response.suggestions[0].parameters
            
            # 打印正在执行的命令            
            self.printer.print_in_terminal(
                "auto_command_executing", 
                style="blue", 
                command=command
            )
            
            self.execute_auto_command(command, parameters)            
            content = ""
            last_result = result_manager.get_last()
            if last_result:
                action = last_result.meta["action"] 
                if action == "coding":                    
                    # 如果上一步是 coding，则需要把上一步的更改前和更改后的内容作为上下文
                    changes = git_utils.get_changes_by_commit_message("", last_result.meta["commit_message"])
                    if changes.success:
                        for file_path, change in changes.changes.items():
                            if change:
                                content += f"## File: {file_path}[更改前]\n{change.before or 'New File'}\n\nFile: {file_path}\n\n[更改后]\n{change.after or 'Deleted File'}\n\n"
                    else:
                        content = printer.get_message_from_key_with_format("no_changes_made")            
                else:
                    # 其他的直接获取执行结果
                    content = last_result.content

                if action != command:
                    # command 和 action 不一致，则认为命令执行失败，退出
                    printer.print_in_terminal("auto_command_action_break", style="yellow", command=command, action=action)
                    break

                # 打印执行结果
                console = Console()
                # 截取content前后200字符
                truncated_content = content[:200] + "\n...\n" + content[-200:] if len(content) > 400 else content
                title = printer.get_message_from_key_with_format(
                    "command_execution_result", 
                    action=action
                )
                # 转义内容，避免Rich将内容中的[]解释为markup语法                
                text_content = Text(truncated_content)
                console.print(Panel(
                    text_content,
                    title=title,
                    border_style="blue",
                    padding=(1, 2)
                ))
                # 保持原content不变，继续后续处理
                
                # 添加新的对话内容
                new_content = self._execute_command_result.prompt(content)
                conversations.append({"role": "user", "content": new_content})
                
                # 统计 token 数量                
                total_tokens = count_tokens(json.dumps(conversations,ensure_ascii=False))                

                # 如果对话过长，使用默认策略进行修剪
                if total_tokens > self.args.conversation_prune_safe_zone_tokens:
                    self.printer.print_in_terminal(
                        "conversation_pruning_start", 
                        style="yellow",
                        total_tokens=total_tokens,
                        safe_zone=self.args.conversation_prune_safe_zone_tokens
                    )
                    from autocoder.common.conversation_pruner import ConversationPruner
                    pruner = ConversationPruner(self.args, self.llm)
                    conversations = pruner.prune_conversations(conversations)                    

                title = printer.get_message_from_key("auto_command_analyzing")
                model_name = ",".join(llms_utils.get_llm_names(self.llm))
                
                start_time = time.monotonic()
                result, last_meta = stream_out(
                    self.llm.stream_chat_oai(conversations=conversations, delta_mode=True),
                    model_name=model_name,
                    title=title,
                    final_title=final_title,
                    display_func= extract_command_response
                )                
                
                if last_meta:
                    elapsed_time = time.monotonic() - start_time
                    printer = Printer()
                    speed = last_meta.generated_tokens_count / elapsed_time
                    
                    # Get model info for pricing
                    from autocoder.utils import llms as llm_utils
                    model_info = llm_utils.get_model_info(model_name, self.args.product_mode) or {}
                    input_price = model_info.get("input_price", 0.0) if model_info else 0.0
                    output_price = model_info.get("output_price", 0.0) if model_info else 0.0
                    
                    # Calculate costs
                    input_cost = (last_meta.input_tokens_count * input_price) / 1000000  # Convert to millions
                    output_cost = (last_meta.generated_tokens_count * output_price) / 1000000  # Convert to millions
                    
                    printer.print_in_terminal("stream_out_stats", 
                                        model_name=model_name,
                                        elapsed_time=elapsed_time,
                                        first_token_time=last_meta.first_token_time,
                                        input_tokens=last_meta.input_tokens_count,
                                        output_tokens=last_meta.generated_tokens_count,
                                        input_cost=round(input_cost, 4),
                                        output_cost=round(output_cost, 4),
                                        speed=round(speed, 2))
                    
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
          添加文件到一个活跃区，活跃区当你使用 chat,coding 函数时，活跃区的文件一定会被他们使用。
          支持通过模式匹配添加文件，支持 glob 语法，例如 *.py。可以使用相对路径或绝对路径。
          如果你检测到用户的coding执行结果，缺少必要的文件修改，可以尝试使用该函数先添加文件再执行coding。
        </description>
        <usage>
         该方法只有一个参数 args，args 是一个列表，列表的元素是字符串。

         如果没有包含子指令，单纯的添加文件，那么 args 列表的元素是文件路径，注意我们需要使用绝对路径。

         使用例子：

         add_files(args=["/absolute/path/to/file1.py"])

         也支持glob 语法，例如：

         add_files(args=["**/*.py"])

         这样会把项目根目录下的所有.py文件添加到活跃区，尽量确保少的添加文件。

         如果是有子指令，参考下面是常见的子指令说明。

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

         remove_files(file_names=["/all"])

         ## 移除指定文件
         可以指定一个或多个文件，文件名之间用逗号分隔。
         使用例子：

         remove_files(file_names=["file1.py,file2.py"])
         remove_files(file_names=["/path/to/file1.py,file2.py"])

        </usage>
        </command>

        <command>
        <name>list_files</name>
        <description>通过add_files 添加的文件</description>
        <usage>
         该命令不需要任何参数，直接使用即可。
         使用例子：

         list_files()

        </usage>
        </command>        

        <command>
        <name>revert</name>
        <description>
        撤销最后一次代码修改，恢复到修改前的状态。同时会删除对应的操作记录文件，
        如果很明显你对上一次coding函数执行后的效果觉得不满意，可以使用该函数来撤销上一次的代码修改。
        </description>
        <usage>
         该命令不需要任何参数，直接使用即可。会撤销最近一次的代码修改操作。
         使用例子：

         revert()

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

         help(query="")

         ## 帮助用户执行特定的配置
         
         help(query="关闭索引")

         这条命令会触发:

         /conf skip_build_index:true

         的执行。

        常见的一些配置选项示例：

        {{ config_readme }}
                
        比如你想开启索引，则可以执行：

        help(query="开启索引")

        其中 query 参数为 "开启索引" 

        ** 特别注意，这些配置参数会影响 coding,chat 的执行效果或者结果 根据返回调用该函数做合理的配置**

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

         chat(query="这个项目使用了什么技术栈？")

         ## 新会话
         使用 /new 开启新对话
         使用例子：

         chat(query="/new 让我们讨论新的话题")         

         ## 代码审查
         使用 /review 请求代码审查
         使用例子：

         chat(query="/review @main.py")

         ## 特殊功能
         - /no_context：不使用当前文件上下文
         - /mcp：获取 MCP 服务内容
         - /rag：使用检索增强生成。 如果用户配置了 rag_url, 那可以设置query参数类似 `/rag 查询mcp该如何开发`
         - /copy：chat 函数执行后的结果会被复制到黏贴版
         - /save：chat 函数执行后的结果会被保存到全局记忆中，后续会自动加到 coding,chat 的上下文中

         ## 引用语法
         - @文件名：引用特定文件
         - @@符号：引用函数或类
         - <img>图片路径</img>：引入图片         

         使用例子：

         chat(query="@utils.py 这个文件的主要功能是什么？")
         chat(query="@@process_data 这个函数的实现有什么问题？")
         chat(query="<img>screenshots/error.png</img> 这个错误如何解决？")

         ## 对最后一次commit 进行review
         使用例子：
         chat(query="/review /commit")

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

         coding(query="创建一个处理用户登录的函数")
         

         ## 和 chat 搭配使用
         当你用过 chat 之后，继续使用 coding 时，可以添加 /apply 来带上 chat 的对话内容。         
         使用例子：

         coding(query="/apply 根据我们的历史对话实现代码,请不要遗漏任何细节。")

         ## 预测下一步
         使用 /next 分析并建议后续步骤
         使用例子：

         coding(query="/next")

         ## 引用语法
         - @文件名：引用特定文件
         - @@符号：引用函数或类
         - <img>图片路径</img>：引入图片

         使用例子：

         coding(query="@auth.py 添加JWT认证")
         coding(query="@@login 优化错误处理")
         coding(query="<img>design/flow.png</img> 实现这个流程图的功能")

         在使用 coding 函数时，建议通过 ask_user 来确认是否执行 coding 函数，除非用户明确说不要询问，直接执行。
        </usage>
        </command>

        <command>
        <name>lib</name>
        <description>库管理命令，用于管理项目依赖和文档。</description>
        <usage>
         该命令用于管理项目的依赖库和相关文档。
         参数为 args: List[str]

         ## 添加库
         使用 /add 添加新库
         使用例子：

         lib(args=["/add", "byzer-llm"])
        

         ## 移除库
         使用 /remove 移除库
         使用例子：

         lib(args=["/remove", "byzer-llm"])

         ## 查看库列表
         使用 /list 查看已添加的库
         使用例子：

         lib(args=["/list"])

         ## 设置代理
         使用 /set-proxy 设置下载代理
         使用例子：

         lib(args=["/set-proxy", "https://gitee.com/allwefantasy/llm_friendly_packages"])

         ## 刷新文档
         使用 /refresh 更新文档
         使用例子：

         lib(args=["/refresh"])

         ## 获取文档
         使用 /get 获取特定包的文档
         使用例子：

         lib(args=["/get", "byzer-llm"])

        目前仅支持用于大模型的 byzer-llm 包，用于数据分析的 byzer-sql 包。

        </usage>
        </command>

        <command>
        <name>models</name>
        <description>模型控制面板命令，用于管理和控制AI模型。</description>
        <usage>
        该命令用于管理和控制AI模型的配置和运行。 包含一个参数：query，字符串类型。
         
        ## 罗列模型模板

        models(query="/list")


        其中展示的结果中标注 * 好的模型表示目前已经激活（配置过api key)的。

        ##添加模型模板

        比如我想添加 open router 或者硅基流动的模型，则可以通过如下方式：
        
        models(query="/add_model name=openrouter-sonnet-3.5 base_url=https://openrouter.ai/api/v1")
        
        这样就能添加自定义模型: openrouter-sonnet-3.5
        

        如果你想添加添加硅基流动deepseek 模型的方式为：

        models(query="/add_model name=siliconflow_ds_2.5  base_url=https://api.siliconflow.cn/v1 model_name=deepseek-ai/DeepSeek-V2.5")

        name 为你取的一个名字，这意味着同一个模型，你可以添加多个，只要保证 name 不一样即可。
        base_url 是 硅基流动的 API 地址
        model_name 则为你在硅基流动选择的模型名

        ## 添加完模型后，你还需要能够激活模型:

        models(query="/activate <模型名，/add_mdoel里的 name字段> <YOUR_API_KEY>")

        之后你就可以这样配置来使用激活的模型：

        conf(conf="model:openrouter-sonnet-3.5")

        ## 删除模型

        models(query="/remove openrouter-sonnet-3.5")

        常见的供应商模型模板(以 DeepSeek R1 和 V3 模型为例)：

        ## openrouter
        models(query="/add_model name=or_r1_chat base_url=https://openrouter.ai/api/v1 model_name=deepseek/deepseek-r1:nitro")
        models(query="/add_model name=or_v3_chat base_url=https://openrouter.ai/api/v1 model_name=deepseek/deepseek-chat")

        ## 硅基流动
        models(query="/add_model name=siliconflow_r1_chat  base_url=https://api.siliconflow.cn/v1 model_name=Pro/deepseek-ai/DeepSeek-R1")
        models(query="/add_model name=siliconflow_v3_chat  base_url=https://api.siliconflow.cn/v1 model_name=Pro/deepseek-ai/DeepSeek-V3")

        ## 火山引擎/火山方舟

        models(query="/add_model name=ark_v3_chat base_url=https://ark.cn-beijing.volces.com/api/v3 model_name=<你的推理点名称>")
        models(query="/add_model name=ark_r1_chat base_url=https://ark.cn-beijing.volces.com/api/v3 model_name=<你的推理点名称> is_reasoning=true")

        ## 百度千帆

        models(query="/add_model name=qianfan_r1_chat base_url=https://qianfan.baidubce.com/v2 model_name=deepseek-r1 is_reasoning=true")
        models(query="/add_model name=qianfan_v3_chat base_url=https://qianfan.baidubce.com/v2 model_name=deepseek-v3")

        ## 阿里百炼
        models(query="/add_model name=ali_r1_chat base_url=https://dashscope.aliyuncs.com/compatible-mode/v1 model_name=deepseek-r1 is_reasoning=true")
        models(query="/add_model name=ali_deepseek_chat base_url=https://dashscope.aliyuncs.com/compatible-mode/v1 model_name=deepseek-v3")

        ## 腾讯混元
        models(query="/add_model name=tencent_r1_chat base_url=https://tencent.ai.qq.com/v1 model_name=deepseek-r1 is_reasoning=true")
        models(query="/add_model name=tencent_v3_chat base_url=https://tencent.ai.qq.com/v1 model_name=deepseek-v3")                

        *** 特别注意 ***
        
        在使用本函数时，如果添加的模型用户在需求中没有提供像推理点名称，激活时的 api key，以及模型名称等,从而导致添加模型会发生不确定性，
        你务必需要先通过函数 ask_user 来获取,之后得到完整信息再来执行 models 相关的操作。

        比如用户说：帮我添加火山方舟的 R1 模型。你需要先问：火山方舟的 R1 模型推理点是什么？然后你再问：火山方舟的 API key 是什么？
        收集到这两个信息后，你再执行：

        models(query="/add_model name=ark_r1_chat base_url=https://ark.cn-beijing.volces.com/api/v3 model_name=<收集到的推理点名称> is_reasoning=true")

        models(query="/activate ark_r1_chat <收集到的API key>")
        
        
        </usage>
        </command>

        <command>
        <name>ask_user</name>
        <description>
        如果你对用户的问题有什么疑问，或者你想从用户收集一些额外信息，可以调用此方法。
        输入参数 question 是你对用户的提问。
        返回值是 用户对你问题的回答。    
        ** 如果你的问题比较多，建议一次就问一个，然后根据用户回答再问下一个。 **
        </description>
        <usage>
         该命令接受一个参数 question，为需要向用户询问的问题字符串。
         
         使用例子：
         ask_user(question="请输入火山引擎的 R1 模型推理点")
         
        </command>

        <command>
        <name>run_python</name>
        <description>运行指定的Python代码。主要用于执行一些Python脚本或测试代码。</description>
        <usage>
         该命令接受一个参数 code，为要执行的Python代码字符串。
         
         使用例子：
         
         run_python(code="print('Hello World')")
         
         注意：
         - 代码将在项目根目录下执行
         - 可以访问项目中的所有文件
         - 输出结果会返回给用户
        </usage>
        </command>

        <command>
        <name>execute_shell_command</name>
        <description>运行指定的Shell脚本。主要用于编译、运行、测试等任务。</description>
        <usage>
         该命令接受一个参数 command，为要执行的Shell脚本字符串。
         
         
         使用例子：
         
         execute_shell_command(command="ls -l")
         
         注意：
         - 脚本将在项目根目录下执行
         - 禁止执行包含 rm 命令的脚本
         - 输出结果会返回给用户
         - 执行该命令的时候，需要通过 ask_user 询问用户是否同意执行，如果用户拒绝，则不再执行当前想执行的脚本呢。
        </usage>
        </command> 

        <command>
        <name>generate_shell_command</name>
        <description>
        根据用户需求描述，生成shell脚本。 
        </description>
        <usage>
          支持的参数名为 input_text， 字符串类型，用户的需求，使用该函数，会打印生成结果，用户可以更加清晰
          的看到生成的脚本。然后配合 ask_user, execute_shell_command 两个函数，最终完成
          脚本执行。
        </usage>
        </command>  


        <command>
        <name>get_project_structure</name>
        <description>返回当前项目结构</description>
        <usage>
         该命令不需要参数。返回一个目录树结构（类似 tree 命令的输出）
         
         使用例子：
         
         get_project_structure()
         
         该函数特别适合你通过目录结构来了解这个项目是什么类型的项目，有什么文件，如果你对一些文件
         感兴趣，可以配合 read_files 函数来读取文件内容，从而帮你做更好的决策
             
        </usage>
        </command>        

        <command>
        <name>get_project_map</name>
        <description>返回项目中指定文件包括文件用途、导入的包、定义的类、函数、变量等。</description>
        <usage>
         该命令接受一个参数 file_path，为文件路径（文件名或者文件路径的一部分）
         
         使用例子：
         
         get_project_map(file_path="main.py")

         该函数特别适合你想要了解某个文件的用途，以及该文件的导入的包，定义的类，函数，变量等信息。
         同时，你还能看到文件的大小（tokens数），以及索引的大小（tokens数），以及构建索引花费费用等信息。
         如果你觉得该文件确实是你关注的，你可以通过 read_files 函数来读取文件完整内容，从而帮你做更好的决策。
         
         注意：
         - 返回值为JSON格式文本
         - 只能返回已被索引的文件
        </usage>
        </command>

        <command>
        <name>read_files</name>
        <description>读取指定文件的内容（支持指定行范围），支持文件名或绝对路径。</description>
        <usage>
        该函数用于读取指定文件的内容。

        参数说明:
        1. paths (str): 
           - 以逗号分隔的文件路径列表
           - 支持两种格式:
             a) 文件名: 如果多个文件匹配该名称，将选择第一个匹配项
             b) 绝对路径: 直接指定文件的完整路径
           - 示例: "main.py,utils.py" 或 "/path/to/main.py,/path/to/utils.py"
           - 建议: 每次调用推荐一个文件，最多不要超过3个文件。

        2. line_ranges (Optional[str]):
           - 可选参数，用于指定每个文件要读取的具体行范围
           - 格式说明:
             * 使用逗号分隔不同文件的行范围
             * 每个文件可以指定多个行范围，用/分隔
             * 每个行范围使用-连接起始行和结束行
           - 示例: 
             * "1-100,2-50" (为两个文件分别指定一个行范围)
             * "1-100/200-300,50-100" (第一个文件指定两个行范围，第二个文件指定一个行范围)
           - 注意: line_ranges中的文件数量必须与paths中的文件数量一致，否则会抛出错误

        返回值:
        - 返回str类型，包含所有请求文件的内容
        - 每个文件内容前会标注文件路径和行范围信息（如果指定了行范围）

        使用例子：

        read_files(paths="main.py,utils.py", line_ranges="1-100/200-300,50-100")

        read_files(paths="main.py,utils.py") 

        你可以使用 get_project_structure 函数获取项目结构后，然后再通过 get_project_map 函数获取某个文件的用途，符号列表，以及
        文件大小（tokens数）,最后再通过 read_files 函数来读取文件内容，从而帮你做更好的决策。如果需要读取的文件过大，
        你可以通过指定行范围来读取文件内容，从而避免读取过多的内容，你可以多次用行范围来调用 read_files,直到你看到满意的内容为止。
        
        </usage>
        </command>

        <command>
        <name>find_files_by_name</name>
        <description>根据文件名中的关键字搜索文件。</description>
        <usage>
         该命令接受一个参数 keyword，为要搜索的关键字字符串。
         
         使用例子：
         
         find_files_by_name(keyword="test")
         
         注意：
         - 搜索不区分大小写
         - 返回所有匹配的文件路径，逗号分隔
        </usage>
        </command>

        <command>
        <name>find_files_by_content</name>
        <description>根据文件内容中的关键字搜索文件。</description>
        <usage>
         该命令接受一个参数 keyword，为要搜索的关键字字符串。
         
         使用例子：
         
         find_files_by_content(keyword="TODO")
         
         注意：
         - 搜索不区分大小写
         - 如果结果过多，只返回前10个匹配项
        </usage>
        </command>

        <command>
        <name>read_file_with_keyword_ranges</name>
        <description>读取包含指定关键字的行及其前后指定范围的行。</description>
        <usage>
         该函数用于读取包含关键字的行及其前后指定范围的行。

         参数说明:
         1. file_path (str): 文件路径，可以是相对路径或绝对路径
         2. keyword (str): 要搜索的关键字
         3. before_size (int): 关键字行之前要读取的行数，默认100
         4. after_size (int): 关键字行之后要读取的行数，默认100

         返回值:
         - 返回str类型，包含关键字的行及其前后指定范围的行
         - 格式如下：
           ```
           ##File: /path/to/file.py
           ##Line: 10-20
           
           内容
           ```

         使用例子：
         read_file_with_keyword_ranges(file_path="main.py", keyword="TODO", before_size=5, after_size=5)

         注意：
         - 如果文件中有多个匹配的关键字，会返回多个内容块
         - 搜索不区分大小写
        </usage>
        </command>

        <command>
        <name>conf_export</name>
        <description>配置管理命令，用于管理和控制配置。</description>
        <usage>
         该命令导出当前软件的配置，并保存到指定路径。
         
         使用例子：         
         conf_export(path="导出路径,通常是.json文件")
         
        </usage>
        </command>

        <command>
        <name>conf_import</name>
        <description>配置管理命令，用于管理和控制配置。</description>
        <usage>
         该命令导入指定路径的配置文件到当前软件。
         
         使用例子：         
         conf_import(path="导入路径,通常是.json文件")
         
        </usage>
        </command>

        <command>
        <name>index_export</name>
        <description>索引管理命令，用于管理和控制索引。</description>
        <usage>
         该命令导出当前软件的索引，并保存到指定路径。
         
         使用例子：         
         index_export(path="导出路径,通常是.json文件")
         
        </usage>
        </command>

        <command>
        <name>index_import</name>
        <description>索引管理命令，用于管理和控制索引。</description>
        <usage>
         该命令导入指定路径的索引文件到当前软件。
         
         使用例子：         
         index_import(path="导入路径，通常最后是.json文件")
         
        </usage>
        </command>

        <command>
        <name>exclude_files</name>
        <description>排除指定文件。</description>
        <usage>
         该命令接受一个参数 query, 为要排除的文件模式字符串,多个文件模式用逗号分隔。
         
         使用例子,比如你想要排除 package-lock.json 文件，你可以这样调用：
        
         exclude_files(query="regex://.*/package-lock\.json")
         
         注意：
         - 文件模式字符串必须以 regex:// 开头
         - regex:// 后面部分是标准的正则表达式         

         也支持子命令：
         /list 列出当前排除的文件模式
         /drop 删除指定的文件模式

         使用例子：
         exclude_files(query="/list")
         exclude_files(query="/drop regex://.*/package-lock\.json")
        </usage>
        </command>

        <command>
        <name>get_project_type</name>
        <description>获取项目类型。</description>
        <usage>
         该命令获取项目类型。

         使用例子：
         get_project_type()

         此时会返回诸如 "ts,py,java,go,js,ts" 这样的字符串，表示项目类型。
        </usage>
        </command>

        <command>
        <name>response_user</name>
        <description>响应用户。</description>
        <usage>
         如果你需要直接发送信息给用户，那么可以通过 response_user 函数来直接回复用户。
         
         比如用户问你是谁？
         你可以通过如下方式来回答：
         response_user(response="你好，我是 auto-coder")
        </usage>
        </command>
        </commands>
        
        
        '''
        return {
            "config_readme": config_readme.prompt()
        }

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
            "models": self.command_config.models,
            "execute_shell_command": self.command_config.execute_shell_command,
            "generate_shell_command": self.command_config.generate_shell_command,
            "conf_export": self.command_config.conf_export,
            "conf_import": self.command_config.conf_import,
            "index_export": self.command_config.index_export,
            "index_import": self.command_config.index_import,
            "exclude_files": self.command_config.exclude_files,

            "run_python": self.tools.run_python_code,            
            "get_related_files_by_symbols": self.tools.get_related_files_by_symbols,
            "get_project_map": self.tools.get_project_map,
            "get_project_structure": self.tools.get_project_structure,
            "read_files": self.tools.read_files,
            "find_files_by_name": self.tools.find_files_by_name,
            "find_files_by_content": self.tools.find_files_by_content,        
            "get_project_related_files": self.tools.get_project_related_files,
            "ask_user":self.tools.ask_user,
            "read_file_with_keyword_ranges": self.tools.read_file_with_keyword_ranges,
            "get_project_type": self.project_type_analyzer.analyze,
            "response_user": self.tools.response_user,
                                    
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
