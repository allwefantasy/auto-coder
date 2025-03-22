"""
Module for code linting capabilities across multiple programming languages.
This module provides a base abstract class for various language-specific linters.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional

class BaseLinter(ABC):
    """
    Base abstract class for all language-specific linters.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the base linter.
        
        Args:
            verbose (bool): Whether to display verbose output.
        """
        self.verbose = verbose
    
    @abstractmethod
    def _check_dependencies(self) -> bool:
        """
        Check if required dependencies are installed.
        
        Returns:
            bool: True if all dependencies are available, False otherwise.
        """
        pass
    
    @abstractmethod
    def lint_file(self, file_path: str, fix: bool = False) -> Dict[str, Any]:
        """
        Lint a single file.
        
        Args:
            file_path (str): Path to the file to lint.
            fix (bool): Whether to automatically fix fixable issues.
            
        Returns:
            Dict[str, Any]: Lint results.
        """
        pass
    
    @abstractmethod
    def lint_project(self, project_path: str, fix: bool = False) -> Dict[str, Any]:
        """
        Lint an entire project.
        
        Args:
            project_path (str): Path to the project directory.
            fix (bool): Whether to automatically fix fixable issues.
            
        Returns:
            Dict[str, Any]: Lint results.
        """
        pass
    
    @abstractmethod
    def format_lint_result(self, lint_result: Dict[str, Any]) -> str:
        """
        Format lint results into a human-readable string.
        
        Args:
            lint_result (Dict[str, Any]): The lint result dictionary.
            
        Returns:
            str: A formatted string representation of the lint results.
        """
        pass
    
    def get_file_extension(self, file_path: str) -> str:
        """
        Get the file extension from a file path.
        
        Args:
            file_path (str): Path to the file.
            
        Returns:
            str: The file extension (lowercase, with dot).
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower()
    
    def is_supported_file(self, file_path: str) -> bool:
        """
        Check if a file is supported by this linter.
        
        Args:
            file_path (str): Path to the file.
            
        Returns:
            bool: True if the file is supported, False otherwise.
        """
        return self.get_file_extension(file_path) in self.get_supported_extensions()
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get the list of file extensions supported by this linter.
        
        Returns:
            List[str]: List of supported file extensions (lowercase, with dot).
        """
        pass 