"""
用于对影子文件进行代码检查并将结果映射回项目路径的模块。
"""

import os
import time
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

from autocoder.linters.linter_factory import LinterFactory
from autocoder.shadows.shadow_manager import ShadowManager
from autocoder.linters.models import (
    LintIssue, 
    FileLintResult, 
    ProjectLintResult, 
    IssuePosition, 
    IssueSeverity
)
from loguru import logger as global_logger

class ShadowLinter:
    """
    用于对ShadowManager管理的文件进行代码检查并将结果转换回项目路径的类。
    """
    
    def __init__(self, shadow_manager: ShadowManager, verbose: bool = False):
        """
        使用ShadowManager实例初始化。
        
        参数:
            shadow_manager (ShadowManager): 用于管理文件路径映射的实例
            verbose (bool): 是否启用详细输出
        """
        self.shadow_manager = shadow_manager
        self.verbose = verbose
        self.logger = global_logger.bind(name="ShadowLinter")
        
    def lint_shadow_file(self, shadow_path: str, fix: bool = False) -> FileLintResult:
        """
        对单个影子文件进行代码检查并将结果中的路径转换为项目路径。
        
        参数:
            shadow_path (str): 影子文件的路径
            fix (bool): 是否自动修复问题
            
        返回:
            FileLintResult: 包含项目路径的代码检查结果
        """
        # 检查路径是否为影子路径
        if not self.shadow_manager.is_shadow_path(shadow_path):
            raise ValueError(f"不是影子路径: {shadow_path}")
            
        try:
            # 获取此影子文件的项目路径
            project_path = self.shadow_manager.from_shadow_path(shadow_path)
            
            # 记录开始时间以计算执行时间
            start_time = time.time()
            
            # 对影子文件运行代码检查
            raw_lint_result = LinterFactory.lint_file(shadow_path, fix=fix, verbose=self.verbose)
            
            # 如果lint过程返回None，创建一个空的结果对象，而不是直接返回None
            if raw_lint_result is None:
                language = self._detect_language(shadow_path)
                return FileLintResult(
                    file_path=project_path,
                    success=False,
                    language=language,
                    issues=[],  # 空问题列表
                    error=None,
                    error_count=0,
                    warning_count=0,
                    info_count=0
                )
            
            # 计算执行时间（毫秒）
            execution_time_ms = int((time.time() - start_time) * 1000)
            raw_lint_result['execution_time_ms'] = execution_time_ms
            
            # 将原始结果转换为Pydantic模型
            return self._convert_raw_lint_result(raw_lint_result, shadow_path, project_path)
        except Exception as e:
            if self.verbose:
                print(f"检查 {shadow_path} 时出错: {str(e)}")
            
            project_path = self.shadow_manager.from_shadow_path(shadow_path)
            language = self._detect_language(shadow_path)
            return FileLintResult(
                file_path=project_path,
                success=False,
                language=language,
                error=str(e),
                issues=[],  # 添加空问题列表
                error_count=0,
                warning_count=0,
                info_count=0
            )
    
    def lint_all_shadow_files(self, fix: bool = False) -> ProjectLintResult:
        """
        对影子目录中的所有文件进行代码检查并返回包含项目路径的结果。
        
        参数:
            fix (bool): 是否自动修复问题
            
        返回:
            ProjectLintResult: 所有文件的汇总代码检查结果
        """
        shadow_files = self._get_all_shadow_files()
        file_results = {}
        total_files = len(shadow_files)
        files_with_issues = 0
        total_issues = 0
        total_errors = 0
        total_warnings = 0
        total_infos = 0
        fixed_issues_count = 0
        
        # 处理每个影子文件
        for shadow_path in shadow_files:
            self.logger.info(f"正在检查文件: {shadow_path}")
            try:
                file_result = self.lint_shadow_file(shadow_path, fix=fix)
                self.logger.info(f"检查完成: {shadow_path}")
                # lint_shadow_file现在总是返回有效的FileLintResult，不再需要检查None
                project_path = self.shadow_manager.from_shadow_path(shadow_path)
                
                file_results[project_path] = file_result
                
                # 更新统计数据
                if file_result.success:
                    issue_count = len(file_result.issues)
                    if issue_count > 0:
                        files_with_issues += 1
                        total_issues += issue_count
                        total_errors += file_result.error_count
                        total_warnings += file_result.warning_count
                        total_infos += file_result.info_count
                    
                    if file_result.fixed_issues_count:
                        fixed_issues_count += file_result.fixed_issues_count
            except Exception as e:
                if self.verbose:
                    import traceback
                    traceback.print_exc()
                    print(f"处理 {shadow_path} 时出错: {str(e)}")
                
                # 加载的是影子文件，但是要转换成项目的路径
                project_path = self.shadow_manager.from_shadow_path(shadow_path)
                language = self._detect_language(shadow_path)
                file_results[project_path] = FileLintResult(
                    file_path=project_path,
                    success=False,
                    language=language,
                    error=str(e),
                    issues=[],
                    error_count=0,
                    warning_count=0,
                    info_count=0
                )
        
        # 创建项目结果
        return ProjectLintResult(
            project_path=self.shadow_manager.source_dir,
            file_results=file_results,
            total_files=total_files,
            files_with_issues=files_with_issues,
            total_issues=total_issues,
            total_errors=total_errors,
            total_warnings=total_warnings,
            total_infos=total_infos,
            fixed_issues_count=fixed_issues_count if fix else None
        )
    
    def lint_shadow_dir(self, shadow_dir: str, fix: bool = False) -> ProjectLintResult:
        """
        对特定影子目录中的所有文件进行代码检查。
        
        参数:
            shadow_dir (str): 影子目录的路径
            fix (bool): 是否自动修复问题
            
        返回:
            ProjectLintResult: 目录中所有文件的汇总代码检查结果
        """
        if not self.shadow_manager.is_shadow_path(shadow_dir):
            raise ValueError(f"不是影子路径: {shadow_dir}")
            
        shadow_files = self._get_files_in_dir(shadow_dir)
        file_results = {}
        total_files = len(shadow_files)
        files_with_issues = 0
        total_issues = 0
        total_errors = 0
        total_warnings = 0
        total_infos = 0
        fixed_issues_count = 0
        
        for shadow_path in shadow_files:
            try:
                file_result = self.lint_shadow_file(shadow_path, fix=fix)
                # lint_shadow_file现在总是返回有效的FileLintResult，不再需要检查None
                project_path = self.shadow_manager.from_shadow_path(shadow_path)
                
                file_results[project_path] = file_result
                
                # 更新统计数据
                if file_result.success:
                    issue_count = len(file_result.issues)
                    if issue_count > 0:
                        files_with_issues += 1
                        total_issues += issue_count
                        total_errors += file_result.error_count
                        total_warnings += file_result.warning_count
                        total_infos += file_result.info_count
                    
                    if file_result.fixed_issues_count:
                        fixed_issues_count += file_result.fixed_issues_count
            except Exception as e:
                if self.verbose:
                    print(f"处理 {shadow_path} 时出错: {str(e)}")
                
                project_path = self.shadow_manager.from_shadow_path(shadow_path)
                language = self._detect_language(shadow_path)
                file_results[project_path] = FileLintResult(
                    file_path=project_path,
                    success=False,
                    language=language,
                    error=str(e),
                    issues=[],
                    error_count=0,
                    warning_count=0,
                    info_count=0
                )
        
        # 创建项目结果
        project_path = self.shadow_manager.from_shadow_path(shadow_dir)
        return ProjectLintResult(
            project_path=project_path,
            file_results=file_results,
            total_files=total_files,
            files_with_issues=files_with_issues,
            total_issues=total_issues,
            total_errors=total_errors,
            total_warnings=total_warnings,
            total_infos=total_infos,
            fixed_issues_count=fixed_issues_count if fix else None
        )
    
    def _get_all_shadow_files(self) -> List[str]:
        """
        获取影子目录中的所有文件。
        
        返回:
            List[str]: 影子文件的绝对路径列表
        """
        all_files = []
        
        for root, _, files in os.walk(self.shadow_manager.shadows_dir):
            for file in files:
                # 跳过隐藏文件和目录
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                all_files.append(file_path)
                
        return all_files
    
    def _get_files_in_dir(self, directory: str) -> List[str]:
        """
        获取目录及其子目录中的所有文件。
        
        参数:
            directory (str): 目录路径
            
        返回:
            List[str]: 绝对文件路径列表
        """
        all_files = []
        
        for root, _, files in os.walk(directory):
            for file in files:
                # 跳过隐藏文件
                if file.startswith('.'):
                    continue
                    
                file_path = os.path.join(root, file)
                all_files.append(file_path)
                
        return all_files
    
    def _detect_language(self, file_path: str) -> str:
        """
        根据文件扩展名检测文件的语言。
        
        参数:
            file_path (str): 文件路径
            
        返回:
            str: 检测到的语言或"unknown"
        """
        try:
            language = LinterFactory._detect_language_from_file(file_path)
            # 确保返回值是字符串
            return language if isinstance(language, str) else "unknown"
        except ValueError:
            # 如果语言检测失败，返回默认值
            return "unknown"
        except Exception:
            # 捕获所有其他异常并返回默认值
            return "unknown"
    
    def _convert_raw_lint_result(self, raw_result: Dict[str, Any], shadow_path: str, project_path: str) -> FileLintResult:
        """
        将原始的linter输出转换为FileLintResult Pydantic模型。
        
        参数:
            raw_result (Dict[str, Any]): Linter的原始输出
            shadow_path (str): 影子文件的路径
            project_path (str): 项目文件的路径
            
        返回:
            FileLintResult: 标准化的lint结果模型
        """
        # 提取语言信息
        language = raw_result.get('language')
        if not isinstance(language, str):
            language = self._detect_language(shadow_path)
        
        # 初始化计数器
        error_count = 0
        warning_count = 0
        info_count = 0
        
        # 处理问题
        issues = []
        raw_issues = raw_result.get('issues', [])
        
        for raw_issue in raw_issues:
            # 确定严重性
            severity_str = raw_issue.get('severity', 'error').lower()
            if severity_str in ('error', 'critical', 'fatal'):
                severity = IssueSeverity.ERROR
                error_count += 1
                
                # 提取位置信息
                line = raw_issue.get('line', 1)
                column = raw_issue.get('column')
                end_line = raw_issue.get('end_line')
                end_column = raw_issue.get('end_column')
                
                position = IssuePosition(
                    line=line,
                    column=column,
                    end_line=end_line,
                    end_column=end_column
                )
                
                # 创建问题
                issue = LintIssue(
                    code=raw_issue.get('code', ''),
                    message=raw_issue.get('message', '未知问题'),
                    severity=severity,
                    position=position,
                    file_path=project_path,  # 使用项目路径而不是影子路径
                    rule_name=raw_issue.get('rule_name'),
                    source=raw_issue.get('source'),
                    fix_available=raw_issue.get('fix_available', False),
                    fix_description=raw_issue.get('fix_description')
                )
                
                issues.append(issue)
            elif severity_str in ('warning', 'warn'):
                severity = IssueSeverity.WARNING
                warning_count += 1
            else:
                severity = IssueSeverity.INFO
                info_count += 1
        
        # 创建文件结果
        return FileLintResult(
            file_path=project_path,
            success=raw_result.get('success', True),
            language=language,
            issues=issues,
            error=raw_result.get('error'),
            warning_count=warning_count,
            error_count=error_count,
            info_count=info_count,
            execution_time_ms=raw_result.get('execution_time_ms'),
            fixed_issues_count=raw_result.get('fixed_issues_count')
        ) 