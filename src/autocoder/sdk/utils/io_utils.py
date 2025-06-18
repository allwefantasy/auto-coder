




















"""
Auto-Coder SDK IO工具

提供输入输出相关的工具函数。
"""

import sys
import os
from pathlib import Path
from typing import Optional


def read_stdin() -> str:
    """
    从标准输入读取内容
    
    Returns:
        str: 读取的内容
    """
    try:
        if sys.stdin.isatty():
            # 如果是交互式终端，返回空字符串
            return ""
        else:
            # 从管道或重定向读取
            return sys.stdin.read().strip()
    except Exception:
        return ""


def write_stdout(content: str) -> None:
    """
    写入标准输出
    
    Args:
        content: 要写入的内容
    """
    try:
        sys.stdout.write(content)
        sys.stdout.flush()
    except Exception:
        pass


def write_stderr(content: str) -> None:
    """
    写入标准错误输出
    
    Args:
        content: 要写入的内容
    """
    try:
        sys.stderr.write(content)
        sys.stderr.flush()
    except Exception:
        pass


def ensure_directory(dir_path: str) -> bool:
    """
    确保目录存在，如果不存在则创建
    
    Args:
        dir_path: 目录路径
        
    Returns:
        bool: 是否成功创建或已存在
    """
    try:
        Path(dir_path).mkdir(parents=True, exist_ok=True)
        return True
    except Exception:
        return False


def read_file_safe(file_path: str, encoding: str = "utf-8") -> Optional[str]:
    """
    安全读取文件内容
    
    Args:
        file_path: 文件路径
        encoding: 编码格式
        
    Returns:
        Optional[str]: 文件内容，如果读取失败返回None
    """
    try:
        with open(file_path, 'r', encoding=encoding) as f:
            return f.read()
    except Exception:
        return None


def write_file_safe(file_path: str, content: str, encoding: str = "utf-8") -> bool:
    """
    安全写入文件内容
    
    Args:
        file_path: 文件路径
        content: 要写入的内容
        encoding: 编码格式
        
    Returns:
        bool: 是否写入成功
    """
    try:
        # 确保目录存在
        ensure_directory(os.path.dirname(file_path))
        
        with open(file_path, 'w', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception:
        return False


def append_file_safe(file_path: str, content: str, encoding: str = "utf-8") -> bool:
    """
    安全追加文件内容
    
    Args:
        file_path: 文件路径
        content: 要追加的内容
        encoding: 编码格式
        
    Returns:
        bool: 是否追加成功
    """
    try:
        # 确保目录存在
        ensure_directory(os.path.dirname(file_path))
        
        with open(file_path, 'a', encoding=encoding) as f:
            f.write(content)
        return True
    except Exception:
        return False


def file_exists(file_path: str) -> bool:
    """
    检查文件是否存在
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 文件是否存在
    """
    return Path(file_path).exists() and Path(file_path).is_file()


def directory_exists(dir_path: str) -> bool:
    """
    检查目录是否存在
    
    Args:
        dir_path: 目录路径
        
    Returns:
        bool: 目录是否存在
    """
    return Path(dir_path).exists() and Path(dir_path).is_dir()


def get_file_size(file_path: str) -> Optional[int]:
    """
    获取文件大小
    
    Args:
        file_path: 文件路径
        
    Returns:
        Optional[int]: 文件大小（字节），如果文件不存在返回None
    """
    try:
        return Path(file_path).stat().st_size
    except Exception:
        return None


def list_files_in_directory(dir_path: str, pattern: str = "*") -> list:
    """
    列出目录中的文件
    
    Args:
        dir_path: 目录路径
        pattern: 文件名模式
        
    Returns:
        list: 文件路径列表
    """
    try:
        dir_path_obj = Path(dir_path)
        if not dir_path_obj.exists() or not dir_path_obj.is_dir():
            return []
        
        return [str(path) for path in dir_path_obj.glob(pattern) if path.is_file()]
    except Exception:
        return []


def create_temp_file(content: str = "", suffix: str = ".tmp") -> Optional[str]:
    """
    创建临时文件
    
    Args:
        content: 文件内容
        suffix: 文件后缀
        
    Returns:
        Optional[str]: 临时文件路径，如果创建失败返回None
    """
    try:
        import tempfile
        
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(content)
            return f.name
    except Exception:
        return None


def delete_file_safe(file_path: str) -> bool:
    """
    安全删除文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        bool: 是否删除成功
    """
    try:
        Path(file_path).unlink()
        return True
    except Exception:
        return False


def copy_file_safe(src_path: str, dst_path: str) -> bool:
    """
    安全复制文件
    
    Args:
        src_path: 源文件路径
        dst_path: 目标文件路径
        
    Returns:
        bool: 是否复制成功
    """
    try:
        import shutil
        
        # 确保目标目录存在
        ensure_directory(os.path.dirname(dst_path))
        
        shutil.copy2(src_path, dst_path)
        return True
    except Exception:
        return False




















