"""
用于表示代码编译结果的 Pydantic 模型。
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

class CompilationErrorSeverity(str, Enum):
    """编译错误严重性的枚举"""
    ERROR = "error"  # 错误
    WARNING = "warning"  # 警告
    INFO = "info"  # 信息

class CompilationErrorPosition(BaseModel):
    """文件中编译错误的位置"""
    line: int = Field(..., description="发现错误的行号（从1开始）")
    column: Optional[int] = Field(None, description="发现错误的列号（从1开始）")
    end_line: Optional[int] = Field(None, description="错误的结束行号")
    end_column: Optional[int] = Field(None, description="错误的结束列号")

    def to_str(self) -> str:
        """将位置转换为人类可读的字符串"""
        result = f"第 {self.line} 行"
        if self.column is not None:
            result += f"，第 {self.column} 列"
        if self.end_line is not None and (self.end_line != self.line or self.end_column is not None):
            result += f" 到第 {self.end_line} 行"
            if self.end_column is not None:
                result += f"，第 {self.end_column} 列"
        return result

class CompilationError(BaseModel):
    """单个编译错误的表示"""
    code: Optional[str] = Field(None, description="错误代码或标识符")
    message: str = Field(..., description="错误的人类可读描述")
    severity: CompilationErrorSeverity = Field(..., description="错误的严重性级别")
    position: CompilationErrorPosition = Field(..., description="错误在文件中的位置")
    file_path: str = Field(..., description="发现错误的文件路径")
    source: Optional[str] = Field(None, description="发现错误的源代码片段")
    
    def to_str(self, show_file_path: bool = True) -> str:
        """
        将错误转换为人类可读的字符串
        
        参数:
            show_file_path: 是否在输出中包含文件路径
            
        返回:
            错误的格式化字符串表示
        """
        parts = []
        
        if show_file_path:
            parts.append(f"{self.file_path}:{self.position.line}")
        
        parts.append(f"[{self.severity.value.upper()}] {self.message}")
        
        if self.code:
            parts.append(f"({self.code})")
            
        result = " ".join(parts)
        
        if self.source:
            # 为了更好的可读性，缩进源代码
            indented_source = "\n    ".join(self.source.splitlines())
            result += f"\n    {indented_source}"
            
        return result

class FileCompilationResult(BaseModel):
    """单个文件的编译结果"""
    file_path: str = Field(..., description="被编译的文件路径")
    success: bool = Field(True, description="编译是否成功完成")
    language: str = Field(..., description="被编译的语言/文件类型")
    errors: List[CompilationError] = Field(default_factory=list, description="发现的编译错误列表")
    error_message: Optional[str] = Field(None, description="如果编译失败，错误消息")
    warning_count: int = Field(0, description="发现的警告数量")
    error_count: int = Field(0, description="发现的错误数量")
    info_count: int = Field(0, description="发现的信息性问题数量")
    execution_time_ms: Optional[int] = Field(None, description="编译文件所花费的时间（毫秒）")
    output_file: Optional[str] = Field(None, description="编译输出的文件路径")

    def to_str(self, show_file_path_in_errors: bool = False) -> str:
        """
        将文件编译结果转换为人类可读的字符串
        
        参数:
            show_file_path_in_errors: 是否在单个错误中包含文件路径
            
        返回:
            文件编译结果的格式化字符串表示
        """
        if not self.success:
            return f"编译 {self.file_path} 时出错: {self.error_message or '未知错误'}"
        
        result = [f"{self.file_path} 的编译结果 ({self.language}):"]
        
        # 摘要信息
        if self.success and self.error_count == 0 and self.warning_count == 0:
            result.append("编译成功")
            if self.output_file:
                result.append(f"输出文件: {self.output_file}")
        else:
            summary = []
            if self.error_count > 0:
                summary.append(f"{self.error_count} 个错误")
            if self.warning_count > 0:
                summary.append(f"{self.warning_count} 个警告")
            if self.info_count > 0:
                summary.append(f"{self.info_count} 个信息")
                
            if summary:
                result.append("发现 " + "，".join(summary))
                
        if self.execution_time_ms is not None:
            result.append(f"执行时间: {self.execution_time_ms}毫秒")
            
        # 添加单个错误
        if self.errors:
            result.append("\n错误:")
            for error in self.errors:
                error_str = error.to_str(show_file_path=show_file_path_in_errors)
                # 缩进错误描述的每一行
                indented_error = "\n  ".join(error_str.splitlines())
                result.append(f"  {indented_error}")
        
        return "\n".join(result)

class ProjectCompilationResult(BaseModel):
    """整个项目的编译结果"""  
    project_path: str = Field(..., description="被编译的项目路径")
    file_results: Dict[str, FileCompilationResult] = Field(default_factory=dict, description="文件路径到其编译结果的映射")
    total_files: int = Field(0, description="编译的文件总数")
    files_with_errors: int = Field(0, description="至少有一个错误的文件数量")
    total_errors: int = Field(0, description="所有文件中发现的错误总数")
    total_warnings: int = Field(0, description="所有文件中的警告总数")
    total_infos: int = Field(0, description="所有文件中的信息性问题总数")
    success: bool = Field(True, description="整个项目的编译过程是否成功完成")
    error_message: Optional[str] = Field(None, description="如果编译失败，错误消息")    
    output_directory: Optional[str] = Field(None, description="编译输出的目录路径")

    def to_str(self, include_all_files: bool = True, include_errors: bool = True) -> str:
        """
        将项目编译结果转换为人类可读的字符串
        
        参数:
            include_all_files: 是否包含没有错误的文件的结果
            include_errors: 是否包含单个错误的详细信息
            
        返回:
            项目编译结果的格式化字符串表示
        """
        result = [f"项目编译结果 ({datetime.now().strftime('%Y-%m-%d %H:%M:%S')})"]
        
        result.append(f"项目: {self.project_path}")
            
        if not self.success:
            result.append(f"错误: {self.error_message or '未知错误'}")            
        
        # 摘要信息
        result.append(f"编译的文件: {self.total_files}")
        
        if self.success and self.total_errors == 0:
            result.append("编译成功完成")
            if self.output_directory:
                result.append(f"输出目录: {self.output_directory}")
        else:
            result.append(f"有错误的文件: {self.files_with_errors}")
            result.append(f"总错误数: {self.total_errors} ({self.total_errors} 个错误, {self.total_warnings} 个警告, {self.total_infos} 个信息)")
        
        # 添加每个文件的结果
        if self.file_results:
            result.append("\n按文件的结果:")
            
            for file_path, file_result in sorted(self.file_results.items()):
                # 如果请求，跳过没有错误的文件
                if not include_all_files and not (file_result.error_count + file_result.warning_count + file_result.info_count) > 0:
                    continue
                    
                if include_errors:
                    file_str = file_result.to_str(show_file_path_in_errors=False)
                    # 缩进文件结果的每一行
                    indented_file = "\n  ".join(file_str.splitlines())
                    result.append(f"  {indented_file}")
                else:
                    # 每个文件只有一行摘要
                    error_count = file_result.error_count + file_result.warning_count + file_result.info_count
                    if error_count > 0:
                        result.append(f"  {file_path}: {error_count} 个问题 ({file_result.error_count} 个错误, {file_result.warning_count} 个警告)")
                    else:
                        result.append(f"  {file_path}: 编译成功")
                        
                # 在文件之间添加分隔符以提高可读性
                result.append("")
        
        return "\n".join(result)

    def get_file_result(self, file_path: str) -> Optional[FileCompilationResult]:
        """
        获取特定文件的编译结果
        
        参数:
            file_path: 文件路径
            
        返回:
            文件的编译结果，如果文件未被编译则返回None
        """
        return self.file_results.get(file_path) 