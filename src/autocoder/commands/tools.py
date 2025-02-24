from typing import Optional
from autocoder.common.result_manager import ResultManager
from autocoder.index.index import IndexManager
from autocoder.pyproject import PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.common.interpreter import Interpreter
from autocoder.common import ExecuteSteps, ExecuteStep, detect_env
from autocoder.common import code_auto_execute
from typing import List, Tuple
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
from autocoder.common import files as files_utils
from autocoder.common.printer import Printer
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style


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
    def __init__(self, args: AutoCoderArgs, 
                 llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        self.args = args
        self.llm = llm
        self.result_manager = ResultManager()
        self.printer = Printer()

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

        session = PromptSession( message=self.printer.get_message_from_key('tool_ask_user'))
        try:
            answer = session.prompt()
        except KeyboardInterrupt:
            answer = ""        

        self.result_manager.append(content=answer, meta = {
            "action": "ask_user",
            "input": {
                "question": question
            }
        })

        return answer
    
    def response_user(self, response: str):
        console = Console()
        answer_text = Text(response, style="italic")
        answer_panel = Panel(
            answer_text,
            title="",
            border_style="green",
            expand=False
        )
        console.print(answer_panel)

        self.result_manager.append(content=response, meta = {
            "action": "response_user",
            "input": {
                "response": response
            }
        })

        return response
        

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
        
        self.result_manager.append(content=s, meta = {
            "action": "run_python_code",
            "input": {
                "code": code
            }
        })

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
        
        self.result_manager.append(content=s, meta = {
            "action": "run_shell_code",
            "input": {
                "script": script
            }
        })

        return s
   
    def get_related_files_by_symbols(self, query: str) -> str:
        """
        你可以给出类名，函数名，以及文件的用途描述等信息，该工具会根据这些信息返回项目中相关的文件。
        """
        v = self.get_project_related_files(query)
        self.result_manager.append(content=v, meta = {
            "action": "get_related_files_by_symbols",
            "input": {
                "query": query
            }
        })
        return v

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
        v =  ",".join([file.file_path for file in file_list])
        self.result_manager.append(content=v, meta = {
            "action": "get_project_related_files",
            "input": {
                "query": query
            }
        })
        return v
    
    def get_project_map(self, file_path: Optional[str] = None) -> str:
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
            value["file_tokens"] = k.get("input_tokens_count", -1)
            value["index_tokens"] = k.get("generated_tokens_count", -1)
            value["file_tokens_cost"] = k.get("input_tokens_cost", -1)
            value["index_tokens_cost"] = k.get("generated_tokens_cost", -1)
            if file_path and file_path in k["module_name"]:
                final_result.append(value)
        v = json.dumps(final_result, ensure_ascii=False)
        self.result_manager.add_result(content=v, meta = {
            "action": "get_project_map",
            "input": {                
            }
        })
        return v
    
    def read_file_with_keyword_ranges(self, file_path: str, keyword:str, before_size:int = 100, after_size:int = 100) -> str:
        """
        该函数用于读取包含了关键字(keyword)的行，以及该行前后指定大小的行。
        输入参数:
        - file_path: 文件路径
        - keyword: 关键字
        - before_size: 关键字所在行之前的行数
        - after_size: 关键字所在行之后的行数
        
        返回值:
        - 返回str类型，返回包含关键字的行，以及该行前后指定大小的行。

        返回值的格式如下：
        ```
        ##File: /path/to/file.py
        ##Line: 10-20
        
        内容
        ```
        """
        absolute_path = file_path
        if not os.path.isabs(file_path):
            # Find the first matching absolute path by traversing args.source_dir
            for root, _, files in os.walk(self.args.source_dir):
                for file in files:
                    if file_path in os.path.join(root, file):
                        absolute_path = os.path.join(root, file)
                        break

        result = []
        try:
            
            lines = files_utils.read_lines(absolute_path)            
            # Find all lines containing the keyword
            keyword_lines = []
            for i, line in enumerate(lines):
                if keyword.lower() in line.lower():
                    keyword_lines.append(i)
            
            # Process each keyword line and its surrounding range
            processed_ranges = set()
            for line_num in keyword_lines:
                # Calculate range boundaries
                start = max(0, line_num - before_size)
                end = min(len(lines), line_num + after_size + 1)
                
                # Check if this range overlaps with any previously processed range
                range_key = (start, end)
                if range_key in processed_ranges:
                    continue
                
                processed_ranges.add(range_key)
                
                # Format the content block
                content = f"##File: {absolute_path}\n"
                content += f"##Line: {start+1}-{end}\n\n"
                content += "".join(lines[start:end])
                result.append(content)
                
        except Exception as e:
            v = f"Error reading file {absolute_path}: {str(e)}"
            self.result_manager.add_result(content=v, meta={
                "action": "read_file_with_keyword_ranges",
                "input": {
                    "file_path": file_path,
                    "keyword": keyword,
                    "before_size": before_size,
                    "after_size": after_size
                }
            })
            return v
        
        final_result = "\n\n".join(result)
        self.result_manager.add_result(content=final_result, meta={
            "action": "read_file_with_keyword_ranges",
            "input": {
                "file_path": file_path,
                "keyword": keyword,
                "before_size": before_size,
                "after_size": after_size
            }
        })
        
        return final_result

    def read_files(self, paths: str, line_ranges: Optional[str] = None) -> str:
        """
        该工具用于读取指定文件的内容。

        参数说明:
        1. paths (str): 
           - 以逗号分隔的文件路径列表
           - 支持两种格式:
             a) 文件名: 如果多个文件匹配该名称，将选择第一个匹配项
             b) 绝对路径: 直接指定文件的完整路径
           - 示例: "main.py,utils.py" 或 "/path/to/main.py,/path/to/utils.py"
           - 建议: 每次调用最多指定5-6个最相关的文件，以避免返回内容过多

        2. line_ranges (Optional[str]):
           - 可选参数，用于指定每个文件要读取的具体行范围
           - 格式说明:
             * 使用逗号分隔不同文件的行范围
             * 每个文件可以指定多个行范围，用/分隔
             * 每个行范围使用-连接起始行和结束行
           - 示例: 
             * "1-100,2-50" (为两个文件分别指定一个行范围)
             * "1-100/200-300,50-100" (第一个文件指定两个行范围，第二个文件指定一个行范围)
           - 注意: line_ranges中的文件数量必须与paths中的文件数量一致

        返回值:
        - 返回str类型，包含所有请求文件的内容
        - 每个文件内容前会标注文件路径和行范围信息（如果指定了行范围）
        """
        paths = [p.strip() for p in paths.split(",")]
        source_code_str = ""
        
        # Parse line ranges if provided
        file_line_ranges = {}
        if line_ranges:
            ranges_per_file = line_ranges.split(",")
            if len(ranges_per_file) != len(paths):
                self.result_manager.add_result(content="Number of line ranges must match number of files", meta = {
                    "action": "read_files",
                    "input": {
                        "paths": paths,
                        "line_ranges": line_ranges
                    }
                })
                raise ValueError("Number of line ranges must match number of files")
            
            for path, ranges in zip(paths, ranges_per_file):
                file_line_ranges[path] = []
                for range_str in ranges.split("/"):
                    if not range_str:
                        continue
                    start, end = map(int, range_str.split("-"))
                    file_line_ranges[path].append((start, end))

        for path in paths:
            absolute_path = path
            if not os.path.isabs(path):
                # Find the first matching absolute path by traversing args.source_dir
                for root, _, files in os.walk(self.args.source_dir):
                    for file in files:
                        if path in os.path.join(root, file):
                            absolute_path = os.path.join(root, file)
                            break
            
            if path in file_line_ranges:
                # Read specific line ranges
                lines = files_utils.read_lines(absolute_path)
                filtered_lines = []
                for start, end in file_line_ranges[path]:
                    # Adjust for 0-based indexing
                    start = max(0, start - 1)
                    end = min(len(lines), end)
                    content = "".join(lines[start:end])
                    filtered_lines.extend(f"##File: {absolute_path}\n##Line: {start}-{end}\n\n{content}")
                source_code = "".join(filtered_lines)
            else:
                # Read entire file if no range specified
                content = files_utils.read_file(absolute_path)
                source_code = f"##File: {absolute_path}\n\n{content}"
                
                sc = SourceCode(module_name=absolute_path, source_code=source_code)
                source_code_str += f"{sc.source_code}\n\n"
        
        self.result_manager.add_result(content=source_code_str, meta = {
            "action": "read_files",
            "input": {
                "paths": paths,
                "line_ranges": line_ranges
            }
        })
        return source_code_str

    def get_project_structure(self) -> str:        
        if self.args.project_type == "ts":
            pp = TSProject(args=self.args, llm=self.llm)
        elif self.args.project_type == "py":
            pp = PyProject(args=self.args, llm=self.llm)
        else:
            pp = SuffixProject(args=self.args, llm=self.llm, file_filter=None)
        pp.run()
        s = pp.get_tree_like_directory_structure()
        self.result_manager.add_result(content=s, meta = {
            "action": "get_project_structure",
            "input": {
            }
        })
        return s


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

        v = ",".join(matched_files)
        self.result_manager.add_result(content=v, meta = {
            "action": "find_files_by_name",
            "input": {
                "keyword": keyword
            }
        })
        return v

    def find_files_by_content(self, keyword: str) -> str:
        """
        根据关键字在项目中搜索文件内容。
        输入参数 keyword: 要搜索的关键字
        返回值是内容包含该关键字的文件路径列表，以逗号分隔。

        该工具会搜索文件内容，返回所有匹配的文件。
        如果结果过多，只返回前10个匹配项。
        搜索不区分大小写。

        默认排除以下目录：['node_modules', '.git', '.venv', 'venv', '__pycache__', 'dist', 'build']
        """
        # 需要排除的目录和文件模式
        excluded_dirs = [
            'node_modules', '.git', '.venv', 'venv', '__pycache__', 'dist', 'build',
            '.DS_Store', '.idea', '.vscode', 'tmp', 'temp', 'cache', 'coverage',
            'htmlcov', '.mypy_cache', '.pytest_cache', '.hypothesis'
        ]
        excluded_file_patterns = [
            '*.pyc', '*.pyo', '*.pyd', '*.egg-info', '*.log'
        ]
        
        matched_files = []
        
        for root, dirs, files in os.walk(self.args.source_dir):
            # 移除需要排除的目录
            dirs[:] = [d for d in dirs if d not in excluded_dirs]
            
            # 过滤掉需要排除的文件
            files[:] = [f for f in files if not any(
                f.endswith(pattern[1:]) for pattern in excluded_file_patterns
            )]
            
            for file in files:
                file_path = os.path.join(root, file)
                try:
                    content = files_utils.read_file(file_path)
                    if keyword.lower() in content.lower():
                        matched_files.append(file_path)
                        # Limit to first 10 matches
                        if len(matched_files) >= 10:
                            break
                except Exception:
                    # Skip files that can't be read
                    pass
            if len(matched_files) >= 10:
                break

        v = ",".join(matched_files[:10])
        self.result_manager.add_result(content=v, meta = {
            "action": "find_files_by_content",
            "input": {
                "keyword": keyword
            }
        })
        return v