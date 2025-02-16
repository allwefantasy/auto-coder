from autocoder.index.index import IndexManager
from autocoder.pyproject import PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.common.interpreter import Interpreter
from autocoder.common import ExecuteSteps, ExecuteStep, detect_env
from autocoder.common import code_auto_execute
import os
import byzerllm
import json
from pydantic import BaseModel
from byzerllm.types import Bool
from contextlib import contextmanager
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt
from typing import Union
from autocoder.utils.queue_communicate import (
    queue_communicate,
    CommunicateEvent,
    CommunicateEventType,
)
import sys
import io

@byzerllm.prompt()
def detect_rm_command(command: str) -> Bool:
    """
    给定如下shell脚本：

    ```shell
    {{ command }}
    ```

    如果该脚本中包含删除目录或者文件的命令，请返回True，否则返回False。
    """

@contextmanager
def redirect_stdout():
    original_stdout = sys.stdout
    sys.stdout = f = io.StringIO()
    try:
        yield f
    finally:
        sys.stdout = original_stdout    

class AutoCommandTools:
    def __init__(self, args: AutoCoderArgs, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        self.args = args
        self.llm = llm

    def ask_user(self,question:str) -> str:
        '''
        如果你对用户的问题有什么疑问，或者你想从用户收集一些额外信息，可以调用此方法。
        输入参数 question 是你对用户的提问。
        返回值是 用户对你问题的回答。

        注意，尽量不要询问用户，除非你感受到你无法回答用户的问题。
        '''

        if self.args.request_id and not self.args.silence and not self.args.skip_events:
            event_data = {
                "question": question                
            }
            response_json = queue_communicate.send_event(
                request_id=self.args.request_id,
                event=CommunicateEvent(
                    event_type=CommunicateEventType.ASK_HUMAN.value,
                    data=json.dumps(event_data, ensure_ascii=False),
                ),
            )
            return response_json

        console = Console()

        # 创建一个醒目的问题面板
        question_text = Text(question, style="bold cyan")
        question_panel = Panel(
            question_text,
            title="[bold yellow]auto-coder.chat's Question[/bold yellow]",
            border_style="blue",
            expand=False
        )

        # 显示问题面板
        console.print(question_panel)

        # 创建一个自定义提示符
        prompt = Prompt.ask(
            "\n[bold green]Your Answer[/bold green]",
            console=console
        )

        # 获取用户的回答
        answer = prompt

        # 显示用户的回答
        answer_text = Text(answer, style="italic")
        answer_panel = Panel(
            answer_text,
            title="[bold yellow]Your Response[/bold yellow]",
            border_style="green",
            expand=False
        )
        console.print(answer_panel)

        return answer

    def run_python_code(self, code: str) -> str:
        """
        你可以通过该工具运行指定的Python代码。
        输入参数 code: Python代码
        返回值是Python代码的sys output 或者 sys error 信息。

        通常你需要在代码中指定项目的根目录（前面我们已经提到了）。
        """
        interpreter = Interpreter(cwd=self.args.source_dir)
        s = ""
        try:
            s = interpreter.execute_steps(
                ExecuteSteps(steps=[ExecuteStep(lang="python", code=code)])
            )
        finally:
            interpreter.close()

        return s

    def run_shell_code(self, script: str) -> str:
        """
        你可以通过该工具运行指定的Shell代码。主要用于一些编译，运行，测试等任务。
        输入参数 script: Shell代码
        返回值是Shell代码的output 或者 error 信息。
        """

        if detect_rm_command.with_llm(self.llm).run(script).value:
            return "The script contains rm command, which is not allowed."

        interpreter = Interpreter(cwd=self.args.source_dir)
        s = ""
        try:
            s = interpreter.execute_steps(
                ExecuteSteps(steps=[ExecuteStep(lang="shell", code=script)])
            )
        finally:
            interpreter.close()

        return s
   
    def get_related_files_by_symbols(self, query: str) -> str:
        """
        你可以给出类名，函数名，以及文件的用途描述等信息，该工具会根据这些信息返回项目中相关的文件。
        """
        return self.get_project_related_files(query)

    def get_project_related_files(self, query: str) -> str:
        """
        该工具会根据查询描述，根据索引返回项目中与查询相关的文件。
        返回值为按逗号分隔的文件路径列表。

        注意，该工具无法涵盖当前项目中所有文件，因为有些文件可能没有被索引。
        """
        if self.args.project_type == "ts":
            pp = TSProject(args=self.args, llm=self.llm)
        elif self.args.project_type == "py":
            pp = PyProject(args=self.args, llm=self.llm)
        else:
            pp = SuffixProject(args=self.args, llm=self.llm, file_filter=None)
        pp.run()
        sources = pp.sources

        index_manager = IndexManager(llm=self.llm, sources=sources, args=self.args)
        target_files = index_manager.get_target_files_by_query(query)
        file_list = target_files.file_list
        return ",".join([file.file_path for file in file_list])

    def get_project_map(self) -> str:
        """
        该工具会返回项目中所有已经被构建索引的文件以及该文件的信息，诸如该文件的用途，导入的包，定义的类，函数，变量等信息。
        返回的是json格式文本。

        注意，这个工具无法返回所有文件的信息，因为有些文件可能没有被索引。
        尽量避免使用该工具。
        """
        if self.args.project_type == "ts":
            pp = TSProject(args=self.args, llm=self.llm)
        elif self.args.project_type == "py":
            pp = PyProject(args=self.args, llm=self.llm)
        else:
            pp = SuffixProject(args=self.args, llm=self.llm, file_filter=None)
        pp.run()
        sources = pp.sources

        index_manager = IndexManager(llm=self.llm, sources=sources, args=self.args)
        s = index_manager.read_index_as_str()
        index_data = json.loads(s)

        final_result = []
        for k in index_data.values():
            value = {}
            value["file_name"] = k["module_name"]
            value["symbols"] = k["symbols"]
            final_result.append(value)
        return json.dumps(final_result, ensure_ascii=False)

    def read_files(self, paths: str) -> str:
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
                            path = os.path.join(root, file)
                            break

            with open(path, "r",encoding="utf-8") as f:
                source_code = f.read()
                sc = SourceCode(module_name=path, source_code=source_code)
                source_code_str += f"##File: {sc.module_name}\n"
                source_code_str += f"{sc.source_code}\n\n"

        return source_code_str

    def find_files_by_name(self, keyword: str) -> str:
        """
        根据关键字在项目中搜索文件名。
        输入参数 keyword: 要搜索的关键字
        返回值是文件名包含该关键字的文件路径列表，以逗号分隔。

        该工具会搜索文件名，返回所有匹配的文件。
        搜索不区分大小写。
        """
        matched_files = []
        for root, _, files in os.walk(self.args.source_dir):
            for file in files:
                if keyword.lower() in file.lower():
                    matched_files.append(os.path.join(root, file))

        return ",".join(matched_files)

    def find_files_by_content(self, keyword: str) -> str:
        """
        根据关键字在项目中搜索文件内容。
        输入参数 keyword: 要搜索的关键字
        返回值是内容包含该关键字的文件路径列表，以逗号分隔。

        该工具会搜索文件内容，返回所有匹配的文件。
        如果结果过多，只返回前10个匹配项。
        搜索不区分大小写。
        """
        matched_files = []
        for root, _, files in os.walk(args.source_dir):
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        if keyword.lower() in content.lower():
                            matched_files.append(file_path)
                except Exception:
                    # Skip files that can't be read
                    pass

        return ",".join(matched_files)