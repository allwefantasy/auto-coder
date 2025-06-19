"""
Auto-Coder CLI 模块

提供命令行接口，允许用户通过终端使用 Auto-Coder 的核心功能。
"""

from .main import AutoCoderCLI
from .options import CLIOptions, CLIResult

__all__ = ["AutoCoderCLI", "CLIOptions", "CLIResult"]
