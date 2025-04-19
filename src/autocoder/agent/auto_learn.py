from typing import Generator, List, Dict, Union, Tuple, Optional
import os
import byzerllm
import pydantic
from rich.console import Console
from autocoder.common.printer import Printer
from autocoder.common import AutoCoderArgs
from autocoder.common.utils_code_auto_generate import stream_chat_with_continue

class AutoLearn:
    def __init__(self, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM],
                 args: AutoCoderArgs,
                 console: Optional[Console] = None):
        """
        初始化 AutoLearn

        Args:
            llm: ByzerLLM 实例，用于代码分析和学习
            args: AutoCoderArgs 实例，包含配置信息
            console: Rich Console 实例，用于输出
        """
        self.llm = llm
        self.args = args
        self.console = console or Console()
        self.printer = Printer()

    @byzerllm.prompt()
    def analyze_modules(self, module_paths: List[str], module_contents: Dict[str, str], query: str) -> str:
        """
        你作为一名高级 Python 工程师，对以下模块进行分析，总结出其中具有通用价值、可在其他场景下复用的功能点，并给出每个功能点的典型用法示例（代码片段）。每个示例需包含必要的 import、初始化、参数说明及调用方式，便于他人在不同项目中快速上手复用。

        分析目标模块路径：
        {% for path in module_paths %}
        - {{ path }}
        {% endfor %}

        下面是这些模块的内容：
        {% for path, content in module_contents.items() %}
        ## File: {{ path }}
        ```python
        {{ content }}
        ```
        {% endfor %}

        用户的具体要求是：
        {{ query }}

        请按照如下格式输出：

        功能点名称（例如：自动 Commit Review）
        简要说明：<该功能点的作用、适用场景>
        典型用法：
        ```python
        # 代码片段，包含 import、初始化、参数说明和调用方法
        ```

        依赖说明：<如有特殊依赖或初始化要求，需说明>
        请覆盖所有具有独立复用价值的功能点，避免遗漏。输出内容务必简明、准确、易于迁移和复用。
        """
        pass

    def read_file_content(self, file_path: str) -> Optional[str]:
        """读取文件内容"""
        try:
            # Ensure the path is absolute or relative to the source directory if needed
            if not os.path.isabs(file_path) and self.args.source_dir:
                 abs_path = os.path.join(self.args.source_dir, file_path)
            else:
                 abs_path = file_path

            if not os.path.exists(abs_path):
                self.printer.print_in_terminal(f"文件不存在: {abs_path}", style="red")
                return None
            with open(abs_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            self.printer.print_in_terminal(f"读取文件时出错 {file_path}: {e}", style="red")
            return None

    def analyze(self, module_paths: List[str], query: str, conversations: List[Dict] = []) -> Optional[Generator[str, None, None]]:
        """
        分析给定的模块文件，根据用户需求生成可复用功能点的总结。

        Args:
            module_paths: 需要分析的模块文件路径列表。
            query: 用户的具体分析要求。
            conversations: 之前的对话历史 (可选)。

        Returns:
            Optional[Generator]: LLM 返回的分析结果生成器，如果出错则返回 None。
        """
        module_contents = {}
        valid_module_paths = []
        for path in module_paths:
            content = self.read_file_content(path)
            if content is not None:
                module_contents[path] = content
                valid_module_paths.append(path)
            else:
                self.printer.print_in_terminal(f"跳过无法读取的文件: {path}", style="yellow")

        if not module_contents:
            self.printer.print_in_terminal("没有提供有效的模块文件进行分析。", style="red")
            return None

        try:
            # 准备 Prompt
            prompt_content = self.analyze_modules.prompt(
                module_paths=valid_module_paths,
                module_contents=module_contents,
                query=query
            )

            # 准备对话历史
            # 如果提供了 conversations，我们假设最后一个是用户的原始查询，替换它
            if conversations:
                new_conversations = conversations[:-1]
            else:
                new_conversations = []
            new_conversations.append({"role": "user", "content": prompt_content})

            # 调用 LLM
            v = stream_chat_with_continue(
                llm=self.llm,
                conversations=new_conversations,
                llm_config={},
                args=self.args
            )
            return v
        except Exception as e:
            self.printer.print_in_terminal("代码分析时出错", style="red", error=str(e))
            return None

```