from enum import Enum
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
from autocoder.common.global_cancel import global_cancel,CancelRequestedException
from autocoder.common.auto_configure import config_readme
from autocoder.utils.auto_project_type import ProjectTypeAnalyzer
from rich.text import Text
from autocoder.common.mcp_server import get_mcp_server, McpServerInfoRequest
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events import event_content as EventContentCreator
from autocoder.events.event_types import Event, EventType, EventMetadata
from autocoder.run_context import get_run_context
from autocoder.common.stream_out_type import AutoCommandStreamOutType
from autocoder.common.rulefiles.autocoderrules_utils import get_rules
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
        self.project_type_analyzer = ProjectTypeAnalyzer(
            args=args, llm=self.llm)
        try:
            self.mcp_server = get_mcp_server()
            mcp_server_info_response = self.mcp_server.send_request(McpServerInfoRequest(
                model=args.inference_model or args.model,
                product_mode=args.product_mode
            ))
            self.mcp_server_info = mcp_server_info_response.result
        except Exception as e:
            logger.error(f"Error getting MCP server info: {str(e)}")
            self.mcp_server_info = ""    

    @byzerllm.prompt()
    def _analyze(self, request: AutoCommandRequest) -> str:
        """
        你是 auto-coder.chat 软件，帮助用户完成编程方面的需求。我们的目标是根据用户输入和当前上下文，组合多个函数来完成用户的需求。
        
        ====

        ## 当前用户环境信息如下:
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

        当前项目根目录：
        {{ current_project }}
    
        {% if current_files %}
        ## 当前用户手动添加关注的文件列表：
        <current_files>
        {% for file in current_files %}
        - {{ file }}
        {% endfor %}
        </current_files>
        {% endif %}


        ## 这是用户对你的配置        
        <current_conf>
        {{ current_conf }}
        </current_conf>

        ====

        ## 可用函数列表:
        {{ available_commands }}

        ## 当前大模型窗口安全值
        {{ conversation_safe_zone_tokens }}

        ## 函数组合说明：        
        {{ command_combination_readme }}

        ====

        ## active-context 项目追踪文档系统
        
        在 {{ current_project }}/.auto-coder/active-context 下,我们提供了对该项目每个文件目录的追踪。
        具体逻辑为：假设我们在当前项目有 ./src/package1/py1.py, 那么相应的在 .auto-coder/active-context 会有一个 ./src/package1 目录,
        该目录下可能会有一个 active-context.md 文件，该文件记录了该目录下所有文件相关信息，可以帮你更好的理解这个目录下的文档，你可以通过 read_files 函数来读取
        这个文件。注意，这个文件不一定存在。如果读取失败也是正常的。

        ## 变更记录文档系统

        在 {{ current_project }}/actions 目录下，会有格式类似 000000001201_chat_action.yml 的文件，该文件记录了最近10次对话，
        你可以通过 read_files 函数来读取这些文件，从而更好的理解用户的需求。

        下面是一些字段的简单介绍
        - query: 用户需求
        - urls： 用户提供的上下文文件列表
        - dynamic_urls： auto-coder.chat 自动感知的一些文件列表
        - add_updated_urls: 这次需求发生变更的文件列表                        

        {% if conversation_history %}
        ====
        ## 历史对话:
        <conversation_history>
        {% for conv in conversation_history %}
        ({{ conv.role }}): {{ conv.content }}
        {% endfor %}
        </conversation_history>
        {% endif %}
        
        {% if rules %}
        ====
        
        用户提供的规则文件，你必须严格遵守。
        {% for key, value in rules.items() %}
        <user_rule>
        ##File: {{ key }}
        {{ value }}
        </user_rule>
        {% endfor %}        
        {% endif %}

        ## 用户需求: 
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
            "conversation_history": [],
            "rules": get_rules(),
            "available_commands": self._command_readme.prompt(),
            "current_conf": json.dumps(self.memory_config.memory["conf"], indent=2),
            "env_info": env_info,
            "shell_type": shell_type,
            "shell_encoding": shells.get_terminal_encoding(),
            "conversation_safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens,
            "os_distribution": shells.get_os_distribution(),
            "current_user": shells.get_current_username(),
            "command_combination_readme": self._command_combination_readme.prompt(),
            "current_project": os.path.abspath(self.args.source_dir)
        }

    @byzerllm.prompt()
    def _command_combination_readme(self) -> str:
        """
        <function_combination_readme>
        如果用户是一个编码需求，你可以先简单观察当前活跃区文件列表：

        ### 是否根据需求动态修改auto-coder软件配置
        关注下当前软件的配置，结合当前用户的需求，如果觉得不合理的地方，可以通过 ask_user 函数来询问用户，是否要通过 help 函数修改一些配置。

        ### 如何了解当前项目

        通常可以自己通过调用 get_project_structure 函数来获取项目结构(如果项目结构太大，该函数会拒绝返回，你可以选择 list_files 函数来查看目录)，然后通过 get_project_map 函数来获取某几个文件的用途，符号列表，以及
        文件大小（tokens数）,最后再通过 read_files/read_file_with_keyword_ranges 函数来读取文件内容,从而更好的结合当前项目理解用户的需求。

        ### 复杂需求，先做讨论设计
        对于一个比较复杂的代码需求，你可以先通过 chat 函数来获得一些设计，根据chat返回的结果，你可以选择多次调用chat调整最后的设计。最后，当你满意后，可以通过 coding("/apply") 来完成最后的编码。
        注意，为了防止对话过长，你可以使用 chat("/new") 来创新新的会话。然后接着正常再次调用 chat 函数。 即可。
        尽可通过了解项目后，多用 @文件和@@符号，这样 chat 函数可以更清晰的理解你关注的代码，文档和意图。

        ### 调用 coding 函数应该注意的事项
        调用 coding 函数的之前，你需要尽可能先了解用户需求，了解项目状态，包括读取 active_context 文件来了解项目。
        然后清晰的描述自己的需求，完整的实现步骤，以及尽可能对@文件和@@符号需要参考以及修改的文件和符号。
        对于比较复杂的需求，你还可以使用 chat 函数来进行讨论，从而获取一些有用的信息。
        如果成功执行了 coding 函数， 最好再调用一次 chat("/review /commit")，方便总结这次代码变更。
        注意，review 完后，需要询问用户是否要做啥调整不，如果用户说不用，那么就停止。否则根据意图进行后续操作。

        ### 关于对话大小的问题
        我们对话历史以及查看的内容累计不能超过 {{ conversation_safe_zone_tokens }} 个tokens,当你读取索引文件 (get_project_map) 的时候，你可以看到
        每个文件的tokens数，你可以根据这个信息来决定如何读取这个文件。如果不确定，使用 count_file_tokens 函数来获取文件的tokens数,再决定如何读取。
        而对于分析一个超大文件推荐组合 read_files 带上 line_ranges 参数来读取，或者组合 read_file_with_keyword_ranges 等来读取，
        每个函数你还可以使用多次来获取更多信息。

        ### 善用脚本完成一些基本的操作
        根据操作系统，终端类型，脚本类型等各种信息，在涉及到路径或者脚本的时候，需要考虑平台差异性。

        ### 关于查看文件的技巧
        在使用 read_files 之前，如果你有明确的目标，比如查看这个文件某个函数在这个文件的实现，你可以先用 read_file_with_keyword_ranges 函数来大致定位,该函数会返回你看到的
        内容的行号范围，你可以通过拓展这个行号范围继续使用 read_file_with_line_ranges 来查看完整函数信息，或者使用 read_files 函数带上 line_ranges 参数来精确读取。 

        如果你没有明确目标，需要单纯查看这个文件获取必要的信息，可以先通过 count_file_tokens 函数来获取文件的tokens数，如果数目小于安全对话窗口的tokens数的1/2, 那么可以直接用
        read_files 函数来读取，否则建议一次读取200-600行，多次读取直到找到合适的信息。

        ## 其他一些注意事项
        1. 使用 read_files 时，一次性读取文件数量不要超过1个,每次只读取200行。如果发现读取的内容不够，则继续读取下面200行。
        2. 确实有必要才使用 get_project_structure 函数，否则可以多使用 list_files 函数来查看目录。
        3. 最后，不要局限在我们前面描述的使用说明中，根据各个函数的说明，灵活组合和使用各个函数，发挥自己的想象力，尽可能的完成用户的需求。
        </function_combination_readme>
        """

    @byzerllm.prompt()
    def _execute_command_result(self, result: str) -> str:
        '''
        根据函数执行结果，返回下一个函数。

        下面是我们上一个函数执行结果: 

        <function_result>
        {{ result }}
        </function_result>                

        请根据命令执行结果以及前面的对话，返回下一个函数。

        *** 非常非常重要的提示 ***
        1. 如果已经满足要求，则总是调用 response_user函数，对用户的初始问题根据前面所有信息做一次详细的回复。
        2. 你最多尝试 {{ auto_command_max_iterations }} 次，如果 {{ auto_command_max_iterations }} 次都没有满足要求，则不要返回任何函数，确保 suggestions 为空。
        '''
        return {
            "auto_command_max_iterations": self.args.auto_command_max_iterations,
            "conversation_safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens
        }

    def analyze(self, request: AutoCommandRequest) -> AutoCommandResponse:
        # 获取 prompt 内容
        prompt = self._analyze.prompt(request)

        # 获取对当前项目变更的最近8条历史人物
        action_yml_file_manager = ActionYmlFileManager(self.args.source_dir)
        history_tasks = action_yml_file_manager.to_tasks_prompt(limit=8)
        new_messages = []
        if self.args.enable_task_history:
            new_messages.append({"role": "user", "content": history_tasks})
            new_messages.append(
                {"role": "assistant", "content": "好的，我知道最近的任务对项目的变更了，我会参考这些来更好的理解你的需求。"})

        # 构造对话上下文
        conversations = new_messages + [{"role": "user", "content": prompt}]

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
                        params_str = ", ".join(
                            [f"{k}={v}" for k, v in parameters.items()])
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
            self.llm.stream_chat_oai(
                conversations=conversations, delta_mode=True),
            model_name=model_name,
            title=title,
            final_title=final_title,
            display_func=extract_command_response,
            args=self.args,
            extra_meta={
                "stream_out_type": AutoCommandStreamOutType.COMMAND_SUGGESTION.value,
                "path": "/agentic/agent/command_suggestion"
            }
        )

        if last_meta:
            elapsed_time = time.monotonic() - start_time
            speed = last_meta.generated_tokens_count / elapsed_time

            # Get model info for pricing
            from autocoder.utils import llms as llm_utils
            model_info = llm_utils.get_model_info(
                model_name, self.args.product_mode) or {}
            input_price = model_info.get(
                "input_price", 0.0) if model_info else 0.0
            output_price = model_info.get(
                "output_price", 0.0) if model_info else 0.0

            # Calculate costs
            input_cost = (last_meta.input_tokens_count *
                          input_price) / 1000000  # Convert to millions
            output_cost = (last_meta.generated_tokens_count *
                           output_price) / 1000000  # Convert to millions

            temp_content = printer.get_message_from_key_with_format("stream_out_stats",
                                                                    model_name=",".join(
                                                                        llms_utils.get_llm_names(self.llm)),
                                                                    elapsed_time=elapsed_time,
                                                                    first_token_time=last_meta.first_token_time,
                                                                    input_tokens=last_meta.input_tokens_count,
                                                                    output_tokens=last_meta.generated_tokens_count,
                                                                    input_cost=round(
                                                                        input_cost, 4),
                                                                    output_cost=round(
                                                                        output_cost, 4),
                                                                    speed=round(speed, 2))
            printer.print_str_in_terminal(temp_content)
            get_event_manager(self.args.event_file).write_result(
                EventContentCreator.create_result(content=EventContentCreator.ResultTokenStatContent(
                    model_name=model_name,
                    elapsed_time=elapsed_time,
                    first_token_time=last_meta.first_token_time,
                    input_tokens=last_meta.input_tokens_count,
                    output_tokens=last_meta.generated_tokens_count,
                    input_cost=round(input_cost, 4),
                    output_cost=round(output_cost, 4),
                    speed=round(speed, 2)
                )).to_dict()
                )

        # 这里打印

        conversations.append({"role": "assistant", "content": result})
        # 提取 JSON 并转换为 AutoCommandResponse
        response = to_model(result, AutoCommandResponse)
        
        result_manager = ResultManager()

        while True:
            global_cancel.check_and_raise(token=self.args.event_file)
            # 执行命令
            command = response.suggestions[0].command
            parameters = response.suggestions[0].parameters

            # 打印正在执行的命令
            temp_content = printer.get_message_from_key_with_format("auto_command_executing",                                                                    
                                                                    command=command
                                                                    )
            printer.print_str_in_terminal(temp_content,style="blue")

            get_event_manager(self.args.event_file).write_result(EventContentCreator.create_result(content=
                                                           EventContentCreator.ResultCommandPrepareStatContent(
                                                               command=command,
                                                               parameters=parameters
                                                           ).to_dict()),metadata=EventMetadata(
                                                               stream_out_type="command_prepare",
                                                               path="/agentic/agent/command_prepare",
                                                               action_file=self.args.file
                                                           ).to_dict())
            
            self.execute_auto_command(command, parameters)
            content = ""
            last_result = result_manager.get_last()
            if last_result:
                action = last_result.meta["action"]
                if action == "coding":
                    # 如果上一步是 coding，则需要把上一步的更改前和更改后的内容作为上下文
                    changes = git_utils.get_changes_by_commit_message(
                        "", last_result.meta["commit_message"])
                    if changes.success:
                        for file_path, change in changes.changes.items():
                            if change:
                                content += f"## File: {file_path}[更改前]\n{change.before or 'New File'}\n\nFile: {file_path}\n\n[更改后]\n{change.after or 'Deleted File'}\n\n"
                    else:
                        content = printer.get_message_from_key("no_changes_made")
                else:
                    # 其他的直接获取执行结果
                    content = last_result.content

                if action != command:
                    # command 和 action 不一致，则认为命令执行失败，退出
                    temp_content = printer.get_message_from_key_with_format(
                        "auto_command_action_break", command=command, action=action)
                    printer.print_str_in_terminal(temp_content,style="yellow")
                    get_event_manager(self.args.event_file).write_result(
                        EventContentCreator.create_result(content=temp_content),
                        metadata=EventMetadata(
                            stream_out_type="command_break",
                            path="/agentic/agent/command_break",
                            action_file=self.args.file
                        ).to_dict()
                    )
                    break

                if command == "response_user":
                    break

                get_event_manager(self.args.event_file).write_result(
                    EventContentCreator.create_result(content=EventContentCreator.ResultCommandExecuteStatContent(
                        command=command,
                        content=content
                    ).to_dict()),metadata=EventMetadata(
                        stream_out_type="command_execute",
                        path="/agentic/agent/command_execute",
                        action_file=self.args.file
                    ).to_dict()
                    )

                # 打印执行结果
                console = Console()
                # 截取content前后200字符
                truncated_content = content[:200] + "\n...\n" + \
                    content[-200:] if len(content) > 400 else content
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
                
                # 添加新的对话内容
                new_content = self._execute_command_result.prompt(content)
                conversations.append({"role": "user", "content": new_content})

                # 统计 token 数量
                total_tokens = count_tokens(json.dumps(
                    conversations, ensure_ascii=False))

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
                    self.llm.stream_chat_oai(
                        conversations=conversations, delta_mode=True),
                    model_name=model_name,
                    title=title,
                    final_title=final_title,
                    display_func=extract_command_response,
                    args=self.args,
                    extra_meta={
                        "stream_out_type": AutoCommandStreamOutType.COMMAND_SUGGESTION.value
                    }
                )

                if last_meta:
                    elapsed_time = time.monotonic() - start_time
                    printer = Printer()
                    speed = last_meta.generated_tokens_count / elapsed_time

                    # Get model info for pricing
                    from autocoder.utils import llms as llm_utils
                    model_info = llm_utils.get_model_info(
                        model_name, self.args.product_mode) or {}
                    input_price = model_info.get(
                        "input_price", 0.0) if model_info else 0.0
                    output_price = model_info.get(
                        "output_price", 0.0) if model_info else 0.0

                    # Calculate costs
                    input_cost = (last_meta.input_tokens_count *
                                  input_price) / 1000000  # Convert to millions
                    # Convert to millions
                    output_cost = (
                        last_meta.generated_tokens_count * output_price) / 1000000

                    temp_content = printer.get_message_from_key_with_format("stream_out_stats",
                                              model_name=model_name,
                                              elapsed_time=elapsed_time,
                                              first_token_time=last_meta.first_token_time,
                                              input_tokens=last_meta.input_tokens_count,
                                              output_tokens=last_meta.generated_tokens_count,
                                              input_cost=round(input_cost, 4),
                                              output_cost=round(
                                                  output_cost, 4),
                                              speed=round(speed, 2))
                    printer.print_str_in_terminal(temp_content)
                    get_event_manager(self.args.event_file).write_result(
                        EventContentCreator.create_result(content=EventContentCreator.ResultTokenStatContent(
                            model_name=model_name,
                            elapsed_time=elapsed_time,
                            first_token_time=last_meta.first_token_time,
                            input_tokens=last_meta.input_tokens_count,
                            output_tokens=last_meta.generated_tokens_count,
                        ).to_dict()))

                conversations.append({"role": "assistant", "content": result})
                # 提取 JSON 并转换为 AutoCommandResponse
                response = to_model(result, AutoCommandResponse)
                if not response or not response.suggestions:
                    break                                                             
            else:
                temp_content = printer.get_message_from_key_with_format("auto_command_break",  command=command)
                printer.print_str_in_terminal(temp_content,style="yellow")
                get_event_manager(self.args.event_file).write_result(
                    EventContentCreator.create_result(content=temp_content),
                    metadata=EventMetadata(
                        stream_out_type="command_break",
                        path="/agentic/agent/command_break",
                        action_file=self.args.file
                    ).to_dict()
                )
                break

        return response

    @byzerllm.prompt()
    def _command_readme(self) -> str:
        '''
        函数列表：

        <functions>
        <function>
        <name>add_files</name>
        <description>
          添加文件到活跃区，在使用 chat 或 coding 函数时，活跃区的文件会被自动包含在上下文中。
          支持多种添加方式：具体文件路径、模式匹配（glob 语法如 *.py）、相对路径或绝对路径。
          
          使用场景：
          1. 在执行 coding 前准备上下文
          2. 当 coding 执行结果缺少必要文件修改时进行补充，然后重新执行 coding 函数,或者在coding函数中的query显示 @需要的文件或者符号。          
          3. 用户可能会主动要求你帮他添加一些文件或者管理文件分组
        </description>
        <usage>
         该方法只有一个参数 args，为字符串列表类型。
         
         # 基本用法 - 直接添加文件

         ## 添加单个文件（推荐使用绝对路径）
         add_files(args=["/absolute/path/to/file1.py"])
         
         ## 添加多个文件
         add_files(args=["/path/to/file1.py", "/path/to/file2.py"])

         ## 使用模式匹配（支持 glob 语法）
         add_files(args=["**/*.py"])        # 添加所有 .py 文件
         add_files(args=["src/**/*.ts"])    # 添加 src 目录下所有 .ts 文件
         
         # 注意：添加文件时应尽量精确，避免添加过多无关文件
         
         # 子命令功能

         ## 刷新文件列表
         add_files(args=["/refresh"])

         ## 文件分组管理
         
         ### 创建新组并保存当前文件列表
         add_files(args=["/group", "/add", "my_group"])
         
         ### 删除指定组
         add_files(args=["/group", "/drop", "my_group"])
         
         ### 设置组描述信息
         add_files(args=["/group", "/set", "my_group", "这个组用于前端组件开发"])
         
         ### 列出所有已定义的组
         add_files(args=["/group", "/list"])
         
         ### 重置当前活跃组（保留文件列表）
         add_files(args=["/group", "/reset"])
         
         # 实用技巧：
         # - 可以先使用 find_files_by_name 或 find_files_by_content 查找相关文件
         # - 然后将结果添加到活跃区
         # - 对于大型项目，可以创建不同的文件组用于不同功能的开发
        </usage>        
        </function>

        <function>
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
        </function>

        <function>
        <name>list_files</name>
        <description>
          列出指定目录下的所有文件，帮助快速了解项目结构和文件组织。
          
          使用场景：
          1. 探索项目结构，了解特定目录包含哪些文件
          2. 在使用 read_files 或 add_files 前先确认目标文件
          3. 当 get_project_structure 返回内容过多时作为替代选择
          4. 寻找特定类型的文件（如配置文件、测试文件）
        </description>
        <usage>
         该函数接受一个参数 path，表示要列出文件的目录路径。
         
         # 基本用法
         
         ## 列出当前目录文件
         list_files(path=".")
         
         ## 列出指定目录文件
         list_files(path="/absolute/path/to/directory")
         list_files(path="src/components")
         
         ## 列出系统目录文件
         list_files(path="/tmp")
         
         # 注意事项：
         # - 只列出指定目录下的直接文件，不包括子目录中的文件
         # - 返回结果包含文件名，以换行符分隔
         # - 可与其他函数配合使用，如获取目录后通过 read_files 读取感兴趣的文件
         
         # 实用技巧：
         # - 结合 find_files_by_name 深入查找特定文件
         # - 遍历项目结构时可以先列出顶层目录，再逐层深入
         # - 查看构建输出或日志目录时特别有用
        </usage>
        </function>        

        <function>
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
        </function>

        <function>
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
        </function>        

        <function>
        <name>chat</name>
        <description>进入聊天模式，与AI进行交互对话。支持多轮对话、上下文理解和代码分析能力，是与系统进行自然交流的主要方式。</description>
        <usage>
         该命令支持丰富的交互方式和特殊功能，是你与AI交流的主要入口。

         ## 基础用法
         
         ### 基础对话
         直接输入对话内容，系统会结合上下文进行回答
         ```
         chat(query="这个项目使用了什么技术栈？")
         chat(query="如何优化当前代码的性能？")
         ```

         ### 会话管理
         使用 /new 开启全新对话，清除历史上下文
         ```
         chat(query="/new 让我们讨论新的话题")
         ```         

         ## 代码分析功能
         
         ### 代码审查
         使用 /review 请求对特定文件的代码审查
         ```
         chat(query="/review @main.py")
         chat(query="/review @src/components/Button.tsx 分析这个组件有什么可以改进的地方")
         ```
         
         ### 提交审查
         对最后一次代码提交进行审查
         ```
         chat(query="/review /commit")
         ```

         ## 特殊功能
         
         ### 上下文控制
         - `/no_context`：不使用当前文件上下文，适合纯粹的概念讨论
         ```
         chat(query="/no_context 解释一下什么是依赖注入")
         ```
         
         ### 高级检索
         - `/mcp`：获取 MCP 服务内容
         - `/rag`：使用检索增强生成，可结合外部知识库
         ```
         chat(query="/rag 查询如何开发插件")
         ```
         
         ### 结果管理
         - `/copy`：自动将结果复制到剪贴板
         - `/save`：将结果保存到全局记忆，自动加入后续上下文
         ```
         chat(query="/copy 生成一个处理用户登录的函数")
         chat(query="/save 总结这个项目的架构")
         ```

         ## 引用语法
         
         ### 文件引用
         使用 @ 引用特定文件，使回答更加针对性
         ```
         chat(query="@utils.py 这个文件的主要功能是什么？")
         chat(query="@src/models/User.js 这个模型有什么需要改进的地方？")
         ```
         
         ### 符号引用
         使用 @@ 引用特定函数或类，分析特定代码块
         ```
         chat(query="@@process_data 这个函数的实现有什么问题？")
         chat(query="@@UserController 这个类的设计是否合理？")
         ```
         
         ### 图片引用
         使用特殊标记引入图片，分析视觉内容
         ```
         chat(query="<_image_>screenshots/error.png</_image_> 这个错误如何解决？")
         chat(query="<_image_>design/flowchart.png</_image_> 根据这个流程图实现代码")
         ```

         ## 使用场景推荐
         
         - 项目探索：使用 chat 快速了解项目结构和关键组件
         - 代码分析：结合 @ 引用分析特定文件或组件
         - 问题诊断：遇到错误时，可以将错误信息发送给AI分析
         - 设计讨论：在编码前先讨论设计方案和架构选择
         - 学习辅助：询问特定技术或框架的使用方法

         ## 注意事项
         
         - 参考特定代码时尽量使用 @ 引用，可获得更精准的回答
         - 复杂问题可以分步提问，逐步深入
         - 使用 /save 保存重要信息，避免上下文丢失
         - 大型项目中建议指定文件范围，避免上下文过大
        </usage>
        </function>

        <function>
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

         *** 但我们推荐你直接自己讲 chat 返回的有用的信息直接放到 query 里 *** 而不是通过 /apply 带入。

         ## 引用语法
         - @文件名：引用特定文件
         - @@符号：引用函数或类
         - <img>图片路径</img>：引入图片

         使用例子：

         coding(query="@auth.py 添加JWT认证")
         coding(query="@@login 优化错误处理")
         coding(query="<img>design/flow.png</img> 实现这个流程图的功能")

         特别注意，在使用 coding 函数时，通过 ask_user 来确认是否执行 coding 函数，除非用户明确说不要询问，直接执行。
        </usage>
        </function>

        <function>
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
        </function>

        <function>
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
        </function>

        <function>
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

        </function>

        <function>
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
        </function>

        <function>
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
        </function> 

        <function>
        <name>generate_shell_command</name>
        <description>
        根据用户需求描述，生成shell脚本。 
        </description>
        <usage>
          支持的参数名为 input_text， 字符串类型，用户的需求，使用该函数，会打印生成结果，用户可以更加清晰
          的看到生成的脚本。然后配合 ask_user, execute_shell_command 两个函数，最终完成
          脚本执行。
        </usage>
        </function>  


        <function>
        <name>get_project_structure</name>
        <description>返回当前项目结构</description>
        <usage>
         该命令不需要参数。返回一个目录树结构（类似 tree 命令的输出）

         使用例子：

         get_project_structure()

         该函数特别适合你通过目录结构来了解这个项目是什么类型的项目，有什么文件，如果你对一些文件
         感兴趣，可以配合 read_files 函数来读取文件内容，从而帮你做更好的决策

        </usage>
        </function>        

        <function>
        <name>get_project_map</name>
        <description>返回项目中指定文件包括文件用途、导入的包、定义的类、函数、变量等。</description>
        <usage>
         该命令接受一个参数 file_paths，路径list,或者是以逗号分割的多个文件路径。
         路径支持相对路径和绝对路径。

         使用例子：

         get_project_map(file_paths=["full/path/to/main.py","partial/path/to/utils.py"])，

         或者：

         get_project_map(file_paths="full/path/to/main.py,partial/path/to/utils.py")

         该函数特别适合你想要了解某个文件的用途，以及该文件的导入的包，定义的类，函数，变量等信息。
         同时，你还能看到文件的大小（tokens数），以及索引的大小（tokens数），以及构建索引花费费用等信息。
         如果你觉得该文件确实是你关注的，你可以通过 read_files 函数来读取文件完整内容，从而帮你做更好的决策。

         注意：
         - 返回值为JSON格式文本
         - 只能返回已被索引的文件
        </usage>
        </function>

        <function>
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

        特别注意：使用 read_files 时，一次性读取文件数量不要超过1个,每次只读取200行。如果发现读取的内容不够，则继续读取下面200行。

        </usage>
        </function>

        <function>
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
        </function>

        <function>
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
        </function>

        <function>
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
        </function>

        <function>
        <name>conf_export</name>
        <description>配置管理命令，用于管理和控制配置。</description>
        <usage>
         该命令导出当前软件的配置，并保存到指定路径。

         使用例子：         
         conf_export(path="导出路径,通常是.json文件")

        </usage>
        </function>

        <function>
        <name>conf_import</name>
        <description>配置管理命令，用于管理和控制配置。</description>
        <usage>
         该命令导入指定路径的配置文件到当前软件。

         使用例子：         
         conf_import(path="导入路径,通常是.json文件")

        </usage>
        </function>

        <function>
        <name>index_export</name>
        <description>索引管理命令，用于管理和控制索引。</description>
        <usage>
         该命令导出当前软件的索引，并保存到指定路径。

         使用例子：         
         index_export(path="导出路径,通常是.json文件")

        </usage>
        </function>

        <function>
        <name>index_import</name>
        <description>索引管理命令，用于管理和控制索引。</description>
        <usage>
         该命令导入指定路径的索引文件到当前软件。

         使用例子：         
         index_import(path="导入路径，通常最后是.json文件")

        </usage>
        </function>

        <function>
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
        </function>

        <function>
        <name>get_project_type</name>
        <description>获取项目类型。</description>
        <usage>
         该命令获取项目类型。

         使用例子：
         get_project_type()

         此时会返回诸如 "ts,py,java,go,js,ts" 这样的字符串，表示项目类型。
        </usage>
        </function>

        <function>
        <name>response_user</name>
        <description>响应用户。</description>
        <usage>
         如果你需要直接发送信息给用户，那么可以通过 response_user 函数来直接回复用户。

         比如用户问你是谁？
         你可以通过如下方式来回答：
         response_user(response="你好，我是 auto-coder")
        </usage>
        </function>

        <function>
        <name>count_file_tokens</name>
        <description>计算指定文件的token数量。</description>
        <usage>
         该函数接受一个参数 file_path, 为要计算的文件路径。

         使用例子：
         count_file_tokens(file_path="full")

         注意：
         - 返回值为int类型，表示文件的token数量。

        </usage>
        </function>

        <function>
        <name>count_string_tokens</name>
        <description>计算指定字符串的token数量。</description>
        <usage>
         该函数接受一个参数 text, 为要计算的文本。

         使用例子：
         count_string_tokens(text="你好，世界")

         注意：
         - 返回值为int类型，表示文本的token数量。

        </usage>
        </function>

        <function>
        <n>find_symbol_definition</n>
        <description>查找指定符号的定义所在的文件路径。</description>
        <usage>
         该函数接受一个参数 symbol, 为要查找的符号名称。

         使用例子：
         find_symbol_definition(symbol="MyClass")
         find_symbol_definition(symbol="process_data")

         注意：
         - 返回值为字符串，包含符号定义所在的文件路径列表，以逗号分隔
         - 支持精确匹配和模糊匹配（不区分大小写）
         - 如果未找到匹配项，会返回提示信息

        </usage>
        </function>        

        <function>
        <n>execute_mcp_server</n>
        <description>执行MCP服务器</description>
        <usage>
         该函数接受一个参数 query, 为要执行的MCP服务器查询字符串。

         你可以根据下面已经连接的 mcp server 信息，来决定个是否调用该函数，注意该函数会更具你的 query 
         自动选择合适的 mcp server 来执行。如果你想某个特定的 server 来执行，你可以在 query 中说明你想哪个 server 执行。

         <mcp_server_info>
         {{ mcp_server_info }}
         </mcp_server_info>

        </usage>
        </function>                        
        '''
        return {
            "config_readme": config_readme.prompt(),
            "mcp_server_info": self.mcp_server_info
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
            "list_files": self.tools.list_files,
            "read_files": self.tools.read_files,
            "find_files_by_name": self.tools.find_files_by_name,
            "find_files_by_content": self.tools.find_files_by_content,
            "get_project_related_files": self.tools.get_project_related_files,
            "ask_user": self.tools.ask_user,
            "read_file_with_keyword_ranges": self.tools.read_file_with_keyword_ranges,
            "get_project_type": self.project_type_analyzer.analyze,
            "response_user": self.tools.response_user,
            "execute_mcp_server": self.tools.execute_mcp_server,
            "count_file_tokens": self.tools.count_file_tokens,
            "count_string_tokens": self.tools.count_string_tokens,
            "find_symbol_definition": self.tools.find_symbol_definition,

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
        except CancelRequestedException as e:
            raise e        

        except Exception as e:
            error_msg = str(e)
            self.printer.print_in_terminal(
                "auto_command_failed", style="red", command=command, error=error_msg)
            
            self.result_manager = ResultManager()
            result = f"command {command} with parameters {parameters} execution failed with error {error_msg}"
            self.result_manager.add_result(content=result, meta={
                "action": command,
                "input": parameters
            })
