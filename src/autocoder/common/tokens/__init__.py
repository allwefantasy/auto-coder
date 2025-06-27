"""
Tokens 模块 - 高效统计文件和目录中的 token 数量

提供了简单易用的接口，支持正则过滤和智能文件类型识别。
"""

from .models import TokenResult, DirectoryTokenResult
from .counter import TokenCounter
from .file_detector import FileTypeDetector
from .filters import FileFilter


def count_file_tokens(file_path: str) -> TokenResult:
    """
    统计单个文件的 token 数量
    
    Args:
        file_path: 文件路径
        
    Returns:
        TokenResult: 统计结果
    """
    counter = TokenCounter()
    return counter.count_file(file_path)


def count_directory_tokens(
    dir_path: str, 
    pattern: str = None,
    exclude_pattern: str = None,
    recursive: bool = True
) -> DirectoryTokenResult:
    """
    统计目录中所有文件的 token 数量
    
    Args:
        dir_path: 目录路径
        pattern: 文件名匹配模式（正则表达式）
        exclude_pattern: 排除的文件名模式（正则表达式）
        recursive: 是否递归处理子目录
        
    Returns:
        DirectoryTokenResult: 目录统计结果
    """
    counter = TokenCounter()
    return counter.count_directory(
        dir_path=dir_path,
        pattern=pattern,
        exclude_pattern=exclude_pattern,
        recursive=recursive
    )


def count_string_tokens(text: str) -> int:
    """
    统计字符串的 token 数量
    
    Args:
        text: 要统计的字符串内容
        
    Returns:
        int: token 数量
    """
    counter = TokenCounter()
    return counter.count_string_tokens(text)


__all__ = [
    'TokenResult',
    'DirectoryTokenResult',
    'TokenCounter',
    'FileTypeDetector',
    'FileFilter',
    'count_file_tokens',
    'count_directory_tokens',
    'count_string_tokens',
]
