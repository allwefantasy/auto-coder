"""
Module for compiling code based on a provided YAML configuration.
This module reads from a compiler.yml file and runs the specified compilation command.
"""

import os
import subprocess
import re
import yaml
from typing import Dict, List, Any, Optional, Union
import time
from pathlib import Path

from autocoder.common import AutoCoderArgs
from autocoder.compilers.base_compiler import BaseCompiler
from autocoder.compilers.models import (
    CompilationError,
    FileCompilationResult,
    ProjectCompilationResult,
    CompilationErrorPosition,
    CompilationErrorSeverity
)
from autocoder.utils.project_structure import EnhancedFileAnalyzer
from loguru import logger


class ProvidedCompiler(BaseCompiler):
    """
    A compiler that uses a provided YAML configuration to execute compilation commands.
    It reads the configuration, runs the command, and processes the output based on
    extraction patterns defined in the YAML.
    """

    def __init__(self, verbose: bool = False, config_path: Optional[str] = None):
        """
        Initialize the ProvidedCompiler.

        Args:
            verbose (bool): Whether to display verbose output.
            config_path (Optional[str]): Path to the compiler.yml file. If None, will look in .auto-coder/projects/compiler.yml
        """
        super().__init__(verbose)
        self.config_path = config_path or os.path.join(".auto-coder","projects","compiler.yml")
        self.config = None

    def get_supported_extensions(self) -> List[str]:
        """
        Get the list of file extensions supported by this compiler.
        This is a generic compiler, so it returns an empty list as it doesn't target specific file types.

        Returns:
            List[str]: List of supported file extensions.
        """
        return []

    def _check_dependencies(self) -> bool:
        """
        Check if required dependencies are installed.
        For the provided compiler, we check if the compiler.yml file exists.

        Returns:
            bool: True if all dependencies are available, False otherwise.
        """
        return os.path.exists(self.config_path)

    def _load_config(self) -> bool:
        """
        Load the compiler configuration from YAML file.

        Returns:
            bool: True if configuration was loaded successfully, False otherwise.
        """
        if not self._check_dependencies():
            if self.verbose:
                print(f"Configuration file not found: {self.config_path}")
            return False

        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config = yaml.safe_load(f)

            if not self.config or 'compilers' not in self.config:
                if self.verbose:
                    print(f"Invalid configuration file: 'compilers' section not found")
                return False

            return True
        except Exception as e:
            if self.verbose:
                print(f"Error loading configuration: {str(e)}")
            return False

    def _run_compilation_command(self, project_path:str, compiler_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run the compilation command specified in the configuration.

        Args:
            compiler_config (Dict[str, Any]): Compiler configuration from YAML.

        Returns:
            Dict[str, Any]: Dictionary containing compilation results.
        """
        result = {
            'success': True,
            'errors': [],
            'error_count': 0,
            'warning_count': 0,
            'info_count': 0,
            'raw_output': "",
        }

        try:
            working_dir = os.path.join(project_path,compiler_config.get('working_dir', '.'))
            command = compiler_config.get('command')
            args = compiler_config.get('args', [])
            extract_regex = compiler_config.get('extract_regex')

            if not command:
                result['success'] = False
                result['error_message'] = "No command specified in configuration"
                return result

            # Create the full command with arguments
            full_command = [command] + args

            # Record start time
            start_time = time.time()

            # Run the command
            try:
                # Ensure the working directory exists
                os.makedirs(os.path.abspath(working_dir), exist_ok=True)

                # Run the command in the specified working directory
                process = subprocess.run(
                    full_command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    cwd=working_dir
                )

                # Combine stdout and stderr
                output = process.stdout + process.stderr
                result['raw_output'] = output

                # Set success based on return code
                result['success'] = process.returncode == 0

                # If unsuccessful and no error message is set
                if not result['success'] and not result.get('error_message'):
                    result['error_message'] = f"Command failed with exit code {process.returncode}"

                # Extract errors using regex if provided
                if extract_regex and output:
                    errors = self._extract_errors(
                        output, extract_regex, working_dir)
                    result['errors'] = errors
                    result['error_count'] = sum(
                        1 for e in errors if e.severity == CompilationErrorSeverity.ERROR)
                    result['warning_count'] = sum(
                        1 for e in errors if e.severity == CompilationErrorSeverity.WARNING)
                    result['info_count'] = sum(
                        1 for e in errors if e.severity == CompilationErrorSeverity.INFO)
                elif not result['success']:
                    result['errors'] = [CompilationError(
                        file_path="",
                        message=result['raw_output'],
                        severity=CompilationErrorSeverity.ERROR,
                        position=CompilationErrorPosition(                            
                            line=-1                            
                        ))]
            except subprocess.SubprocessError as e:
                result['success'] = False
                result['error_message'] = f"Error executing command: {str(e)}"

            # Calculate execution time
            result['execution_time_ms'] = int(
                (time.time() - start_time) * 1000)

        except Exception as e:
            result['success'] = False
            result['error_message'] = f"Unexpected error: {str(e)}"

        return result

    def _extract_errors(self, output: str, regex_pattern: str, base_path: str) -> List[CompilationError]:
        """
        Extract errors from command output using the provided regex pattern.

        Args:
            output (str): Command output text.
            regex_pattern (str): Regular expression to extract errors.
            base_path (str): Base path for file references.

        Returns:
            List[CompilationError]: List of extracted compilation errors.
        """
        errors = []

        try:
            pattern = re.compile(regex_pattern)
            matches = pattern.finditer(output)

            for match in matches:
                match_str = match.group(0)
                errors.append(CompilationError(
                    message=match_str,
                    severity=CompilationErrorSeverity.ERROR,
                    position=CompilationErrorPosition(
                        file_path="",
                        line=-1,
                        column=-1
                    )
                ))
        except Exception as e:
            # If regex parsing fails, create a generic error
            if self.verbose:
                print(f"Error parsing regex: {str(e)}")

        return errors

    def compile_file(self, file_path: str) -> Dict[str, Any]:
        """
        This compiler doesn't support compiling individual files directly.

        Args:
            file_path (str): Path to the file to compile.

        Returns:
            Dict[str, Any]: Error indicating that file compilation is not supported.
        """
        return {
            'success': False,
            'error_message': "ProvidedCompiler does not support compiling individual files.",
            'file_path': file_path,
            'language': 'unknown'
        }
    
    
    def get_all_extensions(self, directory: str = ".") -> str:
        """获取指定目录下所有文件的后缀名,多个按逗号分隔，并且带."""
        args = AutoCoderArgs(
            source_dir=directory,
            # 其他必要参数设置为默认值
            target_file="",
            git_url="",
            project_type="",
            conversation_prune_safe_zone_tokens=0
        )
        
        analyzer = EnhancedFileAnalyzer(
            args=args,
            llm=None,  # 如果只是获取后缀名，可以不需要LLM
            config=None  # 使用默认配置
        )
        
        # 获取分析结果
        analysis_result = analyzer.analyze_extensions()
        
        # 合并 code 和 config 的后缀名
        all_extensions = set(analysis_result["code"] + analysis_result["config"])
        
        # 转换为逗号分隔的字符串
        return ",".join(sorted(all_extensions))

    def compile_project(self, project_path: str,target_compiler_name:Optional[str] = None) -> ProjectCompilationResult:
        """
        Compile a project using configuration from compiler.yml.

        Args:
            project_path (str): Path to the project directory.

        Returns:
            Dict[str, Any]: Dictionary containing compilation results.
        """
        # Create a project compilation result
        result = ProjectCompilationResult(
            project_path=project_path,
            success=True
        )

        # Load configuration
        if not self._load_config():
            result.success = False
            result.error_message = f"Failed to load configuration from {self.config_path}"
            return result
        
        target_compiler_config = None
        if not target_compiler_name:                                 
            for compiler_config in self.config.get('compilers', []):
                working_dir = os.path.join(project_path,compiler_config.get('working_dir', '.'))
                print(working_dir)
                all_extensions = self.get_all_extensions(working_dir)                                
                triggers = compiler_config.get("triggers",[])                
                if any(trigger in all_extensions for trigger in triggers):
                    target_compiler_config = compiler_config
                    break
        
        if target_compiler_name:
            for compiler_config in self.config.get('compilers', []):
                if compiler_config.get("name","") == target_compiler_name:
                    target_compiler_config = compiler_config
                    break
        
        if not target_compiler_config:
            result.success = False
            result.error_message = f"Compiler {target_compiler_name} not found in configuration"
            return result
                
        logger.info(f"Using compiler to compile project({project_path}): {target_compiler_config.get('name','unknown')}")

        # Run the compilation command
        compile_result = self._run_compilation_command(project_path, target_compiler_config)
        compile_errors:List[CompilationError] = compile_result['errors']
        # logger.info(f"compile_result: {compile_result}")
        error_count = len(compile_errors)

        result = ProjectCompilationResult(
            project_path=project_path,            
            success=compile_result['success'],
            error_message=compile_result.get('error_message',''),
            file_results={
                "1":FileCompilationResult(
                file_path="1",  
                language="unknown",              
                errors=compile_errors,
                warning_count= 0,
                error_count= error_count,
                info_count=0,
                execution_time_ms=compile_result['execution_time_ms'],
                output_file=None
                )
            },
            total_errors=error_count,
            total_warnings=0,
            total_infos=0,
            total_files= -1 ,
            files_with_errors=error_count            
        )

        return result

    def format_compile_result(self, compile_result: Union[ProjectCompilationResult, FileCompilationResult]) -> str:
        """
        Format compilation results into a human-readable string.

        Args:
            compile_result (Dict[str, Any]): The compilation result dictionary.

        Returns:
            str: A formatted string representation of the compilation results.
        """
        if isinstance(compile_result, dict) and 'project_path' in compile_result:
            # This is a project compilation result
            project_result = ProjectCompilationResult(**compile_result)
            return project_result.to_str()
        elif isinstance(compile_result, dict) and 'file_path' in compile_result:
            # This is a file compilation result
            file_result = FileCompilationResult(**compile_result)
            return file_result.to_str()
        else:
            # For raw dictionary results
            if compile_result.get('success', False):
                return "Compilation successful"
            else:
                return f"Compilation failed: {compile_result.get('error_message', 'Unknown error')}"


def compile_with_provided_config(project_path: str, config_path: Optional[str] = None, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to compile a project using the provided configuration.

    Args:
        project_path (str): Path to the project directory.
        config_path (Optional[str]): Path to the compiler.yml file. If None, will look in .auto-coder/projects/compiler.yml
        verbose (bool): Whether to display verbose output.

    Returns:
        Dict[str, Any]: A dictionary containing compilation results.
    """
    compiler = ProvidedCompiler(verbose=verbose, config_path=config_path)
    return compiler.compile_project(project_path)
