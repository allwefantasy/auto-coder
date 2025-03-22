"""
Module for linting frontend projects (ReactJS and Vue).
This module provides functionality to analyze ReactJS and Vue projects for code quality and best practices.
"""

import os
import json
import subprocess
from typing import Dict, List, Optional, Union, Tuple, Any

from autocoder.linters.base_linter import BaseLinter

class FrontendLinter(BaseLinter):
    """
    A class that provides linting functionality for ReactJS and Vue projects and single files.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the FrontendLinter.
        
        Args:
            verbose (bool): Whether to display verbose output.
        """
        super().__init__(verbose)
    
    def _check_dependencies(self) -> bool:
        """
        Check if required dependencies (node, npm, npx) are installed.
        
        Returns:
            bool: True if all dependencies are available, False otherwise.
        """
        try:
            # Check if node and npm are installed
            subprocess.run(["node", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["npm", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["npx", "--version"], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False
    
    def get_supported_extensions(self) -> List[str]:
        """
        Get the list of file extensions supported by this linter.
        
        Returns:
            List[str]: List of supported file extensions.
        """
        return ['.js', '.jsx', '.ts', '.tsx', '.vue']
    
    def _detect_project_type(self, project_path: str) -> str:
        """
        Detect whether the project is ReactJS or Vue.
        
        Args:
            project_path (str): Path to the project directory.
            
        Returns:
            str: 'react', 'vue', or 'unknown'
        """
        # Check for package.json
        package_json_path = os.path.join(project_path, 'package.json')
        if not os.path.exists(package_json_path):
            return 'unknown'
        
        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)
            
            dependencies = {
                **package_data.get('dependencies', {}),
                **package_data.get('devDependencies', {})
            }
            
            # Check for React
            if 'react' in dependencies:
                return 'react'
            
            # Check for Vue
            if 'vue' in dependencies:
                return 'vue'
            
            return 'unknown'
        except (json.JSONDecodeError, FileNotFoundError):
            return 'unknown'
    
    def _detect_file_type(self, file_path: str) -> str:
        """
        Detect the type of file based on its extension.
        
        Args:
            file_path (str): Path to the file.
            
        Returns:
            str: 'react', 'vue', 'js', 'ts', or 'unknown'
        """
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return 'unknown'
        
        # Get file extension
        ext = self.get_file_extension(file_path)
        
        if ext == '.jsx' or ext == '.tsx':
            return 'react'
        elif ext == '.vue':
            return 'vue'
        elif ext == '.js':
            # Check content for React imports
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'import React' in content or 'from "react"' in content or "from 'react'" in content:
                    return 'react'
                return 'js'
            except:
                return 'js'
        elif ext == '.ts':
            return 'ts'
        else:
            return 'unknown'
    
    def _install_eslint_if_needed(self, project_path: str, project_type: str) -> bool:
        """
        Install ESLint and the appropriate plugins if they're not already installed.
        
        Args:
            project_path (str): Path to the project directory.
            project_type (str): Type of the project ('react' or 'vue').
            
        Returns:
            bool: True if installation was successful, False otherwise.
        """
        try:
            # Check if .eslintrc.* exists
            eslint_configs = [
                os.path.join(project_path, '.eslintrc'),
                os.path.join(project_path, '.eslintrc.js'),
                os.path.join(project_path, '.eslintrc.json'),
                os.path.join(project_path, '.eslintrc.yml'),
                os.path.join(project_path, '.eslintrc.yaml')
            ]
            
            if any(os.path.exists(config) for config in eslint_configs):
                if self.verbose:
                    print("ESLint configuration found.")
                return True
            
            # Install eslint and appropriate plugins
            if project_type == 'react':
                cmd = ["npm", "install", "--save-dev", "eslint", "eslint-plugin-react"]
                if self.verbose:
                    print("Installing ESLint with React plugins...")
            elif project_type == 'vue':
                cmd = ["npm", "install", "--save-dev", "eslint", "eslint-plugin-vue"]
                if self.verbose:
                    print("Installing ESLint with Vue plugins...")
            else:
                cmd = ["npm", "install", "--save-dev", "eslint"]
                if self.verbose:
                    print("Installing ESLint...")
            
            result = subprocess.run(
                cmd, 
                cwd=project_path, 
                stdout=subprocess.PIPE if not self.verbose else None,
                stderr=subprocess.PIPE if not self.verbose else None
            )
            
            # Create basic configuration
            eslint_config = {
                "env": {
                    "browser": True,
                    "es2021": True,
                    "node": True
                },
                "extends": ["eslint:recommended"]
            }
            
            if project_type == 'react':
                eslint_config["extends"].append("plugin:react/recommended")
                eslint_config["plugins"] = ["react"]
                eslint_config["parserOptions"] = {
                    "ecmaFeatures": {
                        "jsx": True
                    },
                    "ecmaVersion": 2021,
                    "sourceType": "module"
                }
            elif project_type == 'vue':
                eslint_config["extends"].append("plugin:vue/vue3-recommended")
                eslint_config["plugins"] = ["vue"]
                eslint_config["parserOptions"] = {
                    "ecmaVersion": 2021,
                    "sourceType": "module"
                }
            
            # Write configuration
            with open(os.path.join(project_path, '.eslintrc.json'), 'w') as f:
                json.dump(eslint_config, f, indent=2)
            
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False
    
    def lint_file(self, file_path: str, fix: bool = False, project_path: str = None) -> Dict[str, Any]:
        """
        Lint a single file using ESLint.
        
        Args:
            file_path (str): Path to the file to lint.
            fix (bool): Whether to automatically fix fixable issues.
            project_path (str, optional): Path to the project directory. If not provided, 
                                         the parent directory of the file will be used.
            
        Returns:
            Dict: A dictionary containing lint results with the same structure as lint_project.
        """
        result = {
            'success': False,
            'file_type': 'unknown',
            'files_analyzed': 0,
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
            result['error'] = "Required dependencies (node, npm, npx) are not installed"
            return result
        
        # If project_path is not provided, use parent directory
        if project_path is None:
            project_path = os.path.dirname(file_path)
        
        # Detect file type
        file_type = self._detect_file_type(file_path)
        result['file_type'] = file_type
        
        if file_type == 'unknown':
            result['error'] = f"Unsupported file type for '{file_path}'"
            return result
        
        # Map file_type to project_type for ESLint setup
        project_type_map = {
            'react': 'react',
            'vue': 'vue',
            'js': 'js',
            'ts': 'js'  # TypeScript uses generic JS ESLint with TS plugin
        }
        project_type = project_type_map.get(file_type, 'js')
        
        # Install ESLint if needed
        if not self._install_eslint_if_needed(project_path, project_type):
            result['error'] = "Failed to install or configure ESLint"
            return result
        
        # Run ESLint on the file
        try:
            cmd = ["npx", "eslint", "--format", "json"]
            
            # Add fix flag if requested
            if fix:
                cmd.append("--fix")
            
            # Add file path
            cmd.append(file_path)
            
            process = subprocess.run(
                cmd,
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Parse ESLint output
            if process.stdout:
                try:
                    eslint_output = json.loads(process.stdout)
                    
                    # Count files analyzed (should be 1)
                    result['files_analyzed'] = len(eslint_output)
                    
                    # Track overall counts
                    total_errors = 0
                    total_warnings = 0
                    
                    # Process the file result
                    for file_result in eslint_output:
                        file_rel_path = os.path.relpath(file_result['filePath'], project_path)
                        
                        # Add error and warning counts
                        total_errors += file_result.get('errorCount', 0)
                        total_warnings += file_result.get('warningCount', 0)
                        
                        # Process individual messages
                        for message in file_result.get('messages', []):
                            issue = {
                                'file': file_rel_path,
                                'line': message.get('line', 0),
                                'column': message.get('column', 0),
                                'severity': 'error' if message.get('severity', 1) == 2 else 'warning',
                                'message': message.get('message', ''),
                                'rule': message.get('ruleId', 'unknown')
                            }
                            result['issues'].append(issue)
                    
                    result['error_count'] = total_errors
                    result['warning_count'] = total_warnings
                    result['success'] = True
                except json.JSONDecodeError:
                    # Handle case where ESLint output is not valid JSON
                    result['error'] = "Failed to parse ESLint output"
            else:
                # Handle case where ESLint didn't produce any output
                stderr = process.stderr.strip()
                if stderr:
                    result['error'] = f"ESLint error: {stderr}"
                else:
                    # No errors found
                    result['success'] = True
        except subprocess.SubprocessError as e:
            result['error'] = f"Error running ESLint: {str(e)}"
        
        return result
    
    def lint_project(self, project_path: str, fix: bool = False) -> Dict[str, Any]:
        """
        Lint a ReactJS or Vue project.
        
        Args:
            project_path (str): Path to the project directory.
            fix (bool): Whether to automatically fix fixable issues.
            
        Returns:
            Dict: A dictionary containing lint results. Structure:
                {
                    'success': bool,
                    'project_type': str,
                    'files_analyzed': int,
                    'error_count': int,
                    'warning_count': int,
                    'issues': [
                        {
                            'file': str,
                            'line': int,
                            'column': int,
                            'severity': str,
                            'message': str,
                            'rule': str
                        },
                        ...
                    ]
                }
        """
        result = {
            'success': False,
            'project_type': 'unknown',
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
            result['error'] = "Required dependencies (node, npm, npx) are not installed"
            return result
        
        # Detect project type
        project_type = self._detect_project_type(project_path)
        result['project_type'] = project_type
        
        if project_type == 'unknown':
            result['error'] = "Unable to detect project type (neither React nor Vue)"
            return result
        
        # Install ESLint if needed
        if not self._install_eslint_if_needed(project_path, project_type):
            result['error'] = "Failed to install or configure ESLint"
            return result
        
        # Run ESLint
        try:
            cmd = ["npx", "eslint", "--format", "json"]
            
            # Add fix flag if requested
            if fix:
                cmd.append("--fix")
            
            # Target directories based on project type
            if project_type == 'react':
                cmd.extend([
                    "src/**/*.js", 
                    "src/**/*.jsx", 
                    "src/**/*.ts", 
                    "src/**/*.tsx"
                ])
            elif project_type == 'vue':
                cmd.extend([
                    "src/**/*.js", 
                    "src/**/*.vue", 
                    "src/**/*.ts"
                ])
            
            process = subprocess.run(
                cmd,
                cwd=project_path,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Parse ESLint output
            if process.stdout:
                try:
                    eslint_output = json.loads(process.stdout)
                    
                    # Count files analyzed
                    result['files_analyzed'] = len(eslint_output)
                    
                    # Track overall counts
                    total_errors = 0
                    total_warnings = 0
                    
                    # Process each file result
                    for file_result in eslint_output:
                        file_path = os.path.relpath(file_result['filePath'], project_path)
                        
                        # Add error and warning counts
                        total_errors += file_result.get('errorCount', 0)
                        total_warnings += file_result.get('warningCount', 0)
                        
                        # Process individual messages
                        for message in file_result.get('messages', []):
                            issue = {
                                'file': file_path,
                                'line': message.get('line', 0),
                                'column': message.get('column', 0),
                                'severity': 'error' if message.get('severity', 1) == 2 else 'warning',
                                'message': message.get('message', ''),
                                'rule': message.get('ruleId', 'unknown')
                            }
                            result['issues'].append(issue)
                    
                    result['error_count'] = total_errors
                    result['warning_count'] = total_warnings
                    result['success'] = True
                except json.JSONDecodeError:
                    # Handle case where ESLint output is not valid JSON
                    result['error'] = "Failed to parse ESLint output"
            else:
                # Handle case where ESLint didn't produce any output
                stderr = process.stderr.strip()
                if stderr:
                    result['error'] = f"ESLint error: {stderr}"
                else:
                    # No errors found
                    result['success'] = True
        except subprocess.SubprocessError as e:
            result['error'] = f"Error running ESLint: {str(e)}"
        
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
        
        # Handle both project_type and file_type
        if 'project_type' in lint_result:
            type_str = lint_result.get('project_type', 'unknown').capitalize()
            header = f"{type_str} Project Lint Results"
        else:
            type_str = lint_result.get('file_type', 'unknown').capitalize()
            header = f"{type_str} File Lint Results"
        
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
                    
                    output.append(f"  [{severity}] Line {line}, Col {column}: {message} ({rule})")
        
        return "\n".join(output)

def lint_project(project_path: str, fix: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to lint a ReactJS or Vue project.
    
    Args:
        project_path (str): Path to the project directory.
        fix (bool): Whether to automatically fix fixable issues.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict: A dictionary containing lint results.
    """
    linter = FrontendLinter(verbose=verbose)
    return linter.lint_project(project_path, fix=fix)

def lint_file(file_path: str, project_path: str = None, fix: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to lint a single file.
    
    Args:
        file_path (str): Path to the file to lint.
        project_path (str, optional): Path to the project directory. If not provided, 
                                     the parent directory of the file will be used.
        fix (bool): Whether to automatically fix fixable issues.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict: A dictionary containing lint results.
    """
    linter = FrontendLinter(verbose=verbose)
    return linter.lint_file(file_path, fix=fix, project_path=project_path)

def format_lint_result(lint_result: Dict[str, Any]) -> str:
    """
    Format lint results into a human-readable string.
    
    Args:
        lint_result (Dict): The lint result dictionary.
        
    Returns:
        str: A formatted string representation of the lint results.
    """
    linter = FrontendLinter()
    return linter.format_lint_result(lint_result) 