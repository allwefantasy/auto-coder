"""
Module providing a factory for creating language-specific compilers.
"""

import os
from typing import Optional, Dict, Any, List

from autocoder.compilers.base_compiler import BaseCompiler
from autocoder.compilers.reactjs_compiler import ReactJSCompiler
from autocoder.compilers.vue_compiler import VueCompiler
from autocoder.compilers.python_compiler import PythonCompiler
from autocoder.compilers.java_compiler import JavaCompiler
from autocoder.compilers.provided_compiler import ProvidedCompiler

class CompilerFactory:
    """
    Factory class for creating appropriate compiler instances based on file type or language.
    """
    
    @classmethod
    def create_compiler(cls, language: Optional[str] = None, 
                        file_path: Optional[str] = None, 
                        config_path: Optional[str] = None,
                        verbose: bool = False, **kwargs) -> Optional[BaseCompiler]:
        """
        Create and return an appropriate compiler instance based on language or file path.
        
        Args:
            language (Optional[str]): Language identifier ('python', 'java', 'javascript', 'typescript', etc.).
            file_path (Optional[str]): Path to a file to infer the language from.
            config_path (Optional[str]): Path to a config file to use for the compiler.
            verbose (bool): Whether to enable verbose output in the compiler.
            
        Returns:
            BaseCompiler: An instance of a compiler appropriate for the language.
            
        Raises:
            ValueError: If no language could be determined or if the language is not supported.
        """
        if language is None and file_path is None:
            raise ValueError("Either language or file_path must be provided")
        
        # If language is not provided, try to infer from file path
        if language is None and file_path is not None:
            language = cls._detect_language_from_file(file_path)
        
        # Map language to compiler class
        compiler_map = {
            'python': PythonCompiler,
            'java': JavaCompiler,
            'javascript': ReactJSCompiler,
            'typescript': ReactJSCompiler,
            'js': ReactJSCompiler,
            'ts': ReactJSCompiler,
            'jsx': ReactJSCompiler,
            'tsx': ReactJSCompiler,
            'react': ReactJSCompiler,
            'reactjs': ReactJSCompiler,
            'vue': VueCompiler,
            'provided': ProvidedCompiler,
        }
        
        compiler_class = compiler_map.get(language.lower() if language else None)
        
        if compiler_class is None:
            return None
        
        return compiler_class(verbose=verbose, config_path=config_path, **kwargs)
    
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
            '.java': 'java',
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
        return ['python', 'java', 'javascript', 'typescript', 'react', 'vue']
    
    @classmethod
    def compile_file(cls, file_path: str, verbose: bool = False) -> Dict[str, Any]:
        """
        Compile a single file using the appropriate compiler.
        
        Args:
            file_path (str): Path to the file to compile.
            verbose (bool): Whether to enable verbose output.
            
        Returns:
            Dict[str, Any]: Compilation results.
        """
        compiler = cls.create_compiler(file_path=file_path, verbose=verbose)
        if compiler is None:
            return None
        return compiler.compile_file(file_path)
    
    @classmethod
    def compile_project(cls, project_path: str, language: Optional[str] = None, verbose: bool = False) -> Dict[str, Any]:
        """
        Compile a project using the appropriate compiler.
        
        Args:
            project_path (str): Path to the project directory.
            language (Optional[str]): Language identifier to specify which compiler to use.
                                     If not provided, will try to auto-detect.
            verbose (bool): Whether to enable verbose output.
            
        Returns:
            Dict[str, Any]: Compilation results.
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
            # Check for pom.xml or build.gradle (Java)
            elif (os.path.exists(os.path.join(project_path, 'pom.xml')) or
                  os.path.exists(os.path.join(project_path, 'build.gradle'))):
                language = 'java'
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
                relevant_extensions = {'.py', '.java', '.js', '.ts', '.jsx', '.tsx', '.vue'}
                most_common = None
                max_count = 0
                
                for ext, count in language_counts.items():
                    if ext in relevant_extensions and count > max_count:
                        most_common = ext
                        max_count = count
                
                if most_common is None:
                    raise ValueError(f"Could not detect project language in {project_path}")
                
                language = cls._detect_language_from_file(f"dummy{most_common}")
        
        compiler = cls.create_compiler(language=language, verbose=verbose)
        if compiler is None:
            return None
        return compiler.compile_project(project_path)
    
    @classmethod
    def format_compile_result(cls, compile_result: Dict[str, Any], language: Optional[str] = None) -> str:
        """
        Format compilation results into a human-readable string.
        
        Args:
            compile_result (Dict[str, Any]): The compilation result dictionary.
            language (Optional[str]): Language identifier to specify which formatter to use.
                                     If not provided, will try to infer from compile_result.
            
        Returns:
            str: A formatted string representation of the compilation results.
        """
        # Try to infer language/framework from compile_result
        if language is None:
            if 'language' in compile_result:
                language = compile_result['language']
            elif 'framework' in compile_result:
                language = compile_result['framework']
            elif 'file_type' in compile_result:
                language = compile_result['file_type']
            else:
                # Default to Python as a fallback
                language = 'python'
        
        compiler = cls.create_compiler(language=language)
        return compiler.format_compile_result(compile_result)

def compile_file(file_path: str, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to compile a single file.
    
    Args:
        file_path (str): Path to the file to compile.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing compilation results.
    """
    return CompilerFactory.compile_file(file_path, verbose=verbose)

def compile_project(project_path: str, language: Optional[str] = None, verbose: bool = False) -> Dict[str, Any]:
    """
    Utility function to compile a project.
    
    Args:
        project_path (str): Path to the project directory.
        language (Optional[str]): Language identifier to specify which compiler to use.
        verbose (bool): Whether to display verbose output.
        
    Returns:
        Dict[str, Any]: A dictionary containing compilation results.
    """
    return CompilerFactory.compile_project(project_path, language=language, verbose=verbose)

def format_compile_result(compile_result: Dict[str, Any], language: Optional[str] = None) -> str:
    """
    Utility function to format compilation results into a human-readable string.
    
    Args:
        compile_result (Dict[str, Any]): The compilation result dictionary.
        language (Optional[str]): Language identifier to specify which formatter to use.
        
    Returns:
        str: A formatted string representation of the compilation results.
    """
    return CompilerFactory.format_compile_result(compile_result, language=language) 