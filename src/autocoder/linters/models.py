"""
用于表示代码检查结果的 Pydantic 模型。
"""

from enum import Enum
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

class IssueSeverity(str, Enum):
    """问题严重性的枚举。"""
    ERROR = "error"  # 错误
    WARNING = "warning"  # 警告
    INFO = "info"  # 信息
    HINT = "hint"  # 提示

class IssuePosition(BaseModel):
    """文件中问题的位置。"""
    line: int = Field(..., description="发现问题的行号（从1开始）")
    column: Optional[int] = Field(None, description="发现问题的列号（从1开始）")
    end_line: Optional[int] = Field(None, description="问题的结束行号")
    end_column: Optional[int] = Field(None, description="问题的结束列号")

    def to_str(self) -> str:
        """将位置转换为人类可读的字符串。"""
        result = f"第 {self.line} 行"
        if self.column is not None:
            result += f"，第 {self.column} 列"
        if self.end_line is not None and (self.end_line != self.line or self.end_column is not None):
            result += f" 到第 {self.end_line} 行"
            if self.end_column is not None:
                result += f"，第 {self.end_column} 列"
        return result

class LintIssue(BaseModel):
    """单个lint问题的表示。"""
    code: str = Field(..., description="问题代码或标识符")
    message: str = Field(..., description="问题的人类可读描述")
    severity: IssueSeverity = Field(..., description="问题的严重性级别")
    position: IssuePosition = Field(..., description="问题在文件中的位置")
    file_path: str = Field(..., description="发现问题的文件路径")
    rule_name: Optional[str] = Field(None, description="违反的lint规则名称")
    source: Optional[str] = Field(None, description="发现问题的源代码片段")
    fix_available: bool = Field(False, description="是否有可用的自动修复")
    fix_description: Optional[str] = Field(None, description="可用修复的描述")

    def to_str(self, show_file_path: bool = True) -> str:
        """
        将问题转换为人类可读的字符串。
        
        参数:
            show_file_path: 是否在输出中包含文件路径
            
        返回:
            问题的格式化字符串表示
        """
        parts = []
        
        if show_file_path:
            parts.append(f"{self.file_path}:{self.position.line}")
        
        parts.append(f"[{self.severity.value.upper()}] {self.message}")
        
        if self.code:
            parts.append(f"({self.code})")
            
        if self.rule_name:
            parts.append(f"[规则: {self.rule_name}]")
            
        result = " ".join(parts)
        
        if self.source:
            # 为了更好的可读性，缩进源代码
            indented_source = "\n    ".join(self.source.splitlines())
            result += f"\n    {indented_source}"
            
        if self.fix_available and self.fix_description:
            result += f"\n    修复: {self.fix_description}"
            
        return result

class FileLintResult(BaseModel):
    """单个文件的lint结果。"""
    file_path: str = Field(..., description="被检查的文件路径")
    success: bool = Field(True, description="lint是否成功完成")
    language: str = Field(..., description="被检查的语言/文件类型")
    issues: List[LintIssue] = Field(default_factory=list, description="发现的lint问题列表")
    error: Optional[str] = Field(None, description="如果lint失败，错误消息")
    warning_count: int = Field(0, description="发现的警告数量")
    error_count: int = Field(0, description="发现的错误数量")
    info_count: int = Field(0, description="发现的信息性问题数量")
    execution_time_ms: Optional[int] = Field(None, description="lint文件所花费的时间（毫秒）")
    fixed_issues_count: Optional[int] = Field(None, description="自动修复的问题数量")

    def to_str(self, show_file_path_in_issues: bool = False) -> str:
        """
        将文件lint结果转换为人类可读的字符串。
        
        参数:
            show_file_path_in_issues: 是否在单个问题中包含文件路径
            
        返回:
            文件lint结果的格式化字符串表示
        """
        if not self.success:
            return f"检查 {self.file_path} 时出错: {self.error or '未知错误'}"
        
        result = [f"{self.file_path} 的检查结果 ({self.language}):"]
        
        # 摘要信息
        summary = []
        if self.error_count > 0:
            summary.append(f"{self.error_count} 个错误")
        if self.warning_count > 0:
            summary.append(f"{self.warning_count} 个警告")
        if self.info_count > 0:
            summary.append(f"{self.info_count} 个信息")
            
        if summary:
            result.append("发现 " + "，".join(summary))
        else:
            result.append("未发现问题")
            
        if self.execution_time_ms is not None:
            result.append(f"执行时间: {self.execution_time_ms}毫秒")
            
        if self.fixed_issues_count:
            result.append(f"已修复 {self.fixed_issues_count} 个问题")
            
        # 添加单个问题
        if self.issues:
            result.append("\n问题:")
            for issue in self.issues:
                issue_str = issue.to_str(show_file_path=show_file_path_in_issues)
                # 缩进问题描述的每一行
                indented_issue = "\n  ".join(issue_str.splitlines())
                result.append(f"  {indented_issue}")
        
        return "\n".join(result)

class ProjectLintResult(BaseModel):
    """整个项目或一组文件的lint结果。"""    
    project_path: Optional[str] = Field(None, description="被检查的项目路径")
    file_results: Dict[str, FileLintResult] = Field(..., description="文件路径到其lint结果的映射")
    total_files: int = Field(..., description="检查的文件总数")
    files_with_issues: int = Field(0, description="至少有一个问题的文件数量")
    total_issues: int = Field(0, description="所有文件中发现的问题总数")
    total_errors: int = Field(0, description="所有文件中的错误总数")
    total_warnings: int = Field(0, description="所有文件中的警告总数")
    total_infos: int = Field(0, description="所有文件中的信息性问题总数")
    success: bool = Field(True, description="所有文件的lint过程是否成功完成")
    error: Optional[str] = Field(None, description="如果lint失败，错误消息")
    fixed_issues_count: Optional[int] = Field(None, description="自动修复的问题数量")

    def to_str(self, include_all_files: bool = True, include_issues: bool = True) -> str:
        """
        将项目lint结果转换为人类可读的字符串。
        
        参数:
            include_all_files: 是否包含没有问题的文件的结果
            include_issues: 是否包含单个问题的详细信息
            
        返回:
            项目lint结果的格式化字符串表示
        """
        result = [f"项目代码检查结果 ({self.timestamp.strftime('%Y-%m-%d %H:%M:%S')})"]
        
        if self.project_path:
            result.append(f"项目: {self.project_path}")
            
        if not self.success:
            result.append(f"错误: {self.error or '未知错误'}")
            return "\n".join(result)
        
        # 摘要信息
        result.append(f"检查的文件: {self.total_files}")
        result.append(f"有问题的文件: {self.files_with_issues}")
        result.append(f"总问题数: {self.total_issues} ({self.total_errors} 个错误, {self.total_warnings} 个警告, {self.total_infos} 个信息)")
        
        if self.fixed_issues_count:
            result.append(f"已修复的问题: {self.fixed_issues_count}")
            
        # 添加每个文件的结果
        if self.file_results:
            result.append("\n按文件的结果:")
            
            for file_path, file_result in sorted(self.file_results.items()):
                # 如果请求，跳过没有问题的文件
                if not include_all_files and not (file_result.error_count + file_result.warning_count + file_result.info_count) > 0:
                    continue
                    
                if include_issues:
                    file_str = file_result.to_str(show_file_path_in_issues=False)
                    # 缩进文件结果的每一行
                    indented_file = "\n  ".join(file_str.splitlines())
                    result.append(f"  {indented_file}")
                else:
                    # 每个文件只有一行摘要
                    issue_count = file_result.error_count + file_result.warning_count + file_result.info_count
                    if issue_count > 0:
                        result.append(f"  {file_path}: {issue_count} 个问题 ({file_result.error_count} 个错误, {file_result.warning_count} 个警告)")
                    else:
                        result.append(f"  {file_path}: 无问题")
                        
                # 在文件之间添加分隔符以提高可读性
                result.append("")
        
        return "\n".join(result)

    def get_file_result(self, file_path: str) -> Optional[FileLintResult]:
        """
        获取特定文件的lint结果。
        
        参数:
            file_path: 文件路径
            
        返回:
            文件的lint结果，如果文件未被检查则返回None
        """
        return self.file_results.get(file_path) 