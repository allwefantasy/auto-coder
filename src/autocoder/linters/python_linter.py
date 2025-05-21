import os
import sys
import json
import subprocess
import tempfile
from typing import Dict, List, Any, Optional, Tuple

from autocoder.linters.base_linter import BaseLinter
from loguru import logger

class PythonLinter(BaseLinter):
    """
    A class that provides linting functionality for Python code.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the PythonLinter.
        
        Args:
            verbose (bool): Whether to display verbose output.
        """
        super().__init__(verbose)        
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get the list of file extensions supported by this linter.
        
        Returns:
            List[str]: List of supported file extensions.
        """
        return ['.py']
    
    def _check_dependencies(self) -> bool:
        """
        Check if required dependencies (pylint, flake8, black) are installed.
        
        Returns:
            bool: True if all dependencies are available, False otherwise.
        """
        try:
            # Check if python is installed
            subprocess.run([sys.executable, "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Check for pylint or flake8
            has_pylint = False
            has_flake8 = False            
            
            try:
                subprocess.run([sys.executable, "-m", "pylint", "--version"], 
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                has_pylint = True
            except (subprocess.SubprocessError, FileNotFoundError):
                if self.verbose:
                    print("Pylint not found.")
            
            try:
                subprocess.run([sys.executable, "-m", "flake8", "--version"], 
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                has_flake8 = True
            except (subprocess.SubprocessError, FileNotFoundError):
                if self.verbose:
                    print("Flake8 not found.")                   
                
            # Need at least one linter
            return has_pylint or has_flake8
            
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def _install_dependencies_if_needed(self) -> bool:
        """
        Install required linting tools if they are not already installed.
        
        Returns:
            bool: True if installation was successful or dependencies already exist, False otherwise.
        """
        try:
            # Check for each dependency separately
            dependencies_to_install = []
            
            try:
                subprocess.run([sys.executable, "-m", "pylint", "--version"], 
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except (subprocess.SubprocessError, FileNotFoundError):
                dependencies_to_install.append("pylint")
            
            try:
                subprocess.run([sys.executable, "-m", "flake8", "--version"], 
                              check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            except (subprocess.SubprocessError, FileNotFoundError):
                dependencies_to_install.append("flake8")                        
            
            # Install missing dependencies
            if dependencies_to_install:
                if self.verbose:
                    print(f"Installing missing dependencies: {', '.join(dependencies_to_install)}")
                
                install_cmd = [sys.executable, "-m", "pip", "install"] + dependencies_to_install
                
                result = subprocess.run(
                    install_cmd,
                    stdout=subprocess.PIPE if not self.verbose else None,
                    stderr=subprocess.PIPE if not self.verbose else None
                )
                
                return result.returncode == 0
            
            return True  # All dependencies already installed
            
        except Exception as e:
            if self.verbose:
                print(f"Error installing dependencies: {str(e)}")
            return False
    
    def _run_pylint(self, target: str) -> Dict[str, Any]:
        """
        Run pylint on the target file or directory.
        
        Args:
            target (str): Path to the file or directory to lint.
            
        Returns:
            Dict[str, Any]: The pylint results.
        """
        result = {
            'error_count': 0,
            'warning_count': 0,
            'issues': []
        }

        logger.info(f"Running pylint on {target}")
        
        try:
            # Create a temp file to store JSON output
            with tempfile.NamedTemporaryFile(suffix='.json', delete=False) as tmp:
                tmp_path = tmp.name
            
            # Run pylint with JSON reporter
            cmd = [
                sys.executable, 
                "-m", 
                "pylint",                 
                "--output-format=json", 
                target
            ]
            
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if process.stdout:
                try:
                    pylint_output = json.loads(process.stdout)
                    
                    # Process pylint issues
                    for message in pylint_output:
                        severity = "info"
                        if message.get('type') in ['error', 'fatal']:
                            severity = "error"
                            result['error_count'] += 1
                        elif message.get('type') in ['warning']:
                            severity = "warning"
                            result['warning_count'] += 1
                        else:                            
                            result['info_count'] += 1
                        
                        issue = {
                            'file': message.get('path', ''),
                            'line': message.get('line', 0),
                            'column': message.get('column', 0),
                            'severity': severity,
                            'message': message.get('message', ''),
                            'rule': message.get('symbol', 'unknown'),
                            'tool': 'pylint'
                        }
                        
                        result['issues'].append(issue)
                    
                except json.JSONDecodeError:
                    # Handle non-JSON output (like when no files to check)
                    pass
                    
            # Cleanup temp file
            try:
                os.unlink(tmp_path)
            except:
                pass
                
        except Exception as e:
            if self.verbose:
                print(f"Error running pylint: {str(e)}")
        
        return result
    
    def _run_flake8(self, target: str) -> Dict[str, Any]:
        """
        Run flake8 on the target file or directory.
        
        Args:
            target (str): Path to the file or directory to lint.
            
        Returns:
            Dict[str, Any]: The flake8 results.
        """
        result = {
            'error_count': 0,
            'warning_count': 0,
            'issues': []
        }
        
        try:
            # Run flake8
            cmd = [
                sys.executable, 
                "-m", 
                "flake8", 
                target
            ]
            
            process = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if process.stdout:
                # Parse flake8 output
                for line in process.stdout.splitlines():
                    if not line.strip():
                        continue
                    
                    try:
                        # Parse the line (format: "file:line:col: code message")
                        parts = line.split(':', 3)
                        if len(parts) >= 4:
                            file_path = parts[0]
                            line_num = int(parts[1])
                            col_num = int(parts[2].split(' ')[0])
                            
                            code_message = parts[3].strip()
                            code_parts = code_message.split(' ', 1)
                            
                            if len(code_parts) >= 2:
                                code = code_parts[0]
                                message = code_parts[1]
                            else:
                                code = "unknown"
                                message = code_message
                            
                            # Determine severity based on error code
                            severity = "info"
                            # E errors are generally more serious than F warnings
                            if code.startswith('F'):
                                severity = "error"
                                result['error_count'] += 1
                            elif code.startswith('E'):
                                severity = "warning"
                                result['warning_count'] += 1
                            else:
                                result['info_count'] += 1
                            
                            issue = {
                                'file': file_path,
                                'line': line_num,
                                'column': col_num,
                                'severity': severity,
                                'message': message,
                                'rule': code,
                                'tool': 'flake8'
                            }
                            
                            result['issues'].append(issue)
                    except (ValueError, IndexError):
                        # Skip malformed lines
                        continue
        
        except Exception as e:
            if self.verbose:
                print(f"Error running flake8: {str(e)}")
        
        return result
    
    

    def lint_file(self, file_path: str, fix: bool = False) -> Dict[str, Any]:
        """
        Lint a single Python file.
        
        Args:
            file_path (str): Path to the file to lint.
            fix (bool): Whether to automatically fix fixable issues.
            
        Returns:
            Dict[str, Any]: Lint results.
        """
        result = {
            'success': False,
            'language': 'python',
            'files_analyzed': 1,
            'error_count': 0,
            'warning_count': 0,
            'issues': []
        }
        
        # Check if file exists
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            result['error'] = f"File '{file_path}' does not exist or is not a file"
            return result
        
        # Check if file is supported
        if not self.is_supported_file(file_path):
            result['error'] = f"Unsupported file type for '{file_path}'"
            return result
        
        # Check dependencies
        if not self._check_dependencies():
            # Try to install dependencies
            if not self._install_dependencies_if_needed():
                result['error'] = "Required dependencies are not installed and could not be installed automatically"
                return result               
        
        # Run pylint
        try:
            pylint_result = self._run_pylint(file_path)
            result['issues'].extend(pylint_result['issues'])
            result['error_count'] += pylint_result['error_count']
            result['warning_count'] += pylint_result['warning_count']
        except Exception as e:
            if self.verbose:
                print(f"Error running pylint: {str(e)}")               
        
        # Mark as successful
        result['success'] = True
        
        return result
    
    def lint_project(self, project_path: str, fix: bool = False) -> Dict[str, Any]:
        """
        Lint a Python project.
        
        Args:
            project_path (str): Path to the project directory.
            fix (bool): Whether to automatically fix fixable issues.
            
        Returns:
            Dict[str, Any]: Lint results.
        """
        result = {
            'success': False,
            'language': 'python',
            'files_analyzed': 0,
            'error_count': 0,
            'warning_count': 0,
            'issues': []
        }
        
        # Check if the path exists
        if not os.path.exists(project_path) or not os.path.isdir(project_path):
            result['error'] = f"Path '{project_path}' does not exist or is not a directory"
            return result
        
        # Check dependencies
        if not self._check_dependencies():
            # Try to install dependencies
            if not self._install_dependencies_if_needed():
                result['error'] = "Required dependencies are not installed and could not be installed automatically"
                return result
        
        # Find Python files in the project
        python_files = []
        for root, _, files in os.walk(project_path):
            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))
        
        result['files_analyzed'] = len(python_files)
             
        
        # Run pylint
        try:
            pylint_result = self._run_pylint(project_path)
            result['issues'].extend(pylint_result['issues'])
            result['error_count'] += pylint_result['error_count']
            result['warning_count'] += pylint_result['warning_count']
        except Exception as e:
            if self.verbose:
                print(f"Error running pylint: {str(e)}")
                        
        # Mark as successful
        result['success'] = True
        
        return result
    
    def format_lint_result(self, lint_result: Dict[str, Any]) -> str:
        """
        Format lint results into a human-readable string.
        
        Args:
            lint_result (Dict): The lint result dictionary.
            
        Returns:
            str: A formatted string representation of the lint results.
        """
        if not lint_result.get('success', False):
            return f"Linting failed: {lint_result.get('error', 'Unknown error')}"
        
        header = "Python Code Lint Results"
        files_analyzed = lint_result.get('files_analyzed', 0)
        error_count = lint_result.get('error_count', 0)
        warning_count = lint_result.get('warning_count', 0)
        
        output = [
            header,
            f"{'=' * 30}",
            f"Files analyzed: {files_analyzed}",
            f"Errors: {error_count}",
            f"Warnings: {warning_count}",
            ""
        ]
        
        if error_count == 0 and warning_count == 0:
            output.append("No issues found. Great job!")
        else:
            output.append("Issues:")
            output.append(f"{'-' * 30}")
            
            # Group issues by file
            issues_by_file = {}
            for issue in lint_result.get('issues', []):
                file_path = issue.get('file', '')
                if file_path not in issues_by_file:
                    issues_by_file[file_path] = []
                issues_by_file[file_path].append(issue)
            
            # Display issues grouped by file
            for file_path, issues in issues_by_file.items():
                output.append(f"\nFile: {file_path}")
                
                for issue in issues:
                    severity = issue.get('severity', '').upper()
                    line = issue.get('line', 0)
                    column = issue.get('column', 0)
                    message = issue.get('message', '')
                    rule = issue.get('rule', 'unknown')
                    tool = issue.get('tool', 'unknown')
                    
                    output.append(f"  [{severity}] Line {line}, Col {column}: {message} ({rule} - {tool})")
        
        return "\n".join(output)

def lint_python_file(file_path: str, fix: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to lint a single Python file.
    
    Args:
        file_path (str): Path to the file to lint.
        fix (bool): Whether to automatically fix fixable issues.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing lint results.
    """
    linter = PythonLinter(verbose=verbose)
    return linter.lint_file(file_path, fix=fix)

def lint_python_project(project_path: str, fix: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to lint a Python project.
    
    Args:
        project_path (str): Path to the project directory.
        fix (bool): Whether to automatically fix fixable issues.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing lint results.
    """
    linter = PythonLinter(verbose=verbose)
    return linter.lint_project(project_path, fix=fix)

def format_lint_result(lint_result: Dict[str, Any]) -> str:
    """
    Format lint results into a human-readable string.
    
    Args:
        lint_result (Dict): The lint result dictionary.
        
    Returns:
        str: A formatted string representation of the lint results.
    """
    linter = PythonLinter()
    return linter.format_lint_result(lint_result) 