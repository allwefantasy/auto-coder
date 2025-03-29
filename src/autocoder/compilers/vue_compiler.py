"""
Module for compiling/checking Vue.js code.
This module provides functionality to compile/check Vue.js code using tools like npm and vue-cli.
"""

import os
import json
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

class VueCompiler(BaseCompiler):
    """
    A class that provides compilation/checking functionality for Vue.js code.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the VueCompiler.
        
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
        return ['.vue', '.js', '.ts']
    
    def _check_dependencies(self) -> bool:
        """
        Check if required dependencies (node, npm) are installed.
        
        Returns:
            bool: True if all dependencies are available, False otherwise.
        """
        try:
            # Check if node is installed
            node_process = subprocess.run(
                ['node', '--version'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            
            # Check if npm is installed
            npm_process = subprocess.run(
                ['npm', '--version'], 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE
            )
            
            return node_process.returncode == 0 and npm_process.returncode == 0
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _is_vue_project(self, project_path: str) -> bool:
        """
        Check if a directory is a Vue.js project.
        
        Args:
            project_path (str): Path to check.
            
        Returns:
            bool: True if the directory contains a Vue.js project, False otherwise.
        """
        # Check for package.json
        package_json_path = os.path.join(project_path, 'package.json')
        if not os.path.exists(package_json_path):
            return False
        
        try:
            # Read package.json to check for Vue dependency
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            dependencies = package_data.get('dependencies', {})
            dev_dependencies = package_data.get('devDependencies', {})
            
            # Check if Vue is a dependency or vue-cli is a dev dependency
            return ('vue' in dependencies or
                    'vue' in dev_dependencies or
                    '@vue/cli-service' in dev_dependencies)
        except:
            return False
    
    def _parse_error_position(self, error_text: str) -> Tuple[int, Optional[int]]:
        """
        Parse line and column from error text.
        
        Args:
            error_text (str): Error text to parse.
            
        Returns:
            Tuple[int, Optional[int]]: Line and column (if found).
        """
        # Look for common patterns like "Line X:Y" or "line X, column Y" or "LX:CY"
        patterns = [
            r'[Ll]ine\s+(\d+)(?:[,:]\s*(?:column\s+)?(\d+))?',
            r'[Ll](\d+)(?:[,:]\s*[Cc](\d+))?',
            r'[\(\[](\d+)[,:]\s*(\d+)[\)\]]',
            r'at\s+\w+\s+\(.*?:(\d+)(?::(\d+))?\)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, error_text)
            if match:
                line = int(match.group(1))
                column = int(match.group(2)) if match.group(2) else None
                return line, column
        
        return 1, None  # Default to line 1 if not found
    
    def _parse_compilation_error(self, error_text: str, file_path: str) -> CompilationError:
        """
        Parse a compilation error message and create a CompilationError object.
        
        Args:
            error_text (str): Raw error message.
            file_path (str): Path to the file with the error.
            
        Returns:
            CompilationError: Parsed error object.
        """
        line, column = self._parse_error_position(error_text)
        
        return CompilationError(
            message=error_text,
            severity=CompilationErrorSeverity.ERROR,
            position=CompilationErrorPosition(
                line=line,
                column=column
            ),
            file_path=file_path,
            code="vue-compilation-error"
        )
    
    def _check_vue_file_syntax(self, file_path: str) -> Dict[str, Any]:
        """
        Check syntax of a Vue file using vue-template-compiler and babel.
        
        Args:
            file_path (str): Path to the file to check.
            
        Returns:
            Dict[str, Any]: Dictionary containing syntax check results.
        """
        errors = []
        error_count = 0
        warning_count = 0
        
        try:
            # Create a temporary directory
            with tempfile.TemporaryDirectory() as temp_dir:
                # Create a minimal package.json for Vue syntax checking
                package_json = {
                    "name": "vue-syntax-checker",
                    "version": "1.0.0",
                    "description": "Temporary package for Vue syntax checking",
                    "dependencies": {
                        "vue": "^2.6.12",
                        "vue-template-compiler": "^2.6.12",
                        "@babel/core": "^7.14.0",
                        "@babel/preset-env": "^7.14.0"
                    },
                    "scripts": {
                        "check": "node check-vue.js"
                    }
                }
                
                # Write package.json
                with open(os.path.join(temp_dir, 'package.json'), 'w') as f:
                    json.dump(package_json, f)
                
                # Create a script to check Vue file syntax
                checker_script = """
const fs = require('fs');
const compiler = require('vue-template-compiler');
const babel = require('@babel/core');

const filePath = process.argv[2];
const fileContent = fs.readFileSync(filePath, 'utf-8');

try {
    // Parse the Vue file
    const parsed = compiler.parseComponent(fileContent);
    
    // Check template syntax
    if (parsed.template) {
        try {
            compiler.compile(parsed.template.content);
        } catch (e) {
            console.error(`Template error: ${e.message}`);
            process.exit(1);
        }
    }
    
    // Check script syntax
    if (parsed.script) {
        try {
            babel.transformSync(parsed.script.content, {
                presets: ['@babel/preset-env']
            });
        } catch (e) {
            console.error(`Script error: ${e.message}`);
            process.exit(1);
        }
    }
    
    console.log('Syntax check passed');
    process.exit(0);
} catch (e) {
    console.error(`Error parsing Vue file: ${e.message}`);
    process.exit(1);
}
"""
                
                # Write the checker script
                with open(os.path.join(temp_dir, 'check-vue.js'), 'w') as f:
                    f.write(checker_script)
                
                # Install dependencies
                subprocess.run(
                    ['npm', 'install', '--silent'], 
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                
                # Run the checker
                cmd = ['node', 'check-vue.js', file_path]
                
                process = subprocess.run(
                    cmd,
                    cwd=temp_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Check for syntax errors
                if process.returncode != 0:
                    for line in process.stderr.splitlines():
                        if line.strip():
                            error = self._parse_compilation_error(line, file_path)
                            errors.append(error)
                            error_count += 1
        
        except Exception as e:
            errors.append(CompilationError(
                message=f"Error checking syntax: {str(e)}",
                severity=CompilationErrorSeverity.ERROR,
                position=CompilationErrorPosition(line=1),
                file_path=file_path,
                code="syntax-check-error"
            ))
            error_count += 1
        
        return {
            'success': error_count == 0,
            'errors': errors,
            'error_count': error_count,
            'warning_count': warning_count
        }
    
    def compile_file(self, file_path: str) -> Dict[str, Any]:
        """
        Compile (check) a single Vue.js file.
        
        Args:
            file_path (str): Path to the file to compile.
            
        Returns:
            Dict[str, Any]: Compilation results.
        """
        if not os.path.exists(file_path):
            return FileCompilationResult(
                file_path=file_path,
                success=False,
                language="vue",
                error_message=f"File not found: {file_path}"
            ).model_dump()
        
        if not self.is_supported_file(file_path):
            return FileCompilationResult(
                file_path=file_path,
                success=False,
                language="vue",
                error_message=f"Unsupported file type: {file_path}"
            ).model_dump()
        
        if not self._check_dependencies():
            return FileCompilationResult(
                file_path=file_path,
                success=False,
                language="vue",
                error_message="Node.js and npm are required but not found. Please make sure they are installed."
            ).model_dump()
        
        start_time = time.time()
        
        # Check syntax based on file type
        if file_path.endswith('.vue'):
            syntax_result = self._check_vue_file_syntax(file_path)
        else:
            # For .js and .ts files, reuse the same approach as ReactJS
            from autocoder.compilers.reactjs_compiler import ReactJSCompiler
            reactjs_compiler = ReactJSCompiler(verbose=self.verbose)
            syntax_result = reactjs_compiler._check_file_syntax(file_path)
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Create the result
        result = FileCompilationResult(
            file_path=file_path,
            success=syntax_result['success'],
            language="vue",
            errors=syntax_result['errors'],
            error_count=syntax_result['error_count'],
            warning_count=syntax_result['warning_count'],
            info_count=0,
            execution_time_ms=execution_time_ms
        )
        
        return result.model_dump()
    
    def compile_project(self, project_path: str) -> Dict[str, Any]:
        """
        Compile (build) a Vue.js project.
        
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
                error_message="Node.js and npm are required but not found. Please make sure they are installed."
            ).model_dump()
        
        if not self._is_vue_project(project_path):
            return ProjectCompilationResult(
                project_path=project_path,
                success=False,
                total_files=0,
                error_message=f"The directory does not appear to be a Vue.js project: {project_path}"
            ).model_dump()
        
        start_time = time.time()
        
        # Run npm build
        cmd = ['npm', 'run', 'build']
        
        process = subprocess.run(
            cmd,
            cwd=project_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        success = process.returncode == 0
        output = process.stdout + process.stderr
        errors = []
        error_count = 0
        warning_count = 0
        file_results = {}
        total_files = 0
        files_with_errors = 0
        
        # Find Vue files in the project
        vue_files = []
        for root, _, files in os.walk(project_path):
            for file in files:
                if any(file.endswith(ext) for ext in self.get_supported_extensions()):
                    # Skip node_modules directory
                    if 'node_modules' not in root:
                        file_path = os.path.join(root, file)
                        vue_files.append(file_path)
                        total_files += 1
        
        if not success:
            # Parse build errors
            file_error_map = {}  # Maps file paths to errors
            
            # Look for error patterns in the output
            # Vue CLI uses webpack, so errors are often similar to webpack errors
            error_blocks = re.split(r'ERROR\s+in\s+|Module build failed|Failed to compile', output)
            
            if len(error_blocks) > 1:  # If we found error blocks
                for block in error_blocks[1:]:  # Skip the first block (before the error)
                    # Try to find file path in error block
                    file_match = re.search(r'((?:\.\./)*(?:src|components|views|pages).*?\.(?:vue|js|ts))', block)
                    if file_match:
                        error_file = os.path.join(project_path, file_match.group(1))
                        if os.path.exists(error_file):
                            error_message = block.strip()
                            
                            if error_file not in file_error_map:
                                file_error_map[error_file] = []
                            
                            error = self._parse_compilation_error(error_message, error_file)
                            file_error_map[error_file].append(error)
                            errors.append(error)
                            error_count += 1
            
            # If no structured errors found, fall back to checking each file individually
            if not errors:
                for file_path in vue_files:
                    file_result = self.compile_file(file_path)
                    file_results[file_path] = file_result
                    
                    if not file_result['success']:
                        files_with_errors += 1
                    
                    error_count += file_result['error_count']
                    warning_count += file_result['warning_count']
                    
                    # Add file errors to the project errors list
                    for error in file_result.get('errors', []):
                        errors.append(error)
            else:
                # Create file results from the error map
                for file_path in vue_files:
                    file_errors = file_error_map.get(file_path, [])
                    
                    file_result = FileCompilationResult(
                        file_path=file_path,
                        success=len(file_errors) == 0,
                        language="vue",
                        errors=file_errors,
                        error_count=len(file_errors),
                        warning_count=0,
                        info_count=0
                    )
                    
                    file_results[file_path] = file_result.model_dump()
                    
                    if len(file_errors) > 0:
                        files_with_errors += 1
        else:
            # If build succeeded, create a success result for each file
            for file_path in vue_files:
                file_result = FileCompilationResult(
                    file_path=file_path,
                    success=True,
                    language="vue",
                    errors=[],
                    error_count=0,
                    warning_count=0,
                    info_count=0
                )
                
                file_results[file_path] = file_result.model_dump()
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Determine output directory based on Vue.js versions
        output_dir = os.path.join(project_path, 'dist')
        
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
            output_directory=output_dir if success else None
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

def compile_vue_file(file_path: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to compile a single Vue.js file.
    
    Args:
        file_path (str): Path to the file to compile.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing compilation results.
    """
    compiler = VueCompiler(verbose=verbose)
    return compiler.compile_file(file_path)

def compile_vue_project(project_path: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to compile a Vue.js project.
    
    Args:
        project_path (str): Path to the project directory.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing compilation results.
    """
    compiler = VueCompiler(verbose=verbose)
    return compiler.compile_project(project_path) 