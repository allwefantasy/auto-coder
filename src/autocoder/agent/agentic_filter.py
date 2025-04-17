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
from autocoder.common.global_cancel import global_cancel
from autocoder.common.auto_configure import config_readme
from autocoder.utils.auto_project_type import ProjectTypeAnalyzer
from rich.text import Text
from autocoder.common.mcp_server import get_mcp_server, McpServerInfoRequest
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events import event_content as EventContentCreator
from autocoder.run_context import get_run_context
from autocoder.common.stream_out_type import AgenticFilterStreamOutType


class AgenticFilterRequest(BaseModel):
    user_input: str


class FileOperation(BaseModel):
    path: str
    operation: str  # e.g., "MODIFY", "REFERENCE", "ADD", "REMOVE"


class AgenticFilterResponse(BaseModel):
    files: List[FileOperation]  # 文件列表，包含path和operation字段
    reasoning: str  # 决策过程说明


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


class AgenticFilter:
    def __init__(
        self,
        llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM],
        conversation_history: List[Dict[str, Any]],
        args: AutoCoderArgs,
        memory_config: MemoryConfig,
        command_config: Optional[CommandConfig] = None,
    ):
        self.llm = llm
        self.args = args
        self.printer = Printer()
        self.tools = AutoCommandTools(args=args, llm=self.llm)
        self.result_manager = ResultManager(source_dir=args.source_dir)
        # Use existing args for max iterations
        self.max_iterations = args.auto_command_max_iterations
        self.conversation_history = conversation_history
        self.memory_config = memory_config
        self.command_config = command_config
        self.project_type_analyzer = ProjectTypeAnalyzer(args=args, llm=self.llm)
        try:
            self.mcp_server = get_mcp_server()
            mcp_server_info_response = self.mcp_server.send_request(
                McpServerInfoRequest(
                    model=args.inference_model or args.model,
                    product_mode=args.product_mode,
                )
            )
            self.mcp_server_info = mcp_server_info_response.result
        except Exception as e:
            logger.error(f"Error getting MCP server info: {str(e)}")
            self.mcp_server_info = ""

    @byzerllm.prompt()
    def _analyze(self, request: AgenticFilterRequest) -> str:
        """        
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

        ## 可用函数列表:
        {{ available_commands }}

        ## 当前大模型窗口安全值
        {{ conversation_safe_zone_tokens }}

        ## Token 安全区
        对话和文件内容的总Token数不应超过 {{ conversation_safe_zone_tokens }}。请谨慎读取大文件。  
        
        ## 对话历史
        <conversation_history>
        {% for msg in conversation_history %}
        **{{ msg.role }}**: {{ msg.content }}
        {% endfor %}
        </conversation_history>
        
        ## 完成任务的一些实践指导
        {{ command_combination_readme }}
        
        ## 你的任务以及要求
        你是一个代码分析专家，需要根据用户的需求分析项目中相关的文件。你的工作是确定：

        1. **需要修改的文件**（标记为"MODIFY"）：直接需要更改的文件
        2. **需要参考的文件**（标记为"REFERENCE"）：理解需求或实现修改所需参考的文件
        3. **需要新增的文件**（标记为"ADD"）：实现需求可能需要创建的新文件
        4. **需要删除的文件**（标记为"REMOVE"）：实现需求可能需要删除的文件

        请通过以下步骤进行分析：
        1. 理解用户需求的核心目标
        2. 使用提供的工具函数探索项目结构
        3. 分析相关文件的内容和依赖关系
        4. 确定需要修改、参考、新增或删除的文件列表

        ## 返回格式要求
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

        请返回第一个建议的函数调用。我会将每个函数的执行结果提供给你，然后你可以根据这些结果确定下一步要执行的函数，直到完成分析。
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
            "conversation_history": self.conversation_history,
            "available_commands": self._command_readme.prompt(),
            "current_conf": json.dumps(self.memory_config.memory["conf"], indent=2),
            "env_info": env_info,
            "shell_type": shell_type,
            "shell_encoding": shells.get_terminal_encoding(),
            "conversation_safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens,
            "os_distribution": shells.get_os_distribution(),
            "current_user": shells.get_current_username(),
            "command_combination_readme": self._command_combination_readme.prompt(
                user_input=request.user_input
            ),
            "current_project": os.path.abspath(self.args.source_dir),
        }

    @byzerllm.prompt()
    def _command_combination_readme(self, user_input: str) -> str:
        """
        ## 操作流程建议
        1.  **理解需求**: 分析用户输入 `{{ user_input }}`。
        2.  **探索项目**:
            *   使用 `list_files` 层层递进了解项目结构，用来确定需要关注的文件。
            *   如果用户提及文件名等，则可以使用 `find_files_by_name` 或，如果用户提到关键字则可以使用 `find_files_by_content` 定位可能相关的文件。
            *   如果用户提到了具体的符号（函数，类名等）则可以使用 `get_project_map` 获取候选文件的详细信息（如符号）。
        3.  **深入分析**:
            *   使用 `read_files` 读取关键文件的内容进行确认。如果文件过大，使用 `line_ranges` 参数分段读取。
            *   如有必要，使用 `run_python` 或 `execute_shell_command` 执行代码或命令进行更复杂的分析。
        4.  **迭代决策**: 根据工具的返回结果，你可能需要多次调用不同的工具来逐步缩小范围或获取更多信息。        
        6.  **最终响应**: 当你确定了所有需要参考和修改的文件后，**必须**调用 `output_result` 工具，并提供符合其要求格式的JSON字符串作为其 `response` 参数。
            该json格式要求为：
            ```json
            {
                "files": [
                    {"path": "/path/to/file1.py", "operation": "MODIFY"},
                    {"path": "/path/to/file2.md", "operation": "REFERENCE"},
                    {"path": "/path/to/new_file.txt", "operation": "ADD"},
                    {"path": "/path/to/old_file.log", "operation": "REMOVE"}
                ],
                "reasoning": "详细说明你是如何通过分析和使用工具得出这个文件列表的。"
            }
            ```
        
        {% if enable_active_context %}
        ** 非常非常重要的提示 **
        每一个目录都有一个描述信息，比如 {{ project_path }}/src/abc/bbc 的目录描述信息会放在 {{ project_path }}/.auto-coder/active-context/src/abc/bbc/active.md 文件中。
        你可以使用 read_files 函数读取，从而帮助你更好的挑选要详细阅读哪个文件。值得注意的是，active.md 并不会包含该目录下所有的文件信息，只保存最近发生变更的文件的信息。
        {% endif %}
        """        
        return {
            "project_path": os.path.abspath(self.args.source_dir),
            "enable_active_context": self.args.enable_active_context,
        }

    @byzerllm.prompt()
    def _execute_command_result(self, result: str) -> str:
        """
        根据函数执行结果，返回下一个函数。

        下面是我们上一个函数执行结果:

        <function_result>
        {{ result }}
        </function_result>

        请根据命令执行结果以及前面的对话，返回下一个函数。

        *** 非常非常重要的提示 ***
        1. 如果你认为已经收集到足够信息来确定最终的文件列表，请务必调用 `output_result` 并以如下格式要求的JSON字符串作为 `response` 参数。最多允许 {{ max_iterations }} 次工具调用。
            ```json
            {
                "files": [
                    {"path": "/path/to/file1.py", "operation": "MODIFY"},
                    {"path": "/path/to/file2.md", "operation": "REFERENCE"},
                    {"path": "/path/to/new_file.txt", "operation": "ADD"},
                    {"path": "/path/to/old_file.log", "operation": "REMOVE"}
                ],
                "reasoning": "详细说明你是如何通过分析和使用工具得出这个文件列表的。"
            }
            ```
        2. 你最多尝试 {{ auto_command_max_iterations }} 次，如果 {{ auto_command_max_iterations }} 次都没有满足要求，则不要返回任何函数，确保 suggestions 为空。
        """
        return {
            "auto_command_max_iterations": self.args.auto_command_max_iterations,
            "conversation_safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens,
        }

    @byzerllm.prompt()
    def _command_readme(self) -> str:
        """
        你有如下函数可供使用：
        <commands>
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
        </command>

        <command>
        <name>list_files</name>
        <description>list_files 查看某个目录下的所有文件</description>
        <usage>
         该命令接受一个参数 path, 为要查看的目录路径。
         使用例子：
         list_files(path="path/to/dir")

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

        特别注意：使用 read_files 时，一次性读取文件数量不要超过1个,每次只读取200行。如果发现读取的内容不够，则继续读取下面200行。

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
        <name>output_result</name>
        <description>输出最后需要的结果</description>
        <usage>
         只有一个参数：
         response: 字符串类型，需要返回给用户的内容。 response 必须满足如下Json格式：

         ```json
        {
            "files": [
                {"path": "/path/to/file1.py", "operation": "MODIFY"},
                {"path": "/path/to/file2.md", "operation": "REFERENCE"},
                {"path": "/path/to/new_file.txt", "operation": "ADD"},
                {"path": "/path/to/old_file.log", "operation": "REMOVE"}
            ],
            "reasoning": "详细说明你是如何通过分析和使用工具得出这个文件列表的。"
        }
        ```

        使用例子：
        output_result(response='{"files": [{"path": "/path/to/file1.py", "operation": "MODIFY"}, {"path": "/path/to/file2.md", "operation": "REFERENCE"}, {"path": "/path/to/new_file.txt", "operation": "ADD"}, {"path": "/path/to/old_file.log", "operation": "REMOVE"}], "reasoning": "详细说明你是如何通过分析和使用工具得出这个文件列表的。"}')
        </usage>
        </command>

        <command>
        <name>count_file_tokens</name>
        <description>计算指定文件的token数量。</description>
        <usage>
         该函数接受一个参数 file_path, 为要计算的文件路径。

         使用例子：
         count_file_tokens(file_path="full")

         注意：
         - 返回值为int类型，表示文件的token数量。

        </usage>
        </command>

        <command>
        <name>count_string_tokens</name>
        <description>计算指定字符串的token数量。</description>
        <usage>
         该函数接受一个参数 text, 为要计算的文本。

         使用例子：
         count_string_tokens(text="你好，世界")

         注意：
         - 返回值为int类型，表示文本的token数量。

        </usage>
        </command>

        <command>
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
        </command>        
        <command>
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
        </command>
        """
        return {
            "config_readme": config_readme.prompt(),
            "mcp_server_info": self.mcp_server_info,
        }

    def analyze(self, request: AgenticFilterRequest) -> Optional[AgenticFilterResponse]:
        # 获取 prompt 内容
        prompt = self._analyze.prompt(request)

        # 获取对当前项目变更的最近8条历史人物
        action_yml_file_manager = ActionYmlFileManager(self.args.source_dir)
        history_tasks = action_yml_file_manager.to_tasks_prompt(limit=8)
        new_messages = []
        if self.args.enable_task_history:
            new_messages.append({"role": "user", "content": history_tasks})
            new_messages.append(
                {
                    "role": "assistant",
                    "content": "好的，我知道最近的任务对项目的变更了，我会参考这些来更好的理解你的需求。",
                }
            )

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
                            [f"{k}={v}" for k, v in parameters.items()]
                        )
                    else:
                        params_str = ""
                    return f"{command}({params_str})"
                else:
                    return printer.get_message_from_key("satisfied_prompt")
            except Exception as e:
                logger.error(f"Error extracting command response: {str(e)}")
                return content

        result_manager = ResultManager()
        success_flag = False

        get_event_manager(self.args.event_file).write_result(
            EventContentCreator.create_result(content=printer.get_message_from_key("agenticFilterContext")),
            metadata={
                "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value                    
            }
        )

        while True:
            global_cancel.check_and_raise(token=self.args.event_file)
            # print(json.dumps(conversations, ensure_ascii=False, indent=4))
            model_name = ",".join(llms_utils.get_llm_names(self.llm))
            start_time = time.monotonic()
            result, last_meta = stream_out(
                self.llm.stream_chat_oai(conversations=conversations, delta_mode=True),
                model_name=model_name,
                title=title,
                final_title=final_title,
                display_func=extract_command_response,
                args=self.args,
                extra_meta={
                    "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value                    
                },
            )

            if last_meta:
                elapsed_time = time.monotonic() - start_time
                speed = last_meta.generated_tokens_count / elapsed_time

                # Get model info for pricing
                from autocoder.utils import llms as llm_utils

                model_info = (
                    llm_utils.get_model_info(model_name, self.args.product_mode) or {}
                )
                input_price = model_info.get("input_price", 0.0) if model_info else 0.0
                output_price = (
                    model_info.get("output_price", 0.0) if model_info else 0.0
                )

                # Calculate costs
                input_cost = (
                    last_meta.input_tokens_count * input_price
                ) / 1000000  # Convert to millions
                output_cost = (
                    last_meta.generated_tokens_count * output_price
                ) / 1000000  # Convert to millions

                temp_content = printer.get_message_from_key_with_format(
                    "stream_out_stats",
                    model_name=",".join(llms_utils.get_llm_names(self.llm)),
                    elapsed_time=elapsed_time,
                    first_token_time=last_meta.first_token_time,
                    input_tokens=last_meta.input_tokens_count,
                    output_tokens=last_meta.generated_tokens_count,
                    input_cost=round(input_cost, 4),
                    output_cost=round(output_cost, 4),
                    speed=round(speed, 2),
                )
                printer.print_str_in_terminal(temp_content)
                get_event_manager(self.args.event_file).write_result(
                    EventContentCreator.create_result(
                        content=EventContentCreator.ResultTokenStatContent(
                            model_name=model_name,
                            elapsed_time=elapsed_time,
                            first_token_time=last_meta.first_token_time,
                            input_tokens=last_meta.input_tokens_count,
                            output_tokens=last_meta.generated_tokens_count,
                            input_cost=round(input_cost, 4),
                            output_cost=round(output_cost, 4),
                            speed=round(speed, 2),
                        )
                    ).to_dict()
                )

            conversations.append({"role": "assistant", "content": result})
            # 提取 JSON 并转换为 AutoCommandResponse
            response = to_model(result, AutoCommandResponse)

            if not response or not response.suggestions:
                break

            # 执行命令
            command = response.suggestions[0].command
            parameters = response.suggestions[0].parameters

            # 打印正在执行的命令
            temp_content = printer.get_message_from_key_with_format(
                "auto_command_executing", command=command
            )
            printer.print_str_in_terminal(temp_content, style="blue")

            get_event_manager(self.args.event_file).write_result(
                EventContentCreator.create_result(
                    content=EventContentCreator.ResultCommandPrepareStatContent(
                        command=command, parameters=parameters
                    ).to_dict()
                ),metadata={
                    "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value                    
                }
            )
            try:
                self.execute_auto_command(command, parameters)
            except Exception as e:
                error_content = f"执行命令失败，错误信息：{e}"
                conversations.append({"role": "user", "content": error_content})
                continue

            content = ""
            last_result = result_manager.get_last()
            if last_result:
                action = last_result.meta["action"]
                if action == "coding":
                    # 如果上一步是 coding，则需要把上一步的更改前和更改后的内容作为上下文
                    changes = git_utils.get_changes_by_commit_message(
                        "", last_result.meta["commit_message"]
                    )
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
                        "auto_command_action_break", command=command, action=action
                    )
                    printer.print_str_in_terminal(temp_content, style="yellow")
                    get_event_manager(self.args.event_file).write_result(
                        EventContentCreator.create_result(content=temp_content),
                        metadata={
                            "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value                    
                        }
                    )
                    break

                if command == "output_result":
                    success_flag = True
                    break

                get_event_manager(self.args.event_file).write_result(
                    EventContentCreator.create_result(
                        content=EventContentCreator.ResultCommandExecuteStatContent(
                            command=command, content=content
                        ).to_dict(),
                        metadata={
                            "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value                    
                        }
                    )
                )

                # 打印执行结果
                console = Console()
                # 截取content前后200字符
                truncated_content = (
                    content[:200] + "\n...\n" + content[-200:]
                    if len(content) > 400
                    else content
                )
                title = printer.get_message_from_key_with_format(
                    "command_execution_result", action=action
                )
                # 转义内容，避免Rich将内容中的[]解释为markup语法
                text_content = Text(truncated_content)
                console.print(
                    Panel(
                        text_content, title=title, border_style="blue", padding=(1, 2)
                    )
                )

                # 添加新的对话内容
                new_content = self._execute_command_result.prompt(content)
                conversations.append({"role": "user", "content": new_content})

                # 统计 token 数量
                total_tokens = count_tokens(
                    json.dumps(conversations, ensure_ascii=False)
                )

                # 如果对话过长，使用默认策略进行修剪
                if total_tokens > self.args.conversation_prune_safe_zone_tokens:
                    self.printer.print_in_terminal(
                        "conversation_pruning_start",
                        style="yellow",
                        total_tokens=total_tokens,
                        safe_zone=self.args.conversation_prune_safe_zone_tokens,
                    )
                    from autocoder.common.conversation_pruner import ConversationPruner

                    pruner = ConversationPruner(self.args, self.llm)
                    conversations = pruner.prune_conversations(conversations)

            else:
                temp_content = printer.get_message_from_key_with_format(
                    "auto_command_break", command=command
                )
                printer.print_str_in_terminal(temp_content, style="yellow")
                get_event_manager(self.args.event_file).write_result(
                    EventContentCreator.create_result(content=temp_content),
                    metadata={
                        "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value                    
                    }
                )
                break

        get_event_manager(self.args.event_file).write_result(
            EventContentCreator.create_result(content=printer.get_message_from_key("agenticFilterCommandResult")),
            metadata={
                "stream_out_type": AgenticFilterStreamOutType.AGENTIC_FILTER.value                    
            }
        )    

        if success_flag:
            to_model(content, AgenticFilterResponse)
            # return AgenticFilterResponse(**json.loads(content))
        else:
            return None

    def execute_auto_command(self, command: str, parameters: Dict[str, Any]) -> None:
        """
        执行自动生成的命令
        """
        command_map = {
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
            "output_result": self.tools.output_result,
            "execute_mcp_server": self.tools.execute_mcp_server,
            "count_file_tokens": self.tools.count_file_tokens,
            "count_string_tokens": self.tools.count_string_tokens,
            "find_symbol_definition": self.tools.find_symbol_definition,
        }

        if command not in command_map:
            v = self.printer.get_message_from_key_with_format(
                "auto_command_not_found", style="red", command=command
            )
            raise Exception(v)
            return

        try:
            # 将参数字典转换为命令所需的格式
            if parameters:
                command_map[command](**parameters)
            else:
                command_map[command]()

        except Exception as e:
            error_msg = str(e)
            v = self.printer.get_message_from_key_with_format(
                "auto_command_failed", style="red", command=command, error=error_msg
            )
            self.result_manager = ResultManager()
            result = f"command {command} with parameters {parameters} execution failed with error {error_msg}"
            self.result_manager.add_result(content=result, meta={
                "action": command,
                "input": parameters
            })
