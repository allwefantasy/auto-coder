import os
from typing import Dict, List, Set, Any, Optional, Union
import byzerllm
from loguru import logger
from rich.console import Console

class FileAnalyzer:
    def __init__(self, directory: str, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM] = None):
        self.directory = directory
        self.llm = llm
        self.default_exclude_dirs = [
            ".git",
            ".svn",
            ".hg",
            "build",
            "dist",
            "__pycache__",
            "node_modules",
            ".auto-coder",
            "actions",
            ".vscode",
            ".idea",
            "venv",
        ]
        self.console = Console()

    def get_tree_structure(self) -> Dict[str, Any]:
        """
        获取目录的树形结构，类似 tree 命令的输出
        """
        structure_dict = {}
        for root, dirs, files in os.walk(self.directory, followlinks=True):
            # 排除无用目录
            dirs[:] = [d for d in dirs if d not in self.default_exclude_dirs]

            # 构建树形结构
            relative_path = os.path.relpath(root, self.directory)
            parts = relative_path.split(os.sep)
            current_level = structure_dict
            for part in parts:
                if part not in current_level:
                    current_level[part] = {}
                current_level = current_level[part]

            # 添加文件
            for file in files:
                current_level[file] = None

        return structure_dict

    def collect_file_extensions(self) -> Set[str]:
        """
        收集目录中所有文件的后缀名
        """
        extensions = set()
        for root, dirs, files in os.walk(self.directory, followlinks=True):
            # 排除无用目录
            dirs[:] = [d for d in dirs if d not in self.default_exclude_dirs]

            for file in files:
                _, ext = os.path.splitext(file)
                if ext:
                    extensions.add(ext.lower())
        return extensions

    @byzerllm.prompt()
    def identify_code_config_extensions(self, extensions: List[str]) -> str:
        """
        根据以下文件后缀名列表，识别哪些可能是代码文件或配置文件的后缀名：

        {{ extensions }}

        请返回一个 JSON 格式的结果：
        ```json
        {
            "code_extensions": ["可能的代码文件后缀名列表"],
            "config_extensions": ["可能的配置文件后缀名列表"]
        }
        ```
        """

    def analyze_directory(self):
        """
        分析目录结构并识别代码/配置文件后缀名
        """
        # 获取目录树结构
        tree_structure = self.get_tree_structure()
        self.console.print("[bold green]Directory Structure:[/bold green]")
        self.print_tree(tree_structure)

        # 收集文件后缀名
        extensions = self.collect_file_extensions()
        self.console.print(f"\n[bold green]Found {len(extensions)} unique file extensions:[/bold green]")
        self.console.print(sorted(extensions))

        # 识别代码/配置文件后缀名
        if self.llm:
            result = self.identify_code_config_extensions.with_llm(self.llm).run(list(extensions))
            self.console.print("\n[bold green]Identified extensions:[/bold green]")
            self.console.print(result)
        else:
            logger.warning("LLM not provided, skipping extension identification")

    def print_tree(self, tree: Dict[str, Any], indent: str = ""):
        """
        打印树形结构
        """
        for key, value in tree.items():
            if value is None:
                self.console.print(f"{indent}{key}")
            else:
                self.console.print(f"{indent}{key}/")
                self.print_tree(value, indent + "    ")
