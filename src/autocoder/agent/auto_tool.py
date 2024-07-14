from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from autocoder.index.index import IndexManager
from autocoder.pyproject import PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.common.interpreter import Interpreter
from autocoder.common import ExecuteSteps, ExecuteStep, detect_env
from autocoder.common import code_auto_execute
from autocoder.rag.simple_rag import SimpleRAG
from byzerllm.apps.llama_index.byzerai import ByzerAI
from loguru import logger
import os
import io
import byzerllm
import yaml
import json
import sys
from contextlib import contextmanager
from pydantic import BaseModel
from byzerllm.types import Bool

@contextmanager
def redirect_stdout():
    original_stdout = sys.stdout
    sys.stdout = f = io.StringIO()
    try:
        yield f
    finally:
        sys.stdout = original_stdout

@byzerllm.prompt()
def context(project_map: str) -> str:
    """
    你的目标是协助用户执行各种任务，包括但不限于代码生成、修改、测试等。请仔细阅读以下信息，以便更好地完成任务。

    环境信息:

    操作系统: {{ env_info.os_name }} {{ env_info.os_version }}
    Python版本: {{ env_info.python_version }}
    {%- if env_info.conda_env %}
    Conda环境: {{ env_info.conda_env }}
    {%- endif %}
    {%- if env_info.virtualenv %}
    虚拟环境: {{ env_info.virtualenv }}
    {%- endif %}
    {%- if env_info.has_bash %}
    支持Bash
    {%- else %}
    不支持Bash
    {%- endif %}

    {{ project_map }}

    可用工具及使用指南:

    1. get_related_files_by_symbols(query: str) -> str
       - 根据类名、函数名或文件用途描述，返回项目中相关文件的路径列表。
       - 返回结果为逗号分隔的文件路径。

    2. read_files(paths: str) -> str
       - 读取指定文件的内容。
       - 输入为逗号分隔的文件路径列表（支持文件名或绝对路径）。
       - 建议每次最多读取5-6个最相关的文件。

    3. run_python_code(code: str) -> str
       - 运行指定的Python代码。
       - 返回代码的标准输出或错误信息。
       - 使用时需指定项目根目录。

    4. run_shell_code(script: str) -> str
       - 运行指定的Shell代码，用于编译、运行、测试等任务。
       - 返回代码的输出或错误信息。
       - 注意：不允许执行包含rm命令的脚本。

    5. get_project_map() -> str
       - 返回项目中已索引文件的信息，包括文件用途、导入包、定义的类、函数、变量等。
       - 返回JSON格式文本。
       - 仅在其他方法无法获得所需信息时使用。

    6. find_files_by_name(keyword: str) -> str
        - 根据关键字搜索项目中的文件名。
        - 返回文件名包含关键字的文件路径列表，以逗号分隔。

    7. find_files_by_content(keyword: str) -> str
        - 根据关键字搜索项目中的文件内容。
        - 返回内容包含关键字的文件路径列表，以逗号分隔。

    工作流程建议:

    1. 理解用户的任务需求。
    2. 使用提供的工具获取必要的项目信息和相关文件内容。
    3. 分析获取的信息，制定执行计划。
    4. 使用run_python_code或run_shell_code执行必要的操作。
    5. 分析执行结果，如有必要，进行调整并重复执行。
    6. 总结执行结果，并向用户提供清晰的反馈。

    请根据用户的具体需求，灵活运用这些工具来完成任务。提供简洁、准确的执行过程和结果说明。
    """
    return {"env_info": detect_env()}

@byzerllm.prompt()
def detect_rm_command(command: str) -> Bool:
    """
    给定如下shell脚本：

    ```shell
    {{ command }}
    ```

    如果该脚本中包含删除目录或者文件的命令，请返回True，否则返回False。
    """

def get_tools(args: AutoCoderArgs, llm: byzerllm.ByzerLLM):
    # 这里的工具函数实现与ProjectReader中的相同，只是略去了auto_run_job
    # 可以直接复制ProjectReader中的工具函数实现

    tools = [
        FunctionTool.from_defaults(get_related_files_by_symbols),
        FunctionTool.from_defaults(get_project_map),
        FunctionTool.from_defaults(read_files),
        FunctionTool.from_defaults(run_python_code),
        FunctionTool.from_defaults(run_shell_code),
        FunctionTool.from_defaults(find_files_by_name),
        FunctionTool.from_defaults(find_files_by_content),
    ]
    return tools

class AutoTool:
    def __init__(self, args: AutoCoderArgs, llm: byzerllm.ByzerLLM):
        self.llm = llm
        if args.planner_model:
            self.llm = self.llm.get_sub_client("planner_model")
        self.args = args
        self.tools = get_tools(args=args, llm=llm)
        if self.args.project_type == "ts":
            self.pp = TSProject(args=self.args, llm=llm)
        elif self.args.project_type == "py":
            self.pp = PyProject(args=self.args, llm=llm)
        else:
            self.pp = SuffixProject(args=self.args, llm=self.llm, file_filter=None)

    def get_tree_like_directory_structure(self) -> str:
        self.pp.run()
        return self.pp.get_tree_like_directory_structure.prompt()

    def run(self, query: str, max_iterations: int = 20):
        agent = ReActAgent.from_tools(
            tools=self.tools,
            llm=ByzerAI(llm=self.llm),
            verbose=True,
            max_iterations=max_iterations,
            context=context.prompt(
                project_map=self.get_tree_like_directory_structure(),
            ),
        )
        r = agent.chat(message=query)
        
        print("\n\n=============EXECUTE==================")
        executor = code_auto_execute.CodeAutoExecute(
            self.llm, self.args, code_auto_execute.Mode.SINGLE_ROUND
        )
        executor.run(query=query, context=r.response, source_code="")
        
        return r.response