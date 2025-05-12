"""
命令管理模块

该模块提供了一种机制来管理和分析 .autocodercommands 目录中的命令文件。
主要功能包括：
1. 列出命令目录中的所有命令文件
2. 读取指定的命令文件内容
3. 分析命令文件，提取其中的Jinja2变量
4. 提供简单直观的API，便于集成到现有的项目中
"""

from autocoder.common.command_file_manager.models import (
    CommandFile, JinjaVariable, CommandFileAnalysisResult, ListCommandsResult
)
from autocoder.common.command_file_manager.manager import CommandManager
from autocoder.common.command_file_manager.utils import (
    extract_jinja2_variables, extract_jinja2_variables_with_metadata,
    analyze_command_file, is_command_file
)

__all__ = [
    'CommandFile', 'JinjaVariable', 'CommandFileAnalysisResult', 'ListCommandsResult',
    'CommandManager', 'extract_jinja2_variables', 'extract_jinja2_variables_with_metadata',
    'analyze_command_file', 'is_command_file'
]
