from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from autocoder.pyproject import PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs
from autocoder.common.interpreter import Interpreter
from autocoder.common import ExecuteSteps, ExecuteStep, detect_env
from autocoder.common import code_auto_execute
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

    1. run_python_code(code: str) -> str
       - 运行指定的Python代码。
       - 返回代码的标准输出或错误信息。
       - 使用时需指定项目根目录。

    2. run_shell_code(script: str) -> str
       - 运行指定的Shell代码，用于编译、运行、测试等任务。
       - 返回代码的输出或错误信息。
       - 注意：不允许执行包含rm命令的脚本。

    工作流程建议:

    1. 理解用户的任务需求。
    2. 使用提供的工具获取必要的信息和相关文件内容。
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
    def run_python_code(code: str) -> str:
        """
        你可以通过该工具运行指定的Python代码。
        输入参数 code: Python代码
        返回值是Python代码的sys output 或者 sys error 信息。

        通常你需要在代码中指定项目的根目录（前面我们已经提到了）。
        """
        interpreter = Interpreter(cwd=args.source_dir)
        s = ""
        try:
            s = interpreter.execute_steps(
                ExecuteSteps(steps=[ExecuteStep(lang="python", code=code)])
            )
        finally:
            interpreter.close()

        return s

    def run_shell_code(script: str) -> str:
        """
        你可以通过该工具运行指定的Shell代码。主要用于一些编译，运行，测试等任务。
        输入参数 script: Shell代码
        返回值是Shell代码的output 或者 error 信息。
        """

        if detect_rm_command.with_llm(llm).run(script).value:
            return "The script contains rm command, which is not allowed."

        interpreter = Interpreter(cwd=args.source_dir)
        s = ""
        try:
            s = interpreter.execute_steps(
                ExecuteSteps(steps=[ExecuteStep(lang="shell", code=script)])
            )
        finally:
            interpreter.close()

        return s

    tools = [
        FunctionTool.from_defaults(run_python_code),
        FunctionTool.from_defaults(run_shell_code),
    ]
    return tools


class AutoTool:
    def __init__(self, args: AutoCoderArgs, llm: byzerllm.ByzerLLM):
        self.llm = llm
        print(args.code_model)
        if args.code_model:
            self.llm = self.llm.get_sub_client("code_model")
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
