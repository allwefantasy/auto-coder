"""
Module for compiling/checking Python code.
This module provides functionality to check Python code syntax and imports.
"""

import os
import sys
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

class PythonCompiler(BaseCompiler):
    """
    A class that provides compilation/checking functionality for Python code.
    For Python, "compilation" means checking syntax and imports.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the PythonCompiler.
        
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
        return ['.py']
    
    def _check_dependencies(self) -> bool:
        """
        Check if required dependencies are installed.
        
        Returns:
            bool: True if all dependencies are available, False otherwise.
        """
        try:
            # Check if python is installed
            subprocess.run([sys.executable, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
        
    def _check_syntax(self, file_path: str) -> Dict[str, Any]:
        """
        Check Python file syntax without executing the code.
        
        Args:
            file_path (str): Path to the file to check.
            
        Returns:
            Dict[str, Any]: Dictionary containing syntax check results.
        """
        result = {
            'success': True,
            'errors': [],
            'error_count': 0,
            'warning_count': 0
        }
        
        try:
            # Use Python's built-in compiler to check syntax
            with open(file_path, 'r', encoding='utf-8') as f:
                source = f.read()
            
            # Check syntax using compile
            try:
                compile(source, file_path, 'exec')
            except SyntaxError as e:
                # Create error details
                error = CompilationError(
                    message=str(e),
                    severity=CompilationErrorSeverity.ERROR,
                    position=CompilationErrorPosition(
                        line=e.lineno if e.lineno is not None else 1,
                        column=e.offset if e.offset is not None else 1
                    ),
                    file_path=file_path,
                    code="syntax-error"
                )
                
                # Try to get the source line
                if e.text:
                    error.source = e.text
                
                result['errors'].append(error)
                result['error_count'] += 1
                result['success'] = False
                
        except Exception as e:
            # Handle file reading errors
            result['success'] = False
            result['error_message'] = f"Error reading file: {str(e)}"
        
        return result
    
    def _check_imports(self, file_path: str) -> Dict[str, Any]:
        """
        Check if all imports in the Python file can be resolved.
        
        Args:
            file_path (str): Path to the file to check.
            
        Returns:
            Dict[str, Any]: Dictionary containing import check results.
        """
        result = {
            'success': True,
            'errors': [],
            'error_count': 0,
            'warning_count': 0
        }
        
        try:
            # Use a temporary directory for PYTHONPATH to avoid polluting the real environment
            with tempfile.TemporaryDirectory() as temp_dir:
                # Get the directory of the file to check
                file_dir = os.path.dirname(os.path.abspath(file_path))
                
                # Create a temporary file to check imports
                temp_file = os.path.join(temp_dir, "import_checker.py")
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(f"""
import sys
import os
import importlib.util
import re

# Add file directory to path
sys.path.insert(0, "{file_dir}")

# Try to extract imports from the file
with open("{file_path}", "r", encoding="utf-8") as source_file:
    source = source_file.read()

# Regular expressions to match import statements
import_patterns = [
    r'^\\s*import\\s+([\\w\\.]+)',  # import module
    r'^\\s*from\\s+([\\w\\.]+)\\s+import',  # from module import ...
]

# Find all imports
imports = []
for line in source.split('\\n'):
    for pattern in import_patterns:
        match = re.match(pattern, line)
        if match:
            module_name = match.group(1)
            # Handle relative imports
            if module_name.startswith('.'):
                continue  # Skip relative imports
            # Get the top-level package
            top_package = module_name.split('.')[0]
            if top_package not in imports:
                imports.append(top_package)

# Check each import
for module_name in imports:
    try:
        importlib.import_module(module_name)
        print(f"SUCCESS: {{module_name}}")
    except ImportError as e:
        print(f"ERROR: {{module_name}} - {{str(e)}}")
""")
                
                # Run the import checker
                cmd = [sys.executable, temp_file]
                process = subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                # Parse the output to find import errors
                line_num = 1  # Default line number for import errors
                for line in process.stdout.splitlines():
                    if line.startswith("ERROR:"):
                        # Extract module name and error message
                        _, module_info = line.split(":", 1)
                        module_name, error_msg = module_info.strip().split(" - ", 1)
                        
                        # Try to find the line number for this import
                        import_line = self._find_import_line(file_path, module_name)
                        if import_line > 0:
                            line_num = import_line
                        
                        # Create error details
                        error = CompilationError(
                            message=f"Import error for module '{module_name}': {error_msg}",
                            severity=CompilationErrorSeverity.ERROR,
                            position=CompilationErrorPosition(line=line_num),
                            file_path=file_path,
                            code="import-error"
                        )
                        
                        result['errors'].append(error)
                        result['error_count'] += 1
                
                # Check if there were any errors
                if result['error_count'] > 0:
                    result['success'] = False
                
        except Exception as e:
            # Handle any other errors
            result['success'] = False
            result['error_message'] = f"Error checking imports: {str(e)}"
        
        return result
    
    def _find_import_line(self, file_path: str, module_name: str) -> int:
        """
        Find the line number where a module is imported.
        
        Args:
            file_path (str): Path to the file.
            module_name (str): Name of the module to find.
            
        Returns:
            int: Line number (1-based) or 0 if not found.
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for i, line in enumerate(f, 1):
                    if re.search(r'^\s*import\s+' + re.escape(module_name), line) or \
                       re.search(r'^\s*from\s+' + re.escape(module_name) + r'\s+import', line):
                        return i
            return 0
        except Exception:
            return 0
                
    def compile_file(self, file_path: str) -> Dict[str, Any]:
        """
        Compile (check) a single Python file.
        
        Args:
            file_path (str): Path to the file to compile.
            
        Returns:
            Dict[str, Any]: Compilation results.
        """
        if not os.path.exists(file_path):
            return FileCompilationResult(
                file_path=file_path,
                success=False,
                language="python",
                error_message=f"File not found: {file_path}"
            ).model_dump()
        
        if not self.is_supported_file(file_path):
            return FileCompilationResult(
                file_path=file_path,
                success=False,
                language="python",
                error_message=f"Unsupported file type: {file_path}"
            ).model_dump()
        
        start_time = time.time()
        
        # First check syntax
        syntax_result = self._check_syntax(file_path)
        
        # Then check imports if syntax is correct
        import_result = {'errors': [], 'error_count': 0, 'warning_count': 0}
        if syntax_result['success']:
            import_result = self._check_imports(file_path)
        
        # Combine results
        all_errors = syntax_result['errors'] + import_result['errors']
        error_count = syntax_result['error_count'] + import_result['error_count']
        warning_count = syntax_result['warning_count'] + import_result['warning_count']
        
        # Calculate execution time
        execution_time_ms = int((time.time() - start_time) * 1000)
        
        # Create the final result
        result = FileCompilationResult(
            file_path=file_path,
            success=(error_count == 0),
            language="python",
            errors=all_errors,
            error_count=error_count,
            warning_count=warning_count,
            info_count=0,
            execution_time_ms=execution_time_ms
        )
        
        return result.model_dump()
    
    def compile_project(self, project_path: str) -> Dict[str, Any]:
        """
        Compile (check) a Python project.
        
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
        
        # Find all Python files
        python_files = []
        for root, _, files in os.walk(project_path):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        if not python_files:
            return ProjectCompilationResult(
                project_path=project_path,
                success=True,
                total_files=0,
                file_results={}
            ).model_dump()
        
        # Compile each file
        file_results = {}
        total_errors = 0
        total_warnings = 0
        files_with_errors = 0
        
        for file_path in python_files:
            file_result = self.compile_file(file_path)
            file_results[file_path] = file_result
            
            if file_result['error_count'] > 0:
                files_with_errors += 1
                total_errors += file_result['error_count']
            
            total_warnings += file_result['warning_count']
        
        # Create the project result
        result = ProjectCompilationResult(
            project_path=project_path,
            success=(total_errors == 0),
            total_files=len(python_files),
            files_with_errors=files_with_errors,
            total_errors=total_errors,
            total_warnings=total_warnings,
            total_infos=0,
            file_results={p: FileCompilationResult(**r) for p, r in file_results.items()}
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

def compile_python_file(file_path: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to compile a single Python file.
    
    Args:
        file_path (str): Path to the file to compile.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing compilation results.
    """
    compiler = PythonCompiler(verbose=verbose)
    return compiler.compile_file(file_path)

def compile_python_project(project_path: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to compile a Python project.
    
    Args:
        project_path (str): Path to the project directory.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing compilation results.
    """
    compiler = PythonCompiler(verbose=verbose)
    return compiler.compile_project(project_path) 