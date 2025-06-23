import os
import re
from pathlib import Path
from typing import List, Optional, Tuple


class FileFilter:
    """文件过滤器，用于过滤需要统计的文件"""
    
    def __init__(self, 
                 patterns: List[str] = None, 
                 exclude_patterns: List[str] = None,
                 min_size: int = None, 
                 max_size: int = None,
                 only_text_files: bool = True):
        """
        初始化文件过滤器
        
        Args:
            patterns: 包含的文件名模式（正则表达式）
            exclude_patterns: 排除的文件名模式（正则表达式）
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
            only_text_files: 是否只包含文本文件
        """
        self.patterns = []
        self.exclude_patterns = []
        self.min_size = min_size
        self.max_size = max_size
        self.only_text_files = only_text_files
        
        if patterns:
            for pattern in patterns:
                self.add_pattern(pattern)
                
        if exclude_patterns:
            for pattern in exclude_patterns:
                self.add_exclude_pattern(pattern)
    
    def add_pattern(self, pattern: str) -> None:
        """
        添加包含的文件名模式
        
        Args:
            pattern: 正则表达式模式
        """
        try:
            self.patterns.append(re.compile(pattern))
        except re.error:
            raise ValueError(f"Invalid regex pattern: {pattern}")
    
    def add_exclude_pattern(self, pattern: str) -> None:
        """
        添加排除的文件名模式
        
        Args:
            pattern: 正则表达式模式
        """
        try:
            self.exclude_patterns.append(re.compile(pattern))
        except re.error:
            raise ValueError(f"Invalid regex pattern: {pattern}")
    
    def set_size_range(self, min_size: Optional[int] = None, max_size: Optional[int] = None) -> None:
        """
        设置文件大小范围
        
        Args:
            min_size: 最小文件大小（字节）
            max_size: 最大文件大小（字节）
        """
        self.min_size = min_size
        self.max_size = max_size
    
    def matches(self, file_path: str) -> bool:
        """
        检查文件是否匹配过滤条件
        
        Args:
            file_path: 文件路径
            
        Returns:
            bool: 是否匹配
        """
        # 检查文件是否存在
        if not os.path.isfile(file_path):
            return False
            
        # 检查文件大小
        if self.min_size is not None or self.max_size is not None:
            size = os.path.getsize(file_path)
            if self.min_size is not None and size < self.min_size:
                return False
            if self.max_size is not None and size > self.max_size:
                return False
        
        # 检查是否匹配排除模式
        for pattern in self.exclude_patterns:
            if pattern.search(file_path):
                return False
        
        # 如果没有包含模式，则默认匹配所有文件
        if not self.patterns:
            return True
            
        # 检查是否匹配包含模式
        for pattern in self.patterns:
            if pattern.search(file_path):
                return True
                
        return False
