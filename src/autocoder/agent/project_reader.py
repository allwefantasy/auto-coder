from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from autocoder.index.index import IndexManager
from autocoder.pyproject import PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.common.interpreter import Interpreter
from autocoder.common import ExecuteSteps, ExecuteStep
from autocoder.rag.simple_rag import SimpleRAG
from byzerllm.apps.llama_index.byzerai import ByzerAI
from loguru import logger
import os
import byzerllm
import yaml
import json


@byzerllm.prompt()
def context():
    """
    你的目标是帮助用户阅读和理解一个项目。
    """
@byzerllm.prompt()
def detect_rm_command(command: str) -> str:
    '''
    给定如下shell脚本：

    ```shell
    {{ command }}
    ```
    '''


def get_tools(args: AutoCoderArgs, llm: byzerllm.ByzerLLM):

    def run_python_code(code: str) -> str:
        """
        你可以通过该工具运行指定的Python代码。
        输入参数 code: Python代码
        返回值是Python代码的sys output 或者 sys error 信息。
        """
        interpreter = Interpreter(cwd=args.source_dir)
        s = ""
        try:
            s = interpreter.execute_steps(
                ExecuteSteps(
                    steps=[ExecuteStep(lang="python", code=code)]
                )
            )
        finally:
            interpreter.close()

        return s
    
    def run_shell_code(script: str) -> str:
        """
        你可以通过该工具运行指定的Shell代码。
        输入参数 script: Shell代码
        返回值是Shell代码的output 或者 error 信息。
        """        
        interpreter = Interpreter(cwd=args.source_dir)
        s = ""
        try:
            s = interpreter.execute_steps(
                ExecuteSteps(
                    steps=[ExecuteStep(lang="shell", code=script)]
                )
            )
        finally:
            interpreter.close()

        return s

    def get_project_related_files(query: str) -> str:
        """
        该工具会根据查询描述，返回项目中与查询相关的文件。
        返回文件路径列表。
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
        该工具会返回项目中所有文件以及文件的信息，诸如该文件的用途，导入的包，定义的类，函数，变量等信息。
        返回的是json格式文本。
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
            value["module_name"] = k["module_name"]
            value["symbols"] = k["symbols"]
            final_result.append(value)
        return json.dumps(final_result, ensure_ascii=False)

    def read_source_codes(paths: str) -> str:
        """
        你可以通过使用该工具获取相关文件的源代码。
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
                            path = os.path.join(root, path)
                            break

            with open(path, "r") as f:
                source_code = f.read()
                sc = SourceCode(module_name=path, source_code=source_code)
                source_code_str += f"##File: {sc.module_name}\n"
                source_code_str += f"{sc.source_code}\n\n"

        return source_code_str

    tools = [
        FunctionTool.from_defaults(get_project_related_files),
        FunctionTool.from_defaults(get_project_map),
        FunctionTool.from_defaults(read_source_codes),
        FunctionTool.from_defaults(run_python_code),
    ]
    return tools


class ProjectReader:
    def __init__(self, args: AutoCoderArgs, llm: byzerllm.ByzerLLM):
        self.llm = llm
        if args.planner_model:
            self.llm = self.llm.get_sub_client("planner_model")
        self.args = args
        self.tools = get_tools(args=args, llm=llm)

    def run(self, query: str, max_iterations: int = 10):
        agent = ReActAgent.from_tools(
            tools=self.tools,
            llm=ByzerAI(llm=self.llm),
            verbose=True,
            max_iterations=max_iterations,
            context=context.prompt(),
        )
        r = agent.chat(message=query)
        return r.response
