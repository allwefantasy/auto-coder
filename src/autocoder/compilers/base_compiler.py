"""
Module for code compilation capabilities across multiple programming languages.
This module provides a base abstract class for various language-specific compilers.
"""

import os
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional,Union
from autocoder.compilers.models import ProjectCompilationResult,FileCompilationResult

class BaseCompiler(ABC):
    """
    Base abstract class for all language-specific compilers.
    """
    
    def __init__(self, verbose: bool = False):
        """
        Initialize the base compiler.
        
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
    def compile_file(self, file_path: str,target_compiler_name:Optional[str] = None) -> FileCompilationResult:
        """
        Compile a single file.
        
        Args:
            file_path (str): Path to the file to compile.
            
        Returns:
            FileCompilationResult: Compilation results.
        """
        pass
    
    @abstractmethod
    def compile_project(self, project_path: str,target_compiler_name:Optional[str] = None) -> ProjectCompilationResult:
        """
        Compile an entire project.
        
        Args:
            project_path (str): Path to the project directory.
            
        Returns:
            ProjectCompilationResult: Compilation results.
        """
        pass
    
    @abstractmethod
    def format_compile_result(self, compile_result: Union[ProjectCompilationResult, FileCompilationResult]) -> str:
        """
        Format compilation results into a human-readable string.
        
        Args:
            compile_result (Union[ProjectCompilationResult, FileCompilationResult]): The compilation result.
            
        Returns:
            str: A formatted string representation of the compilation results.
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
        Check if a file is supported by this compiler.
        
        Args:
            file_path (str): Path to the file.
            
        Returns:
            bool: True if the file is supported, False otherwise.
        """
        return self.get_file_extension(file_path) in self.get_supported_extensions()
    
    @abstractmethod
    def get_supported_extensions(self) -> List[str]:
        """
        Get the list of file extensions supported by this compiler.
        
        Returns:
            List[str]: List of supported file extensions (lowercase, with dot).
        """
        pass 