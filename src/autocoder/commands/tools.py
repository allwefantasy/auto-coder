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
from typing import List, Tuple,Dict
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
from autocoder.rag.token_counter import count_tokens
from autocoder.index.symbols_utils import (
    extract_symbols,
    SymbolType,
    symbols_info_to_str,
)
from autocoder.run_context import get_run_context
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events import event_content as EventContentCreator
from autocoder.linters.linter_factory import LinterFactory, lint_file, lint_project, format_lint_result
import traceback
from autocoder.common.mcp_server import get_mcp_server
from autocoder.common.mcp_server_types import (
    McpRequest, McpInstallRequest, McpRemoveRequest, McpListRequest, 
    McpListRunningRequest, McpRefreshRequest
)

from autocoder.common.ignorefiles.ignore_file_utils import should_ignore


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

    def execute_mcp_server(self, query: str) -> str:
        mcp_server = get_mcp_server()
        response = mcp_server.send_request(
            McpRequest(
                query=query,
                model=self.args.inference_model or self.args.model,
                product_mode=self.args.product_mode
            )
        )

        result = response.result

        self.result_manager.append(content=result, meta={
            "action": "execute_mcp_server",
            "input": {
                "query": query
            }
        })
        return result

    def ask_user(self, question: str) -> str:
        '''
        如果你对用户的问题有什么疑问，或者你想从用户收集一些额外信息，可以调用此方法。
        输入参数 question 是你对用户的提问。
        返回值是 用户对你问题的回答。

        注意，尽量不要询问用户，除非你感受到你无法回答用户的问题。
        '''

        # 如果是在web模式下，则使用event_manager事件来询问用户
        if get_run_context().is_web():
            answer = get_event_manager(
                self.args.event_file).ask_user(prompt=question)
            self.result_manager.append(content=answer, meta={
                "action": "ask_user",
                "input": {
                    "question": question
                }
            })
            return answer

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

        session = PromptSession(
            message=self.printer.get_message_from_key('tool_ask_user'))
        try:
            answer = session.prompt()
        except KeyboardInterrupt:
            answer = ""

        self.result_manager.append(content=answer, meta={
            "action": "ask_user",
            "input": {
                "question": question
            }
        })

        return answer

    def response_user(self, response: Union[str, Dict]):
        # 如果是在web模式下，则使用event_manager事件来询问用户
        if isinstance(response, dict):
            response = json.dumps(response, ensure_ascii=False,indent=4)

        if get_run_context().is_web():
            try:
                get_event_manager(
                    self.args.event_file).write_result(
                    EventContentCreator.create_result(
                        EventContentCreator.ResultSummaryContent(
                            summary=response
                        )
                    )
                )
                self.result_manager.append(content=response, meta={
                    "action": "response_user",
                    "input": {
                        "response": response
                    }
                })
            except Exception as e:
                error_message = f"Error: {str(e)}\n\n完整异常堆栈信息:\n{traceback.format_exc()}"
                self.result_manager.append(content=f"Error: {error_message}", meta={
                    "action": "response_user",
                    "input": {
                        "response": response
                    }
                })
            return response

        console = Console()
        answer_text = Text(response, style="italic")
        answer_panel = Panel(
            answer_text,
            title="",
            border_style="green",
            expand=False
        )
        console.print(answer_panel)

        self.result_manager.append(content=response, meta={
            "action": "response_user",
            "input": {
                "response": response
            }
        })

        return response
    
    def output_result(self, response: Union[str, Dict]):
        # 如果是在web模式下，则使用event_manager事件来询问用户
        if isinstance(response, dict):
            response = json.dumps(response, ensure_ascii=False,indent=4)

        if get_run_context().is_web():
            try:
                get_event_manager(
                    self.args.event_file).write_result(
                    EventContentCreator.create_result(
                        EventContentCreator.MarkdownContent(
                            content=response
                        )
                    )
                )
                self.result_manager.append(content=response, meta={
                    "action": "output_result",
                    "input": {
                        "response": response
                    }
                })
            except Exception as e:
                error_message = f"Error: {str(e)}\n\n完整异常堆栈信息:\n{traceback.format_exc()}"
                self.result_manager.append(content=f"Error: {error_message}", meta={
                    "action": "output_result",
                    "input": {
                        "response": response
                    }
                })
            return response

        console = Console()
        answer_text = Text(response, style="italic")
        answer_panel = Panel(
            answer_text,
            title="",
            border_style="green",
            expand=False
        )
        console.print(answer_panel)

        self.result_manager.append(content=response, meta={
            "action": "output_result",
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

        self.result_manager.append(content=s, meta={
            "action": "run_python",
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

        self.result_manager.append(content=s, meta={
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
        self.result_manager.append(content=v, meta={
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

        index_manager = IndexManager(
            llm=self.llm, sources=sources, args=self.args)
        target_files = index_manager.get_target_files_by_query(query)
        file_list = target_files.file_list
        v = ",".join([file.file_path for file in file_list])
        self.result_manager.append(content=v, meta={
            "action": "get_project_related_files",
            "input": {
                "query": query
            }
        })
        return v

    def _get_sources(self):
        if self.args.project_type == "ts":
            pp = TSProject(args=self.args, llm=self.llm)
        elif self.args.project_type == "py":
            pp = PyProject(args=self.args, llm=self.llm)
        else:
            pp = SuffixProject(args=self.args, llm=self.llm, file_filter=None)
        pp.run()
        return pp.sources

    def _get_index(self):
        sources = self._get_sources()
        index_manager = IndexManager(
            llm=self.llm, sources=sources, args=self.args)
        return index_manager

    def get_project_map(self, file_paths: Optional[str] = None) -> str:
        """
        该工具会返回项目中所有已经被构建索引的文件以及该文件的信息，诸如该文件的用途，导入的包，定义的类，函数，变量等信息。
        返回的是json格式文本。

        参数说明:
        file_paths (Optional[str]): 可选参数，以逗号分隔的文件路径列表，用于筛选特定文件。
                                  例如："main.py,utils.py"或"/path/to/main.py,/path/to/utils.py"

        注意，这个工具无法返回所有文件的信息，因为有些文件可能没有被索引。
        尽量避免使用该工具。
        """
        try:
            index_manager = self._get_index()
            s = index_manager.read_index_as_str()
            index_data = json.loads(s)
        except Exception as e:
            v = f"Error: {str(e)}\n\n完整异常堆栈信息:\n{traceback.format_exc()}"
            self.result_manager.add_result(content=v, meta={
                "action": "get_project_map",
                "input": {
                    "file_paths": file_paths
                }
            })
            return v

        final_result = []

        # 解析文件路径列表（如果提供了）
        file_path_list = []
        if file_paths:
            # 处理可能是列表或字符串的file_paths
            if isinstance(file_paths, list):
                file_path_list = file_paths
            elif isinstance(file_paths, str):
                file_path_list = [path.strip() for path in file_paths.split(",")]
            else:
                file_path_list = [str(file_paths)]

        for k in index_data.values():
            value = {}
            value["file_name"] = k["module_name"]
            value["symbols"] = k["symbols"]
            value["file_tokens"] = k.get("input_tokens_count", -1)
            value["index_tokens"] = k.get("generated_tokens_count", -1)
            value["file_tokens_cost"] = k.get("input_tokens_cost", -1)
            value["index_tokens_cost"] = k.get("generated_tokens_cost", -1)

            # 如果提供了文件路径列表，检查当前文件是否匹配任何一个路径
            if file_path_list:
                if any(path in k["module_name"] for path in file_path_list):
                    final_result.append(value)
            else:
                final_result.append(value)

        v = json.dumps(final_result, ensure_ascii=False)
        tokens = count_tokens(v)
        if tokens > self.args.conversation_prune_safe_zone_tokens/2.0:
            result = f"The project map is too large to return. (tokens: {tokens}). Try to use another function."
            self.result_manager.add_result(content=result, meta={
                "action": "get_project_map",
                "input": {
                    "file_paths": file_paths
                }
            })
            return result

        self.result_manager.add_result(content=v, meta={
            "action": "get_project_map",
            "input": {
                "file_paths": file_paths
            }
        })
        return v

    def read_file_with_keyword_ranges(self, file_path: str, keyword: str, before_size: int = 100, after_size: int = 100) -> str:
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
                self.result_manager.add_result(content="Number of line ranges must match number of files", meta={
                    "action": "read_files",
                    "input": {
                        "paths": paths,
                        "line_ranges": line_ranges
                    }
                })
                raise ValueError(
                    "Number of line ranges must match number of files")

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
                    filtered_lines.extend(
                        f"##File: {absolute_path}\n##Line: {start}-{end}\n\n{content}")
                source_code = "".join(filtered_lines)
                # Add source_code to source_code_str
                source_code_str += source_code
            else:
                # Read entire file if no range specified
                content = files_utils.read_file(absolute_path)
                source_code = f"##File: {absolute_path}\n\n{content}"

                sc = SourceCode(module_name=absolute_path,
                                source_code=source_code)
                source_code_str += f"{sc.source_code}\n\n"

        self.result_manager.add_result(content=source_code_str, meta={
            "action": "read_files",
            "input": {
                "paths": paths,
                "line_ranges": line_ranges
            }
        })
        return source_code_str

    def find_symbol_definition(self, symbol: str) -> str:
        """
        该工具用于查找指定符号的定义。
        输入参数 symbol: 要查找的符号
        返回值是符号的定义所在的文件路径列表，以逗号分隔。
        """
        index_manager = self._get_index()
        result = []
        index_items = index_manager.read_index()

        for item in index_items:
            symbols = extract_symbols(item.symbols)
            for symbol_info in symbols:
                # 进行精确匹配和模糊匹配
                if (symbol_info.name == symbol or
                        symbol.lower() in symbol_info.name.lower()):
                    # 检查是否已经添加过该文件路径
                    if symbol_info.module_name not in result:
                        result.append(symbol_info.module_name)

        # 生成以逗号分隔的文件路径列表
        file_paths = ",".join(result)

        # 如果没有找到任何匹配项，返回提示信息
        if not file_paths:
            file_paths = f"未找到符号 '{symbol}' 的定义"

        # 记录操作结果
        self.result_manager.add_result(content=file_paths, meta={
            "action": "find_symbols_definition",
            "input": {
                "symbol": symbol
            }
        })

        return file_paths

    def list_files(self, path: str) -> str:
        """
        该工具用于列出指定目录下的所有文件（不包括子目录中的文件）。
        输入参数 path: 要列出文件的目录路径
        返回值是目录下所有文件的列表，以逗号分隔。
        """        
        # 处理绝对路径和相对路径
        target_path = path
        if not os.path.isabs(path):
            # 如果是相对路径，将其转换为绝对路径
            target_path = os.path.join(self.args.source_dir, path)

        # 确保路径存在且是目录
        if not os.path.exists(target_path):
            result = f"目录不存在: {target_path}"
            self.result_manager.add_result(content=result, meta={
                "action": "list_files",
                "input": {
                    "path": path
                }
            })
            return result

        if not os.path.isdir(target_path):
            result = f"指定路径不是目录: {target_path}"
            self.result_manager.add_result(content=result, meta={
                "action": "list_files",
                "input": {
                    "path": path
                }
            })
            return result

        # 只收集当前目录下的文件，不递归子目录
        file_list = []
        for item in os.listdir(target_path):
            item_path = os.path.join(target_path, item)
            file_list.append(item_path)                

        # 生成以逗号分隔的文件列表
        result = "\n".join(file_list)

        # 记录结果
        self.result_manager.add_result(content=result, meta={
            "action": "list_files",
            "input": {
                "path": path
            }
        })

        return result

    def get_project_structure(self) -> str:
        if self.args.project_type == "ts":
            pp = TSProject(args=self.args, llm=self.llm)
        elif self.args.project_type == "py":
            pp = PyProject(args=self.args, llm=self.llm)
        else:
            pp = SuffixProject(args=self.args, llm=self.llm, file_filter=None)
        pp.run()
        s = pp.get_tree_like_directory_structure()

        tokens = count_tokens(s)
        if tokens > self.args.conversation_prune_safe_zone_tokens / 2.0:
            result = f"The project structure is too large to return. (tokens: {tokens}). Try to use another function."
            self.result_manager.add_result(content=result, meta={
                "action": "get_project_structure",
                "input": {
                }
            })
            return result

        self.result_manager.add_result(content=s, meta={
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
        for root, dirs, files in os.walk(self.args.source_dir):
            # 过滤忽略的目录，避免递归进入
            dirs[:] = [d for d in dirs if not should_ignore(os.path.join(root, d))]
            for file in files:
                file_path = os.path.join(root, file)
                if should_ignore(file_path):
                    continue
                if keyword.lower() in file.lower():
                    matched_files.append(file_path)

        v = ",".join(matched_files)
        
        tokens = count_tokens(v)
        if tokens > self.args.conversation_prune_safe_zone_tokens / 2.0:
            result = f"The result is too large to return. (tokens: {tokens}). Try to use another function or use another keyword to search."
            self.result_manager.add_result(content=result, meta={
                "action": "find_files_by_name",
                "input": {
                    "keyword": keyword
                }
            })
            return result

        self.result_manager.add_result(content=v, meta={
            "action": "find_files_by_name",
            "input": {
                "keyword": keyword
            }
        })
        return v

    def count_file_tokens(self, file_path: str) -> int:
        """
        该工具用于计算指定文件的token数量。
        输入参数 file_path: 文件路径
        返回值是文件的token数量。
        """
        content = files_utils.read_file(file_path)
        return count_tokens(content)

    def count_string_tokens(self, text: str) -> int:
        """
        该工具用于计算指定字符串的token数量。
        输入参数 text: 要计算的文本
        返回值是字符串的token数量。
        """
        return count_tokens(text)

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
            'htmlcov', '.mypy_cache', '.pytest_cache', '.hypothesis',".auto-coder"
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
        self.result_manager.add_result(content=v, meta={
            "action": "find_files_by_content",
            "input": {
                "keyword": keyword
            }
        })
        return v

    def lint_code(self, path: str, language: Optional[str] = None, fix: bool = False, verbose: bool = False) -> str:
        """
        对代码进行质量检查，支持多种编程语言。

        参数说明:
        path (str): 要检查的文件路径或项目目录
        language (str, optional): 明确指定语言类型，如'python', 'javascript', 'typescript', 'react', 'vue'等
                                如果不指定，将尝试根据文件扩展名或项目结构自动检测
        fix (bool): 是否自动修复可修复的问题，默认为False
        verbose (bool): 是否显示详细输出，默认为False

        返回值:
        格式化后的lint结果，包含错误和警告信息

        支持的语言:
        - 前端: JavaScript, TypeScript, React, Vue (使用ESLint)
        - Python: 使用pylint, flake8, black

        说明:
        - 对于前端代码，需要Node.js环境
        - 对于Python代码，需要pylint/flake8/black
        - 工具会尝试自动安装缺少的依赖
        - 如果路径是文件，则只检查该文件
        - 如果路径是目录，则检查整个项目
        - fix=True时会尝试自动修复问题
        """
        try:
            # 检查是否是目录或文件
            is_directory = os.path.isdir(path)

            # 根据路径类型执行相应的lint操作
            if is_directory:
                # 对整个项目进行lint
                result = lint_project(
                    path, language=language, fix=fix, verbose=verbose)
            else:
                # 对单个文件进行lint
                result = lint_file(path, fix=fix, verbose=verbose)

            # 格式化结果
            formatted_result = format_lint_result(result, language=language)

            # 记录操作结果
            self.result_manager.add_result(content=formatted_result, meta={
                "action": "lint_code",
                "input": {
                    "path": path,
                    "language": language,
                    "fix": fix,
                    "verbose": verbose
                },
                "result": result
            })

            return formatted_result

        except Exception as e:
            error_message = f"Linting failed: {str(e)}\n\n完整异常堆栈信息:\n{traceback.format_exc()}"

            self.result_manager.add_result(content=error_message, meta={
                "action": "lint_code",
                "input": {
                    "path": path,
                    "language": language,
                    "fix": fix,
                    "verbose": verbose
                },
                "error": error_message
            })

            return error_message
