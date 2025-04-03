from collections import defaultdict
import os
import re
from dataclasses import dataclass
from typing import List, Pattern, Dict, Any, Set, Union
from concurrent.futures import ThreadPoolExecutor
import byzerllm
from pydantic import BaseModel
from rich.tree import Tree
from rich.console import Console
from loguru import logger
from autocoder.pyproject import PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs

@dataclass
class AnalysisConfig:
    exclude_dirs: List[str] = None
    exclude_file_patterns: List[Pattern] = None
    exclude_extensions: List[str] = None
    max_depth: int = -1
    show_hidden: bool = False
    parallel_processing: bool = True

class ExtentionResult(BaseModel):
    code: List[str] = []
    config: List[str] = []
    data: List[str] = []
    document: List[str] = []
    other: List[str] = []

class EnhancedFileAnalyzer:
    DEFAULT_EXCLUDE_DIRS = [".git", "node_modules", "__pycache__", "venv"]
    DEFAULT_EXCLUDE_EXTS = [".log", ".tmp", ".bak", ".swp"]

    def __init__(self, args: AutoCoderArgs, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM], config: AnalysisConfig = None,):
        self.directory = os.path.abspath(args.source_dir)
        self.config = config or self.default_config()
        self.llm = llm
        self.console = Console()
        self.file_filter = EnhancedFileFilter(self.config)

    @classmethod
    def default_config(cls) -> AnalysisConfig:
        return AnalysisConfig(
            exclude_dirs=cls.DEFAULT_EXCLUDE_DIRS,
            exclude_file_patterns=[re.compile(r'~$')],  # 默认排除临时文件
            exclude_extensions=cls.DEFAULT_EXCLUDE_EXTS
        )

    def analyze(self) -> Dict[str, Any]:
        """执行完整分析流程"""
        return {
            "structure": self.get_tree_structure(),
            "extensions": self.analyze_extensions(),
            "stats": self.get_directory_stats()
        }

    def get_tree_structure(self) -> Dict:
        """获取优化的树形结构"""
        tree = {}
        if self.config.parallel_processing:
            return self._parallel_tree_build()
        return self._sequential_tree_build()

    def _sequential_tree_build(self) -> Dict:
        """单线程构建目录树"""
        tree = {}
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if not self.file_filter.should_ignore(d, True)]
            relative_path = os.path.relpath(root, self.directory)
            current = tree
            for part in relative_path.split(os.sep):
                current = current.setdefault(part, {})
            current.update({f: None for f in files if not self.file_filter.should_ignore(f, False)})
        return tree

    def _parallel_tree_build(self) -> Dict:
        """并行构建目录树"""        
        from concurrent.futures import ThreadPoolExecutor, as_completed
        import threading

        tree = {}
        tree_lock = threading.Lock()

        def process_directory(root: str, dirs: List[str], files: List[str]) -> Dict:
            local_tree = {}
            relative_path = os.path.relpath(root, self.directory)
            current = local_tree
            for part in relative_path.split(os.sep):
                current = current.setdefault(part, {})
            current.update({f: None for f in files if not self.file_filter.should_ignore(f, False)})
            return local_tree

        with ThreadPoolExecutor() as executor:
            futures = []
            for root, dirs, files in os.walk(self.directory):
                dirs[:] = [d for d in dirs if not self.file_filter.should_ignore(d, True)]
                futures.append(executor.submit(process_directory, root, dirs, files))

            for future in as_completed(futures):
                try:
                    local_tree = future.result()
                    with tree_lock:
                        self._merge_trees(tree, local_tree)
                except Exception as e:
                    logger.error(f"Error processing directory: {e}")

        return tree

    def _merge_trees(self, base_tree: Dict, new_tree: Dict) -> None:
        """递归合并两个目录树"""
        for key, value in new_tree.items():
            if key in base_tree:
                if isinstance(value, dict) and isinstance(base_tree[key], dict):
                    self._merge_trees(base_tree[key], value)
            else:
                base_tree[key] = value

    def analyze_extensions(self) -> Dict:
        """增强版后缀分析"""
        from collections import defaultdict
        extensions = self._collect_extensions()
        if self.llm:
            return self._llm_enhanced_analysis.with_llm(self.llm).run(extensions)
        return self._basic_analysis(extensions)

    def _collect_extensions(self) -> Set[str]:
        """带过滤的文件后缀收集，支持软链接目录和文件"""
        extensions = set()
        for root, dirs, files in os.walk(self.directory, followlinks=True):
            dirs[:] = [d for d in dirs if not self.file_filter.should_ignore(d, True)]
            for file in files:
                if self.file_filter.should_ignore(file, False):
                    continue
                ext = os.path.splitext(file)[1].lower()
                if ext:  # 排除无后缀文件
                    extensions.add(ext)
        return extensions

    @byzerllm.prompt()
    def _llm_enhanced_analysis(self, extensions: List[str]) -> Dict:
        """LLM增强分析"""
        '''
        请根据以下文件后缀列表，按照以下规则进行分类：

        1. 代码文件：包含可编译代码、有语法结构的文件
        2. 配置文件：包含参数设置、环境配置的文件
        3. 数据文件：包含结构化或非结构化数据的文件
        4. 文档文件：包含文档、说明、笔记的文件
        5. 其他文件：无法明确分类的文件

        文件后缀列表：
        {{ extensions | join(', ') }}

        请返回如下JSON格式：
        {
            "code": ["后缀1", "后缀2"],
            "config": ["后缀3", "后缀4"],
            "data": ["后缀5", "后缀6"],
            "document": ["后缀7", "后缀8"],
            "other": ["后缀9", "后缀10"]
        }
        '''
        return {
            "extensions": extensions
        }

    def _basic_analysis(self, extensions: Set[str]) -> Dict:
        """基于规则的基础分析"""
        CODE_EXTS = {
            # 通用脚本语言
            '.py',  # Python
            '.js', '.jsx', '.ts', '.tsx',  # JavaScript/TypeScript
            '.rb', '.erb',  # Ruby
            '.php',  # PHP
            '.pl', '.pm',  # Perl
            
            # 编译型语言
            '.java', '.kt', '.groovy',  # JVM系
            '.c', '.cpp', '.cc', '.cxx', '.h', '.hpp',  # C/C++
            '.cs',  # C#
            '.go',  # Go
            '.rs',  # Rust
            '.swift',  # Swift
            
            # Web开发
            '.vue', '.svelte',  # 前端框架
            '.html', '.htm',  # HTML
            '.css', '.scss', '.sass', '.less',  # 样式表
            
            # 其他语言
            '.scala',  # Scala
            '.clj',  # Clojure
            '.coffee',  # CoffeeScript
            '.lua',  # Lua
            '.r',  # R
            '.sh', '.bash',  # Shell脚本
            '.sql',  # SQL
            '.dart',  # Dart
            '.ex', '.exs',  # Elixir
            '.fs', '.fsx',  # F#
            '.hs',  # Haskell
            '.ml', '.mli'  # OCaml
        }
        CONFIG_EXTS = {'.yml', '.yaml', '.json', '.toml', '.ini'}

        return {
            "code": [ext for ext in extensions if ext in CODE_EXTS],
            "config": [ext for ext in extensions if ext in CONFIG_EXTS],
            "unknown": [ext for ext in extensions if ext not in CODE_EXTS | CONFIG_EXTS]
        }

    def get_directory_stats(self) -> Dict:
        """获取目录统计信息"""
        stats = {
            'total_files': 0,
            'total_dirs': 0,
            'by_extension': defaultdict(int),
            'file_types': {
                'code': 0,
                'config': 0,
                'data': 0,
                'document': 0,
                'other': 0
            }
        }
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if not self.file_filter.should_ignore(d, True)]
            stats['total_dirs'] += len(dirs)
            for file in files:
                if self.file_filter.should_ignore(file, False):
                    continue
                stats['total_files'] += 1
                ext = os.path.splitext(file)[1].lower()
                stats['by_extension'][ext] += 1

                # 根据扩展名分类
                if ext in ['.py', '.js', '.ts', '.java', '.c', '.cpp']:
                    stats['file_types']['code'] += 1
                elif ext in ['.yml', '.yaml', '.json', '.toml', '.ini']:
                    stats['file_types']['config'] += 1
                else:
                    stats['file_types']['other'] += 1
        return stats

    def interactive_display(self):
        """交互式可视化展示"""
        tree = self.build_interactive_tree(self.directory, self.config)
        self.console.print(tree)
        self.console.print("\n[bold]Statistical Summary:[/]")
        stats = self.get_directory_stats()

        from rich.table import Table
        table = Table(title="Directory Statistics", show_header=True, header_style="bold magenta")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Total Files", str(stats['total_files']))
        table.add_row("Total Directories", str(stats['total_dirs']))
        table.add_row("Code Files", str(stats['file_types']['code']))
        table.add_row("Config Files", str(stats['file_types']['config']))
        self.console.print(table)

class EnhancedFileFilter:
    """增强版文件过滤器"""
    def __init__(self, config: AnalysisConfig):
        self.config = config

    def should_ignore(self, path: str, is_dir: bool) -> bool:
        """综合判断是否应忽略路径"""
        base_name = os.path.basename(path)

        # 隐藏文件处理
        if not self.config.show_hidden and base_name.startswith('.'):
            return True

        # 目录排除
        if is_dir and base_name in self.config.exclude_dirs:
            return True

        # 文件扩展名排除
        if not is_dir:
            ext = os.path.splitext(path)[1].lower()
            if ext in self.config.exclude_extensions:
                return True

        # 正则匹配排除
        full_path = os.path.abspath(path)
        for pattern in self.config.exclude_file_patterns:
            if pattern.search(full_path):
                return True

        return False

def get_project_structure(args:AutoCoderArgs, llm:Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
    if args.project_type == "ts":
        pp = TSProject(args=args, llm=llm)
    elif args.project_type == "py":
        pp = PyProject(args=args, llm=llm)
    else:
        pp = SuffixProject(args=args, llm=llm, file_filter=None)
    return pp.get_tree_like_directory_structure()
