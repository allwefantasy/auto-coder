import os
import re
from dataclasses import dataclass
from typing import List, Pattern, Dict, Any, Set, Union
from concurrent.futures import ThreadPoolExecutor
import byzerllm
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

class EnhancedFileAnalyzer:
    DEFAULT_EXCLUDE_DIRS = [".git", "node_modules", "__pycache__", "venv"]
    DEFAULT_EXCLUDE_EXTS = [".log", ".tmp", ".bak", ".swp"]

    def __init__(self, directory: str, config: AnalysisConfig = None, llm: byzerllm.ByzerLLM = None):
        self.directory = os.path.abspath(directory)
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
        # 实现略，需处理线程安全
        pass

    def analyze_extensions(self) -> Dict:
        """增强版后缀分析"""
        extensions = self._collect_extensions()
        if self.llm:
            return self._llm_enhanced_analysis(extensions)
        return self._basic_analysis(extensions)

    def _collect_extensions(self) -> Set[str]:
        """带过滤的文件后缀收集"""
        extensions = set()
        for root, dirs, files in os.walk(self.directory):
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
        # 使用优化后的提示词模板
        pass

    def _basic_analysis(self, extensions: Set[str]) -> Dict:
        """基于规则的基础分析"""
        CODE_EXTS = {'.py', '.js', '.ts', '.java', '.c', '.cpp'}
        CONFIG_EXTS = {'.yml', '.yaml', '.json', '.toml', '.ini'}

        return {
            "code": [ext for ext in extensions if ext in CODE_EXTS],
            "config": [ext for ext in extensions if ext in CONFIG_EXTS],
            "unknown": [ext for ext in extensions if ext not in CODE_EXTS | CONFIG_EXTS]
        }

    def get_directory_stats(self) -> Dict:
        """获取目录统计信息"""
        stats = {'total_files': 0, 'total_dirs': 0, 'by_extension': {}}
        for root, dirs, files in os.walk(self.directory):
            dirs[:] = [d for d in dirs if not self.file_filter.should_ignore(d, True)]
            stats['total_dirs'] += len(dirs)
            for file in files:
                if self.file_filter.should_ignore(file, False):
                    continue
                stats['total_files'] += 1
                ext = os.path.splitext(file)[1].lower()
                stats['by_extension'][ext] = stats['by_extension'].get(ext, 0) + 1
        return stats

    def interactive_display(self):
        """交互式可视化展示"""
        tree = build_interactive_tree(self.directory, self.config)
        self.console.print(tree)
        self.console.print("\n[bold]Statistical Summary:[/]")
        self.console.print(self.get_directory_stats())

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
