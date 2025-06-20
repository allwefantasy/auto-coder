"""
Auto-Coder CLI 模块

提供命令行接口，允许用户通过终端使用 Auto-Coder 的核心功能。
"""

from .main import AutoCoderCLI
from .options import CLIOptions, CLIResult

# 导出main函数作为入口点
def main():
    """CLI主入口点函数"""
    return AutoCoderCLI.main()

__all__ = ["AutoCoderCLI", "CLIOptions", "CLIResult", "main"]
