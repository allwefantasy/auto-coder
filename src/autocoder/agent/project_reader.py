from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from autocoder.index.index import IndexManager
from autocoder.pyproject import PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.common.interpreter import Interpreter
from autocoder.common import ExecuteSteps, ExecuteStep,detect_env
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
import contextlib2
from pydantic import BaseModel
from byzerllm.types import Bool
from contextlib import contextmanager


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
    '''
    你的目标是帮助用户阅读和理解一个项目。请仔细阅读以下信息，以便更好地完成任务。

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

    工作流程建议:

    1. 首先使用get_related_files_by_symbols获取相关文件路径。
    2. 然后使用read_files读取这些文件的内容。
    3. 对于需要计算的问题（如代码行数、文件数量等），优先使用run_python_code。
    4. 如需执行Shell命令，使用run_shell_code，但要注意环境兼容性。
    5. 在无法通过上述方法获取足够信息时，可以使用get_project_map。
    6. 需要时，可以多次组合使用get_related_files_by_symbols和read_files以获取更全面的信息。

    请根据用户的具体需求，灵活运用这些工具来分析和理解项目。提供简洁、准确的回答，并在需要时主动提供深入解释的选项。
    '''
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

    def auto_run_job(job: str, context: str = "") -> str:
        """
        该工具会根据job描述，自动拆解任务，然后生成执行步骤，然后按执行步骤一个一个执行。
        输入参数 job: 任务描述
        输入参数 context: 上下文信息
        返回值是执行步骤的输出。

        该工具的主要用途是帮助用户自动执行一些任务，比如编译，运行，测试等。
        你需要通过目录结构（比如包含了pom文件，那么就是maven项目）并且搭配工具read_files(比如可以读取README.md)来获得一些context信息，
        指导该工具生成合适的执行步骤，帮助用户自动化完成任务。
        """
        executor = code_auto_execute.CodeAutoExecute(
            llm, args, code_auto_execute.Mode.SINGLE_ROUND
        )
        with redirect_stdout() as output:
            executor.run(query=job, context=context, source_code="")
        return output.getvalue()
    
    def get_related_files_by_symbols(query: str) -> str:
        '''
        你可以给出类名，函数名，以及文件的用途描述等信息，该工具会根据这些信息返回项目中相关的文件。
        '''
        return get_project_related_files(query)

    def get_project_related_files(query: str) -> str:
        """
        该工具会根据查询描述，根据索引返回项目中与查询相关的文件。
        返回值为按逗号分隔的文件路径列表。

        注意，该工具无法涵盖当前项目中所有文件，因为有些文件可能没有被索引。
        """
        if args.project_type == "ts":
            pp = TSProject(args=args, llm=llm)
        elif args.project_type == "py":
            pp = PyProject(args=args, llm=llm)
        else:
            pp = SuffixProject(args=args, llm=llm, file_filter=None)
        pp.run()
        sources = pp.sources

        index_manager = IndexManager(llm=llm, sources=sources, args=args)
        target_files = index_manager.get_target_files_by_query(query)
        file_list = target_files.file_list
        return ",".join([file.file_path for file in file_list])

    def get_project_map() -> str:
        """
        该工具会返回项目中所有已经被构建索引的文件以及该文件的信息，诸如该文件的用途，导入的包，定义的类，函数，变量等信息。
        返回的是json格式文本。

        注意，这个工具无法返回所有文件的信息，因为有些文件可能没有被索引。
        尽量避免使用该工具。
        """
        if args.project_type == "ts":
            pp = TSProject(args=args, llm=llm)
        elif args.project_type == "py":
            pp = PyProject(args=args, llm=llm)
        else:
            pp = SuffixProject(args=args, llm=llm, file_filter=None)
        pp.run()
        sources = pp.sources

        index_manager = IndexManager(llm=llm, sources=sources, args=args)
        s = index_manager.read_index_as_str()
        index_data = json.loads(s)

        final_result = []
        for k in index_data.values():
            value = {}
            value["file_name"] = k["module_name"]
            value["symbols"] = k["symbols"]
            final_result.append(value)
        return json.dumps(final_result, ensure_ascii=False)

    def read_files(paths: str) -> str:
        """
        你可以通过使用该工具获取相关文本文件的内容。
        输入参数 paths: 逗号分隔的文件路径列表,支持文件名（多个文件匹配上了，则选择第一个）或绝对路径
        返回值是文件的源代码。

        注意，paths数量务必不要太多，否则内容会太多，推荐输入最相关的5-6个文件来进行阅读。
        """
        paths = [p.strip() for p in paths.split(",")]
        source_code_str = ""
        for path in paths:
            if not os.path.isabs(path):
                # Find the first matching absolute path by traversing args.source_dir
                for root, _, files in os.walk(args.source_dir):
                    for file in files:
                        if path in os.path.join(root, file):
                            path = os.path.join(root,file)
                            break

            with open(path, "r") as f:
                source_code = f.read()
                sc = SourceCode(module_name=path, source_code=source_code)
                source_code_str += f"##File: {sc.module_name}\n"
                source_code_str += f"{sc.source_code}\n\n"

        return source_code_str

    tools = [
        # FunctionTool.from_defaults(get_project_related_files),
        FunctionTool.from_defaults(get_related_files_by_symbols),
        FunctionTool.from_defaults(get_project_map),
        FunctionTool.from_defaults(read_files),
        FunctionTool.from_defaults(run_python_code),
        FunctionTool.from_defaults(run_shell_code),
        # FunctionTool.from_defaults(auto_run_job),
    ]
    return tools


class ProjectReader:
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
        return r.response
