"""
用于对文件进行编译的模块。
"""

import os
from typing import Optional
from autocoder.compilers.compiler_factory import CompilerFactory
from autocoder.compilers.models import ProjectCompilationResult, FileCompilationResult

class NormalCompiler:
    """
    用于对文件进行编译的类。
    """
    
    def __init__(self, project_dir: str, verbose: bool = False):
        """
        初始化编译器。
        
        参数:
            project_dir (str): 项目根目录路径
            verbose (bool): 是否启用详细输出
        """
        self.project_dir = project_dir
        self.compiler = CompilerFactory.create_compiler(
            language="provided",
            config_path=os.path.join(self.project_dir, ".auto-coder", "projects", "compiler.yml")
        )

    def compile_file(self, file_path: str) -> FileCompilationResult:
        """
        编译单个文件。
        
        参数:
            file_path (str): 文件路径
            
        返回:
            FileCompilationResult: 编译结果
        """
        return FileCompilationResult(
            file_path=file_path,
            success=True,
            language="provided",
            errors=[],
            error_message=None,
            warning_count=0,
            error_count=0,
            info_count=0,
            execution_time_ms=0,
            output_file=None
        )  

    def compile_all_files(self, target_compiler_name: Optional[str] = None) -> ProjectCompilationResult:
        """
        编译项目中的所有文件。
        
        参数:
            target_compiler_name (Optional[str]): 目标编译器名称
            
        返回:
            ProjectCompilationResult: 项目编译结果
        """
        result = self.compiler.compile_project(self.project_dir, target_compiler_name)
        result.project_path = self.project_dir
        return result
