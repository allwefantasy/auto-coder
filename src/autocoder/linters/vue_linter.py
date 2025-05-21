"""
Module for linting Vue projects.
This module provides functionality to analyze Vue projects for code quality and best practices.
"""

import os
import json
import subprocess
from typing import Dict, List, Optional, Any

from autocoder.linters.base_linter import BaseLinter


class VueLinter(BaseLinter):
    """
    A class that provides linting functionality for Vue projects and single files.
    """

    def __init__(self, verbose: bool = False):
        """
        Initialize the VueLinter.

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
            subprocess.run(["node", "--version"], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["npm", "--version"], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            subprocess.run(["npx", "--version"], check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return True
        except (subprocess.SubprocessError, FileNotFoundError):
            return False

    def get_supported_extensions(self) -> List[str]:
        """
        Get the list of file extensions supported by this linter.

        Returns:
            List[str]: List of supported file extensions.
        """
        return ['.vue', '.js', '.ts']

    def _detect_project_type(self, project_path: str) -> bool:
        """
        Detect whether the project is Vue.

        Args:
            project_path (str): Path to the project directory.

        Returns:
            bool: True if it's a Vue project, False otherwise
        """
        # Check for package.json
        package_json_path = os.path.join(project_path, 'package.json')
        if not os.path.exists(package_json_path):
            return False

        try:
            with open(package_json_path, 'r') as f:
                package_data = json.load(f)

            dependencies = {
                **package_data.get('dependencies', {}),
                **package_data.get('devDependencies', {})
            }

            # Check for Vue
            return 'vue' in dependencies
        except (json.JSONDecodeError, FileNotFoundError):
            return False

    def _detect_file_type(self, file_path: str) -> bool:
        """
        Detect if the file is a Vue file.

        Args:
            file_path (str): Path to the file.

        Returns:
            bool: True if it's a Vue file, False otherwise
        """
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return False

        # Get file extension
        ext = self.get_file_extension(file_path)

        if ext == '.vue':
            return True
        elif ext == '.js' or ext == '.ts':
            # Check content for Vue imports
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                if 'import Vue' in content or 'from "vue"' in content or "from 'vue'" in content:
                    return True
            except:
                pass
        
        return False

    def _install_eslint_if_needed(self, project_path: str) -> bool:
        """
        Install ESLint and the appropriate Vue plugins if they're not already installed.

        Args:
            project_path (str): Path to the project directory.

        Returns:
            bool: True if installation was successful, False otherwise.
        """
        try:
            # 首先尝试运行 npx eslint --version 检查是否已安装
            if self.verbose:
                print("Checking if ESLint is already installed...")
            
            try:
                result = subprocess.run(
                    ["npx", "eslint", "--version"],
                    cwd=project_path,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    check=False
                )
                
                if result.returncode == 0:
                    if self.verbose:
                        print(f"ESLint is already installed: {result.stdout.strip()}")
                    return True
            except subprocess.SubprocessError:
                if self.verbose:
                    print("ESLint not found via npx, will proceed with installation")
            
            # 检查 .eslintrc.* 配置文件是否存在
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

            # Install eslint and Vue plugins
            cmd = ["npm", "install", "--save-dev", "eslint", "eslint-plugin-vue"]
            if self.verbose:
                print("Installing ESLint with Vue plugins...")

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
                "extends": ["eslint:recommended", "plugin:vue/vue3-recommended"],
                "plugins": ["vue"],
                "parserOptions": {
                    "ecmaVersion": 2021,
                    "sourceType": "module"
                }
            }

            # Write configuration
            with open(os.path.join(project_path, '.eslintrc.json'), 'w') as f:
                json.dump(eslint_config, f, indent=2)
                
            return result.returncode == 0
        except subprocess.SubprocessError:
            return False

    def _extract_json_from_output(self, output_text: str) -> str:
        """
        Extract JSON string from output text that might contain non-JSON content at the beginning.
        
        Args:
            output_text (str): The output text that may contain a JSON string after a separator.
            
        Returns:
            str: The extracted JSON string, or the original text if no separator is found.
        """
        if "=============" in output_text:
            lines = output_text.split('\n')
            json_lines = []
            found_separator = False
            
            for line in lines:
                if line.startswith("============="):
                    found_separator = True
                    continue
                if found_separator:
                    json_lines.append(line)
            
            if json_lines:
                return '\n'.join(json_lines)
        
        return output_text

    def lint_file(self, file_path: str, fix: bool = False, project_path: str = None) -> Dict[str, Any]:
        """
        Lint a single Vue file using ESLint.

        Args:
            file_path (str): Path to the file to lint.
            fix (bool): Whether to automatically fix fixable issues.
            project_path (str, optional): Path to the project directory. If not provided, 
                                         the parent directory of the file will be used.

        Returns:
            Dict: A dictionary containing lint results.
        """
        result = {
            'success': False,
            'framework': 'vue',
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

        # Check if it's a Vue file
        if not self._detect_file_type(file_path):
            result['error'] = f"Not a Vue file: '{file_path}'"
            return result

        # Check dependencies
        if not self._check_dependencies():
            result['error'] = "Required dependencies (node, npm, npx) are not installed"
            return result

        # If project_path is not provided, use parent directory
        if project_path is None:
            project_path = os.path.dirname(file_path)

        # Install ESLint if needed
        if not self._install_eslint_if_needed(project_path):
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
                    output_text = process.stdout                    
                    try:
                        eslint_output = json.loads(output_text)
                    except json.JSONDecodeError:
                        # Try to extract JSON from output if it contains separator
                        json_text = self._extract_json_from_output(output_text)
                        eslint_output = json.loads(json_text)
                    
                    # print(f"eslint_output: {json.dumps(eslint_output, indent=4,ensure_ascii=False)}")

                    # Count files analyzed (should be 1)
                    result['files_analyzed'] = len(eslint_output)

                    # Track overall counts
                    total_errors = 0
                    total_warnings = 0

                    # Process the file result
                    for file_result in eslint_output:
                        file_rel_path = os.path.relpath(
                            file_result['filePath'], project_path)

                        # Add error and warning counts
                        total_errors += file_result.get('errorCount', 0)
                        total_warnings += file_result.get('warningCount', 0)

                        severity = "info"
                        if message.get('severity', 1) == 2:
                            severity = "error"
                        elif message.get('severity', 1) == 1:
                            severity = "warning"
                        elif message.get('severity', 1) == 0:
                            severity = "info"

                        # Process individual messages
                        for message in file_result.get('messages', []):
                            issue = {
                                'file': file_rel_path,
                                'line': message.get('line', 0),
                                'column': message.get('column', 0),
                                'severity': severity,
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
        Lint a Vue project.

        Args:
            project_path (str): Path to the project directory.
            fix (bool): Whether to automatically fix fixable issues.

        Returns:
            Dict: A dictionary containing lint results.
        """
        result = {
            'success': False,
            'framework': 'vue',
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
        if not self._detect_project_type(project_path):
            result['error'] = "Not a Vue project"
            return result

        # Install ESLint if needed
        if not self._install_eslint_if_needed(project_path):
            result['error'] = "Failed to install or configure ESLint"
            return result

        # Run ESLint
        try:
            cmd = ["npx", "eslint", "--format", "json"]

            # Add fix flag if requested
            if fix:
                cmd.append("--fix")

            # Target Vue files
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
                    try:
                        eslint_output = json.loads(process.stdout)
                    except json.JSONDecodeError:
                        # Try to extract JSON from output if it contains separator
                        json_text = self._extract_json_from_output(process.stdout)
                        eslint_output = json.loads(json_text)

                    # Count files analyzed
                    result['files_analyzed'] = len(eslint_output)

                    # Track overall counts
                    total_errors = 0
                    total_warnings = 0

                    # Process each file result
                    for file_result in eslint_output:
                        file_path = os.path.relpath(
                            file_result['filePath'], project_path)

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

        files_analyzed = lint_result.get('files_analyzed', 0)
        error_count = lint_result.get('error_count', 0)
        warning_count = lint_result.get('warning_count', 0)

        output = [
            "Vue Lint Results",
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

                    output.append(
                        f"  [{severity}] Line {line}, Col {column}: {message} ({rule})")

        return "\n".join(output)


def lint_project(project_path: str, fix: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to lint a Vue project.

    Args:
        project_path (str): Path to the project directory.
        fix (bool): Whether to automatically fix fixable issues.
        verbose (bool): Whether to display verbose output.

    Returns:
        Dict: A dictionary containing lint results.
    """
    linter = VueLinter(verbose=verbose)
    return linter.lint_project(project_path, fix=fix)


def lint_file(file_path: str, project_path: str = None, fix: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to lint a single Vue file.

    Args:
        file_path (str): Path to the file to lint.
        project_path (str, optional): Path to the project directory. If not provided, 
                                     the parent directory of the file will be used.
        fix (bool): Whether to automatically fix fixable issues.
        verbose (bool): Whether to display verbose output.

    Returns:
        Dict: A dictionary containing lint results.
    """
    linter = VueLinter(verbose=verbose)
    return linter.lint_file(file_path, fix=fix, project_path=project_path)


def format_lint_result(lint_result: Dict[str, Any]) -> str:
    """
    Format lint results into a human-readable string.

    Args:
        lint_result (Dict): The lint result dictionary.

    Returns:
        str: A formatted string representation of the lint results.
    """
    linter = VueLinter()
    return linter.format_lint_result(lint_result) 