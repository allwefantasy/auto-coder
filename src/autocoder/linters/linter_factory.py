"""
Module providing a factory for creating language-specific linters.
"""

import os
from typing import Optional, Dict, Any, List

from autocoder.linters.base_linter import BaseLinter
from autocoder.linters.reactjs_linter import ReactJSLinter
from autocoder.linters.vue_linter import VueLinter
from autocoder.linters.python_linter import PythonLinter
from loguru import logger

class LinterFactory:
    """
    Factory class for creating appropriate linter instances based on file type or language.
    """
    
    @classmethod
    def create_linter(cls, language: Optional[str] = None, file_path: Optional[str] = None, verbose: bool = False) -> BaseLinter:
        """
        Create and return an appropriate linter instance based on language or file path.
        
        Args:
            language (Optional[str]): Language identifier ('python', 'javascript', 'typescript', etc.).
            file_path (Optional[str]): Path to a file to infer the language from.
            verbose (bool): Whether to enable verbose output in the linter.
            
        Returns:
            BaseLinter: An instance of a linter appropriate for the language.
            
        Raises:
            ValueError: If no language could be determined or if the language is not supported.
        """
        if language is None and file_path is None:
            raise ValueError("Either language or file_path must be provided")
        
        # If language is not provided, try to infer from file path
        if language is None and file_path is not None:
            language = cls._detect_language_from_file(file_path)
        
        # Map language to linter class
        linter_map = {
            'python': PythonLinter,
            'javascript': ReactJSLinter,
            'typescript': ReactJSLinter,
            'js': ReactJSLinter,
            'ts': ReactJSLinter,
            'jsx': ReactJSLinter,
            'tsx': ReactJSLinter,
            'react': ReactJSLinter,
            'reactjs': ReactJSLinter,
            'vue': VueLinter,
        }
        
        linter_class = linter_map.get(language.lower() if language else None)
        
        if linter_class is None:
            return None
        
        return linter_class(verbose=verbose)
    
    @classmethod
    def _detect_language_from_file(cls, file_path: str) -> Optional[str]:
        """
        Detect the programming language based on file extension.
        
        Args:
            file_path (str): Path to the file.
            
        Returns:
            str: Language identifier.
            
        Raises:
            ValueError: If the file extension is not recognized.
        """
        if not os.path.exists(file_path):
            return None
        
        _, ext = os.path.splitext(file_path)
        ext = ext.lower()
        
        # Map extensions to languages
        extension_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'react',
            '.tsx': 'react',
            '.vue': 'vue',
        }
        
        language = extension_map.get(ext)                
        return language
    
    @classmethod
    def get_supported_languages(cls) -> List[str]:
        """
        Get a list of supported programming languages.
        
        Returns:
            List[str]: List of supported language identifiers.
        """
        return ['python', 'javascript', 'typescript', 'react', 'vue']
    
    @classmethod
    def lint_file(cls, file_path: str, fix: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """
        Lint a single file using the appropriate linter.
        
        Args:
            file_path (str): Path to the file to lint.
            fix (bool): Whether to automatically fix fixable issues.
            verbose (bool): Whether to enable verbose output.
            
        Returns:
            Dict[str, Any]: Lint results.
        """
        logger.info(f"根据文件路径{file_path}自动查找 linter")
        linter = cls.create_linter(file_path=file_path, verbose=verbose)
        logger.info(f"Linting file: {file_path} with linter: {linter.__class__.__name__}")
        if linter is None:
            return None        
        return linter.lint_file(file_path, fix=fix)
    
    @classmethod
    def lint_project(cls, project_path: str, language: Optional[str] = None, fix: bool = False, verbose: bool = False) -> Dict[str, Any]:
        """
        Lint a project using the appropriate linter.
        
        Args:
            project_path (str): Path to the project directory.
            language (Optional[str]): Language identifier to specify which linter to use.
                                     If not provided, will try to auto-detect.
            fix (bool): Whether to automatically fix fixable issues.
            verbose (bool): Whether to enable verbose output.
            
        Returns:
            Dict[str, Any]: Lint results.
        """
        # If language not specified, try to detect from project contents
        if language is None:
            # First check for package.json (JavaScript/TypeScript/React/Vue)
            if os.path.exists(os.path.join(project_path, 'package.json')):
                # Check if it's a React or Vue project
                try:
                    with open(os.path.join(project_path, 'package.json'), 'r') as f:
                        import json
                        package_data = json.load(f)
                        
                    dependencies = {
                        **package_data.get('dependencies', {}),
                        **package_data.get('devDependencies', {})
                    }
                    
                    if 'react' in dependencies:
                        language = 'react'
                    elif 'vue' in dependencies:
                        language = 'vue'
                    else:
                        language = 'javascript'
                except:
                    language = 'javascript'  # Default to JavaScript
            # Check for setup.py or requirements.txt (Python)
            elif (os.path.exists(os.path.join(project_path, 'setup.py')) or
                  os.path.exists(os.path.join(project_path, 'requirements.txt'))):
                language = 'python'
            else:
                # Count file extensions to guess the dominant language
                language_counts = {}
                for root, _, files in os.walk(project_path):
                    for file in files:
                        _, ext = os.path.splitext(file)
                        ext = ext.lower()
                        language_counts[ext] = language_counts.get(ext, 0) + 1
                
                # Find the most common relevant extension
                relevant_extensions = {'.py', '.js', '.ts', '.jsx', '.tsx', '.vue'}
                most_common = None
                max_count = 0
                
                for ext, count in language_counts.items():
                    if ext in relevant_extensions and count > max_count:
                        most_common = ext
                        max_count = count
                
                if most_common is None:
                    raise ValueError(f"Could not detect project language in {project_path}")
                
                language = cls._detect_language_from_file(f"dummy{most_common}")
        
        linter = cls.create_linter(language=language, verbose=verbose)
        if linter is None:
            return None
        return linter.lint_project(project_path, fix=fix)
    
    @classmethod
    def format_lint_result(cls, lint_result: Dict[str, Any], language: Optional[str] = None) -> str:
        """
        Format lint results into a human-readable string.
        
        Args:
            lint_result (Dict[str, Any]): The lint result dictionary.
            language (Optional[str]): Language identifier to specify which formatter to use.
                                     If not provided, will try to infer from lint_result.
            
        Returns:
            str: A formatted string representation of the lint results.
        """
        # Try to infer language/framework from lint_result
        if language is None:
            if 'language' in lint_result:
                language = lint_result['language']
            elif 'framework' in lint_result:
                language = lint_result['framework']
            elif 'file_type' in lint_result:
                language = lint_result['file_type']
            else:
                # Default to Python as a fallback
                language = 'python'
        
        linter = cls.create_linter(language=language)
        return linter.format_lint_result(lint_result)

def lint_file(file_path: str, fix: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to lint a single file.
    
    Args:
        file_path (str): Path to the file to lint.
        fix (bool): Whether to automatically fix fixable issues.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing lint results.
    """
    return LinterFactory.lint_file(file_path, fix=fix, verbose=verbose)

def lint_project(project_path: str, language: Optional[str] = None, fix: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to lint a project.
    
    Args:
        project_path (str): Path to the project directory.
        language (Optional[str]): Language identifier to specify which linter to use.
        fix (bool): Whether to automatically fix fixable issues.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing lint results.
    """
    return LinterFactory.lint_project(project_path, language=language, fix=fix, verbose=verbose)

def format_lint_result(lint_result: Dict[str, Any], language: Optional[str] = None) -> str:
    """
    Format lint results into a human-readable string.
    
    Args:
        lint_result (Dict): The lint result dictionary.
        language (Optional[str]): Language identifier to specify which formatter to use.
        
    Returns:
        str: A formatted string representation of the lint results.
    """
    return LinterFactory.format_lint_result(lint_result, language=language) 