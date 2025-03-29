"""
Module for compiling Java code.
This module provides functionality to compile Java code and report compilation errors.
"""

import os
import subprocess
import tempfile
import time
import re
from typing import Dict, List, Any, Optional, Tuple

from autocoder.compilers.base_compiler import BaseCompiler
from autocoder.compilers.models import (
    CompilationError, 
    FileCompilationResult, 
    ProjectCompilationResult,
    CompilationErrorPosition,
    CompilationErrorSeverity
)

class JavaCompiler(BaseCompiler):
    """
    A class that provides compilation functionality for Java code.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the JavaCompiler.
        
        Args:
            verbose (bool): Whether to display verbose output.
        """
        super().__init__(verbose)
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get the list of file extensions supported by this compiler.
        
        Returns:
            List[str]: List of supported file extensions.
        """
        return ['.java']
    
    def _check_dependencies(self) -> bool:
        """
        Check if required dependencies (javac) are installed.
        
        Returns:
            bool: True if all dependencies are available, False otherwise.
        """
        try:
            # Check if javac is installed
            process = subprocess.run(
                ['javac', '-version'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                text=True
            )
            return process.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _parse_javac_error(self, error_line: str, file_path: Optional[str] = None) -> Optional[CompilationError]:
        """
        Parse a javac error message into a CompilationError object.
        
        Args:
            error_line (str): Error line from javac output
            file_path (Optional[str]): The file path to use if not found in error message
            
        Returns:
            Optional[CompilationError]: Parsed error or None if couldn't parse
        """
        # Common javac error format: file_path:line: error: message
        match = re.match(r'(.*?):(\d+)(?::(\d+))?: (error|warning): (.*)', error_line)
        if match:
            error_file = match.group(1)
            line = int(match.group(2))
            column = int(match.group(3)) if match.group(3) else None
            severity_str = match.group(4)
            message = match.group(5)
            
            # Use provided file_path if error_file is not absolute
            if file_path and not os.path.isabs(error_file):
                # Try to find the full path
                if os.path.exists(os.path.join(os.path.dirname(file_path), error_file)):
                    error_file = os.path.join(os.path.dirname(file_path), error_file)
                else:
                    error_file = file_path
            
            return CompilationError(
                message=message,
                severity=CompilationErrorSeverity.ERROR if severity_str == 'error' else CompilationErrorSeverity.WARNING,
                position=CompilationErrorPosition(
                    line=line,
                    column=column
                ),
                file_path=error_file,
                code="java-compilation-error"
            )
        
        return None
    
    def compile_file(self, file_path: str) -> Dict[str, Any]:
        """
        Compile a single Java file.
        
        Args:
            file_path (str): Path to the file to compile.
            
        Returns:
            Dict[str, Any]: Compilation results.
        """
        if not os.path.exists(file_path):
            return FileCompilationResult(
                file_path=file_path,
                success=False,
                language="java",
                error_message=f"File not found: {file_path}"
            ).model_dump()
        
        if not self.is_supported_file(file_path):
            return FileCompilationResult(
                file_path=file_path,
                success=False,
                language="java",
                error_message=f"Unsupported file type: {file_path}"
            ).model_dump()
        
        if not self._check_dependencies():
            return FileCompilationResult(
                file_path=file_path,
                success=False,
                language="java",
                error_message="Java compiler (javac) not found. Please make sure JDK is installed."
            ).model_dump()
        
        start_time = time.time()
        errors = []
        error_count = 0
        warning_count = 0
        
        try:
            # Create a temporary directory for output
            with tempfile.TemporaryDirectory() as temp_dir:
                # Run javac on the file
                cmd = ['javac', '-d', temp_dir, file_path]
                
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Parse compilation errors
                if process.returncode != 0:
                    success = False
                    # Parse error output
                    error_lines = process.stderr.splitlines()
                    
                    for line in error_lines:
                        if not line.strip():
                            continue
                            
                        error = self._parse_javac_error(line, file_path)
                        if error:
                            errors.append(error)
                            if error.severity == CompilationErrorSeverity.ERROR:
                                error_count += 1
                            elif error.severity == CompilationErrorSeverity.WARNING:
                                warning_count += 1
                else:
                    success = True
                    
                # Get output file location (class file)
                output_file = None
                class_name = os.path.splitext(os.path.basename(file_path))[0]
                class_file = os.path.join(temp_dir, f"{class_name}.class")
                
                if os.path.exists(class_file):
                    output_file = class_file
        
        except Exception as e:
            return FileCompilationResult(
                file_path=file_path,
                success=False,
                language="java",
                error_message=f"Error during compilation: {str(e)}"
            ).model_dump()
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Create the result
        result = FileCompilationResult(
            file_path=file_path,
            success=success,
            language="java",
            errors=errors,
            error_count=error_count,
            warning_count=warning_count,
            info_count=0,
            execution_time_ms=execution_time_ms,
            output_file=output_file
        )
        
        return result.model_dump()
    
    def _is_maven_project(self, project_path: str) -> bool:
        """
        Check if a directory is a Maven project.
        
        Args:
            project_path (str): Path to the project directory.
            
        Returns:
            bool: True if it's a Maven project (has pom.xml), False otherwise.
        """
        return os.path.exists(os.path.join(project_path, 'pom.xml'))
    
    def _is_gradle_project(self, project_path: str) -> bool:
        """
        Check if a directory is a Gradle project.
        
        Args:
            project_path (str): Path to the project directory.
            
        Returns:
            bool: True if it's a Gradle project (has build.gradle), False otherwise.
        """
        return (os.path.exists(os.path.join(project_path, 'build.gradle')) or 
                os.path.exists(os.path.join(project_path, 'build.gradle.kts')))
    
    def _compile_maven_project(self, project_path: str) -> Dict[str, Any]:
        """
        Compile a Maven project.
        
        Args:
            project_path (str): Path to the Maven project directory.
            
        Returns:
            Dict[str, Any]: Compilation results.
        """
        errors = []
        error_count = 0
        warning_count = 0
        success = False
        
        try:
            # Run Maven compile
            cmd = ['mvn', 'compile', '-B']
            
            process = subprocess.run(
                cmd,
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            success = process.returncode == 0
            
            # Parse Maven output for errors
            if not success:
                output = process.stdout + process.stderr
                error_pattern = r'\[ERROR\] (.*?):(\d+)(?::(\d+))?: (.*)'
                
                for line in output.splitlines():
                    match = re.search(error_pattern, line)
                    if match:
                        source_file = match.group(1)
                        line_number = int(match.group(2))
                        column = int(match.group(3)) if match.group(3) else None
                        message = match.group(4)
                        
                        error = CompilationError(
                            message=message,
                            severity=CompilationErrorSeverity.ERROR,
                            position=CompilationErrorPosition(
                                line=line_number,
                                column=column
                            ),
                            file_path=source_file,
                            code="maven-compile-error"
                        )
                        
                        errors.append(error)
                        error_count += 1
            
            # Check for warnings too
            warning_pattern = r'\[WARNING\] (.*?):(\d+)(?::(\d+))?: (.*)'
            output = process.stdout + process.stderr
            
            for line in output.splitlines():
                match = re.search(warning_pattern, line)
                if match:
                    source_file = match.group(1)
                    line_number = int(match.group(2))
                    column = int(match.group(3)) if match.group(3) else None
                    message = match.group(4)
                    
                    warning = CompilationError(
                        message=message,
                        severity=CompilationErrorSeverity.WARNING,
                        position=CompilationErrorPosition(
                            line=line_number,
                            column=column
                        ),
                        file_path=source_file,
                        code="maven-compile-warning"
                    )
                    
                    errors.append(warning)
                    warning_count += 1
            
            return {
                'success': success,
                'errors': errors,
                'error_count': error_count,
                'warning_count': warning_count,
                'output_directory': os.path.join(project_path, 'target', 'classes') if success else None
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [],
                'error_count': 0,
                'warning_count': 0,
                'error_message': f"Error during Maven compilation: {str(e)}"
            }
    
    def _compile_gradle_project(self, project_path: str) -> Dict[str, Any]:
        """
        Compile a Gradle project.
        
        Args:
            project_path (str): Path to the Gradle project directory.
            
        Returns:
            Dict[str, Any]: Compilation results.
        """
        errors = []
        error_count = 0
        warning_count = 0
        success = False
        
        try:
            # Run Gradle build
            cmd = ['./gradlew', 'compileJava', '--console=plain']
            if not os.path.exists(os.path.join(project_path, 'gradlew')):
                cmd = ['gradle', 'compileJava', '--console=plain']
            
            process = subprocess.run(
                cmd,
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            success = process.returncode == 0
            
            # Parse Gradle output for errors
            if not success:
                output = process.stdout + process.stderr
                # Gradle error pattern: file_path:line: error: message
                error_pattern = r'(.*?):(\d+)(?::(\d+))?: (error|warning): (.*)'
                
                for line in output.splitlines():
                    match = re.search(error_pattern, line)
                    if match:
                        source_file = match.group(1)
                        line_number = int(match.group(2))
                        column = int(match.group(3)) if match.group(3) else None
                        severity_type = match.group(4)
                        message = match.group(5)
                        
                        error = CompilationError(
                            message=message,
                            severity=CompilationErrorSeverity.ERROR if severity_type == 'error' else CompilationErrorSeverity.WARNING,
                            position=CompilationErrorPosition(
                                line=line_number,
                                column=column
                            ),
                            file_path=source_file,
                            code="gradle-compile-error"
                        )
                        
                        errors.append(error)
                        if severity_type == 'error':
                            error_count += 1
                        else:
                            warning_count += 1
            
            return {
                'success': success,
                'errors': errors,
                'error_count': error_count,
                'warning_count': warning_count,
                'output_directory': os.path.join(project_path, 'build', 'classes') if success else None
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [],
                'error_count': 0,
                'warning_count': 0,
                'error_message': f"Error during Gradle compilation: {str(e)}"
            }
    
    def _compile_standard_java_project(self, project_path: str) -> Dict[str, Any]:
        """
        Compile a standard Java project (not using Maven or Gradle).
        
        Args:
            project_path (str): Path to the Java project directory.
            
        Returns:
            Dict[str, Any]: Compilation results.
        """
        errors = []
        error_count = 0
        warning_count = 0
        success = True
        file_results = {}
        
        try:
            # Create a temporary directory for output
            with tempfile.TemporaryDirectory() as temp_dir:
                # Find all Java files
                java_files = []
                for root, _, files in os.walk(project_path):
                    for file in files:
                        if file.endswith(".java"):
                            java_files.append(os.path.join(root, file))
                
                if not java_files:
                    return {
                        'success': True,
                        'errors': [],
                        'error_count': 0,
                        'warning_count': 0,
                        'file_results': {},
                        'message': "No Java files found in the project"
                    }
                
                # First try to compile all files together
                all_files_cmd = ['javac', '-d', temp_dir] + java_files
                
                process = subprocess.run(
                    all_files_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                if process.returncode == 0:
                    # Successfully compiled all files together
                    return {
                        'success': True,
                        'errors': [],
                        'error_count': 0,
                        'warning_count': 0,
                        'file_results': {f: {'success': True, 'error_count': 0} for f in java_files},
                        'output_directory': temp_dir
                    }
                
                # If all-at-once compilation failed, try compiling each file individually
                for file_path in java_files:
                    file_result = self.compile_file(file_path)
                    file_results[file_path] = file_result
                    
                    if not file_result['success']:
                        success = False
                    
                    error_count += file_result['error_count']
                    warning_count += file_result['warning_count']
                    errors.extend(file_result['errors'])
            
            return {
                'success': success,
                'errors': errors,
                'error_count': error_count,
                'warning_count': warning_count,
                'file_results': file_results,
                'output_directory': temp_dir if success else None
            }
            
        except Exception as e:
            return {
                'success': False,
                'errors': [],
                'error_count': 0,
                'warning_count': 0,
                'error_message': f"Error during Java compilation: {str(e)}"
            }
    
    def compile_project(self, project_path: str) -> Dict[str, Any]:
        """
        Compile a Java project.
        
        Args:
            project_path (str): Path to the project directory.
            
        Returns:
            Dict[str, Any]: Compilation results.
        """
        if not os.path.exists(project_path):
            return ProjectCompilationResult(
                project_path=project_path,
                success=False,
                total_files=0,
                error_message=f"Project directory not found: {project_path}"
            ).model_dump()
        
        if not self._check_dependencies():
            return ProjectCompilationResult(
                project_path=project_path,
                success=False,
                total_files=0,
                error_message="Java compiler (javac) not found. Please make sure JDK is installed."
            ).model_dump()
        
        start_time = time.time()
        
        # Determine project type and compile accordingly
        if self._is_maven_project(project_path):
            maven_result = self._compile_maven_project(project_path)
            success = maven_result['success']
            errors = maven_result.get('errors', [])
            error_count = maven_result.get('error_count', 0)
            warning_count = maven_result.get('warning_count', 0)
            output_directory = maven_result.get('output_directory')
            error_message = maven_result.get('error_message')
            
            # Count Java files in src/main/java
            java_dir = os.path.join(project_path, 'src', 'main', 'java')
            total_files = 0
            file_results = {}
            
            if os.path.exists(java_dir):
                for root, _, files in os.walk(java_dir):
                    for file in files:
                        if file.endswith(".java"):
                            java_file = os.path.join(root, file)
                            total_files += 1
                            
                            # Create a file result for each Java file
                            file_errors = [e for e in errors if e.file_path == java_file]
                            file_results[java_file] = FileCompilationResult(
                                file_path=java_file,
                                success=len(file_errors) == 0,
                                language="java",
                                errors=file_errors,
                                error_count=len([e for e in file_errors if e.severity == CompilationErrorSeverity.ERROR]),
                                warning_count=len([e for e in file_errors if e.severity == CompilationErrorSeverity.WARNING]),
                                info_count=0
                            ).model_dump()
        
        elif self._is_gradle_project(project_path):
            gradle_result = self._compile_gradle_project(project_path)
            success = gradle_result['success']
            errors = gradle_result.get('errors', [])
            error_count = gradle_result.get('error_count', 0)
            warning_count = gradle_result.get('warning_count', 0)
            output_directory = gradle_result.get('output_directory')
            error_message = gradle_result.get('error_message')
            
            # Count Java files in src/main/java
            java_dir = os.path.join(project_path, 'src', 'main', 'java')
            total_files = 0
            file_results = {}
            
            if os.path.exists(java_dir):
                for root, _, files in os.walk(java_dir):
                    for file in files:
                        if file.endswith(".java"):
                            java_file = os.path.join(root, file)
                            total_files += 1
                            
                            # Create a file result for each Java file
                            file_errors = [e for e in errors if e.file_path == java_file]
                            file_results[java_file] = FileCompilationResult(
                                file_path=java_file,
                                success=len(file_errors) == 0,
                                language="java",
                                errors=file_errors,
                                error_count=len([e for e in file_errors if e.severity == CompilationErrorSeverity.ERROR]),
                                warning_count=len([e for e in file_errors if e.severity == CompilationErrorSeverity.WARNING]),
                                info_count=0
                            ).model_dump()
        
        else:
            # Standard Java project
            standard_result = self._compile_standard_java_project(project_path)
            success = standard_result['success']
            errors = standard_result.get('errors', [])
            error_count = standard_result.get('error_count', 0)
            warning_count = standard_result.get('warning_count', 0)
            output_directory = standard_result.get('output_directory')
            error_message = standard_result.get('error_message')
            file_results = standard_result.get('file_results', {})
            
            # Count total files
            total_files = 0
            for root, _, files in os.walk(project_path):
                for file in files:
                    if file.endswith(".java"):
                        total_files += 1
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Count files with errors
        files_with_errors = len([f for f in file_results.values() if f.get('error_count', 0) > 0])
        
        # Create the project result
        result = ProjectCompilationResult(
            project_path=project_path,
            success=success,
            total_files=total_files,
            files_with_errors=files_with_errors,
            total_errors=error_count,
            total_warnings=warning_count,
            total_infos=0,
            file_results={p: FileCompilationResult(**r) for p, r in file_results.items()},
            error_message=error_message,
            output_directory=output_directory
        )
        
        return result.model_dump()
    
    def format_compile_result(self, compile_result: Dict[str, Any]) -> str:
        """
        Format compilation results into a human-readable string.
        
        Args:
            compile_result (Dict[str, Any]): The compilation result dictionary.
            
        Returns:
            str: A formatted string representation of the compilation results.
        """
        if 'project_path' in compile_result:
            # This is a project result
            return ProjectCompilationResult(**compile_result).to_str()
        else:
            # This is a file result
            return FileCompilationResult(**compile_result).to_str()

def compile_java_file(file_path: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to compile a single Java file.
    
    Args:
        file_path (str): Path to the file to compile.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing compilation results.
    """
    compiler = JavaCompiler(verbose=verbose)
    return compiler.compile_file(file_path)

def compile_java_project(project_path: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to compile a Java project.
    
    Args:
        project_path (str): Path to the project directory.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing compilation results.
    """
    compiler = JavaCompiler(verbose=verbose)
    return compiler.compile_project(project_path) 