"""
目录映射器 - 处理URL到目录上下文的映射
"""

import os
import sys
from typing import List, Dict, Any
from loguru import logger as global_logger

class DirectoryMapper:
    """
    DirectoryMapper负责将文件URL映射到对应的目录结构，
    用于确定需要生成active.md文件的目录。
    """
    
    def __init__(self):
        """
        初始化目录映射器
        """
        # 创建专用的 logger 实例
        self.logger = global_logger.bind(name="DirectoryMapper")
    
    def map_directories(self, project_path: str, changed_urls: List[str], 
                        current_urls: List[str] = None) -> List[Dict[str, Any]]:
        """
        映射URLs到目录上下文
        
        Args:
            project_path: 项目根目录
            changed_urls: 变更的文件路径列表
            current_urls: 当前相关的文件路径列表
        
        Returns:
            List[Dict]: 目录上下文列表，每个上下文包含目录路径和相关文件信息
        """
        # 1. 提取所有相关的目录
        directories = set()
        for url in changed_urls:
            try:
                directories.add(os.path.dirname(url))
            except Exception as e:
                self.logger.error(f"Error extracting directory from {url}: {e}")
        
        # 2. 创建目录上下文字典
        directory_contexts = []
        for directory in directories:
            try:
                # 收集该目录下的所有变更文件
                dir_changed_files = [url for url in changed_urls if os.path.dirname(url) == directory]
                
                # 如果有current_urls，也收集
                dir_current_files = []
                if current_urls:
                    dir_current_files = [url for url in current_urls if os.path.dirname(url) == directory]
                    
                # 只有当目录中有变更文件时才添加上下文
                if dir_changed_files:
                    context = {
                        'directory_path': directory,
                        'changed_files': [{'path': url} for url in dir_changed_files],
                        'current_files': [{'path': url} for url in dir_current_files]
                    }
                    directory_contexts.append(context)
            except Exception as e:
                self.logger.error(f"Error processing directory {directory}: {e}")
        
        return directory_contexts 