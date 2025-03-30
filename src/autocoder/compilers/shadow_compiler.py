import os
from typing import Optional
from autocoder.shadows.shadow_manager import ShadowManager
from autocoder.compilers.compiler_factory import CompilerFactory
from autocoder.compilers.models import ProjectCompilationResult,FileCompilationResult

class ShadowCompiler:
    """
    用于对ShadowManager管理的文件进行代码检查并将结果转换回项目路径的类。
    """
    
    def __init__(self, shadow_manager: ShadowManager,verbose:bool=False):
        """
        使用ShadowManager实例初始化。
        
        参数:
            shadow_manager (ShadowManager): 用于管理文件路径映射的实例
            verbose (bool): 是否启用详细输出
        """
        self.shadow_manager = shadow_manager
        self.compiler = CompilerFactory.create_compiler(language="provided",config_path=os.path.join(self.shadow_manager.source_dir,".auto-coder","projects","compiler.yml"))

    def compile_shadow_file(self, shadow_path: str) -> FileCompilationResult:
        return FileCompilationResult(
            file_path=shadow_path,
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

    def compile_all_shadow_files(self,target_compiler_name:Optional[str]=None) -> ProjectCompilationResult:
        link_projects_dir = self.shadow_manager.create_link_project()
        result = self.compiler.compile_project(link_projects_dir,target_compiler_name)
        result.project_path = self.shadow_manager.source_dir
        return result
        
