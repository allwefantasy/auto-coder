import os
import json
from collections import defaultdict
from typing import Dict, List, Set, Tuple
from pathlib import Path
from loguru import logger
import byzerllm
from autocoder.common import AutoCoderArgs
from autocoder.common.printer import Printer

class ProjectTypeAnalyzer:
    def __init__(self, args: AutoCoderArgs, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        self.args = args
        self.llm = llm
        self.printer = Printer()
        self.default_exclude_dirs = [
            ".git", ".svn", ".hg", "build", "dist", "__pycache__", 
            "node_modules", ".auto-coder", ".vscode", ".idea", "venv",
            ".next", ".nuxt", ".svelte-kit", "out", "cache", "logs",
            "temp", "tmp", "coverage", ".DS_Store", "public", "static"
        ]
        self.extension_counts = defaultdict(int)
        self.stats_file = Path(args.source_dir) / ".auto-coder" / "project_type_stats.json"

    def traverse_project(self) -> None:
        """遍历项目目录，统计文件后缀"""
        for root, dirs, files in os.walk(self.args.source_dir):
            # 过滤掉默认排除的目录
            dirs[:] = [d for d in dirs if d not in self.default_exclude_dirs]
            
            for file in files:
                _, ext = os.path.splitext(file)
                if ext:  # 只统计有后缀的文件
                    self.extension_counts[ext.lower()] += 1

    def count_extensions(self) -> Dict[str, int]:
        """返回文件后缀统计结果"""
        return dict(sorted(self.extension_counts.items(), key=lambda x: x[1], reverse=True))

    @byzerllm.prompt()
    def classify_extensions(self, extensions: List[str]) -> Dict[str, List[str]]:
        """
        根据文件后缀列表，将后缀分类为代码、配置、数据、文档等类型。

        文件后缀列表：
        {{ extensions }}

        请返回如下JSON格式：
        {
            "code": ["后缀1", "后缀2"],
            "config": ["后缀3", "后缀4"],
            "data": ["后缀5", "后缀6"],
            "document": ["后缀7", "后缀8"],
            "other": ["后缀9", "后缀10"],
            "framework": ["后缀11", "后缀12"]
        }
        """
        return {
            "extensions": extensions
        }

    def save_stats(self) -> None:
        """保存统计结果到文件"""
        stats = {
            "extension_counts": self.extension_counts,
            "project_type": self.detect_project_type()
        }
        
        # 确保目录存在
        self.stats_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.stats_file, "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)
        
        self.printer.print_in_terminal("stats_saved", path=str(self.stats_file))

    def load_stats(self) -> Dict[str, any]:
        """从文件加载统计结果"""
        if not self.stats_file.exists():
            self.printer.print_in_terminal("stats_not_found", path=str(self.stats_file))
            return {}
            
        with open(self.stats_file, "r", encoding="utf-8") as f:
            return json.load(f)

    def detect_project_type(self) -> str:
        """根据后缀统计结果推断项目类型"""
        # 获取统计结果
        ext_counts = self.count_extensions()
        
        # 将后缀分类
        classification = self.classify_extensions.with_llm(self.llm).run(list(ext_counts.keys()))
        
        # 根据代码文件占比判断项目类型
        code_exts = set(classification.get("code", []))
        framework_exts = set(classification.get("framework", []))
        total_files = sum(ext_counts.values())
        
        # 添加防除零保护
        if total_files == 0:
            return "unknown"
            
        code_files = sum(count for ext, count in ext_counts.items() if ext in code_exts)
        
        # 优先检测前端框架
        if ".vue" in framework_exts:
            return "vue"
        elif ".svelte" in framework_exts:
            return "svelte"
        elif ".jsx" in framework_exts or ".tsx" in framework_exts:
            return "react"
        elif ".astro" in framework_exts:
            return "astro"
            
        # 根据代码文件占比判断项目类型
        if code_files / total_files > 0.7:
            if ".py" in code_exts:
                return "py"
            elif ".ts" in code_exts or ".tsx" in code_exts:
                return "ts"
            else:
                # 如果有多个代码后缀，返回主要后缀
                main_ext = max((ext for ext in code_exts), key=lambda x: ext_counts.get(x, 0))
                return main_ext.lstrip(".")
        else:
            return "unknown"

    def analyze(self) -> Dict[str, any]:
        """执行完整的项目类型分析流程"""
        # 遍历项目目录
        self.traverse_project()
        
        # 检测项目类型
        project_type = self.detect_project_type()
        
        # 保存统计结果
        self.save_stats()
        
        return {
            "project_type": project_type,
            "extension_counts": self.count_extensions()
        }