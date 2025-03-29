"""
Package for compiling code across multiple programming languages.
This package provides functionality for compiling and checking code in Python, Java, ReactJS, and Vue.js.
"""

from autocoder.compilers.compiler_factory import (
    CompilerFactory,
    compile_file,
    compile_project,
    format_compile_result
)

from autocoder.compilers.models import (
    CompilationError,
    CompilationErrorSeverity,
    CompilationErrorPosition,
    FileCompilationResult,
    ProjectCompilationResult
)

from autocoder.compilers.base_compiler import BaseCompiler
from autocoder.compilers.python_compiler import PythonCompiler
from autocoder.compilers.java_compiler import JavaCompiler
from autocoder.compilers.reactjs_compiler import ReactJSCompiler
from autocoder.compilers.vue_compiler import VueCompiler
from autocoder.compilers.provided_compiler import ProvidedCompiler, compile_with_provided_config
from autocoder.compilers.compiler_config_manager import CompilerConfigManager, get_compiler_config_manager
from autocoder.compilers.compiler_config_api import CompilerConfigAPI, get_compiler_config_api

__all__ = [
    'CompilerFactory',
    'compile_file',
    'compile_project',
    'format_compile_result',
    'CompilationError',
    'CompilationErrorSeverity',
    'CompilationErrorPosition',
    'FileCompilationResult',
    'ProjectCompilationResult',
    'BaseCompiler',
    'PythonCompiler',
    'JavaCompiler',
    'ReactJSCompiler',
    'VueCompiler',
    'ProvidedCompiler',
    'compile_with_provided_config',
    'CompilerConfigManager',
    'get_compiler_config_manager',
    'CompilerConfigAPI',
    'get_compiler_config_api'
] 