"""
活动上下文标题模块 - 负责生成和更新 active.md 文件的标题部分
"""

import os
import re
from typing import Dict, Any, Optional
from loguru import logger as global_logger


class ActiveHeader:
    """
    负责处理 active.md 文件的标题部分
    """
    
    def __init__(self):
        """初始化活动标题处理器"""
        self.logger = global_logger.bind(name="ActiveHeader")
    
    def generate_header(self, context: Dict[str, Any]) -> str:
        """
        生成活动上下文标题
        
        Args:
            context: 目录上下文字典
            
        Returns:
            str: 生成的标题内容
        """
        try:
            # 安全获取目录名称
            dir_name = os.path.basename(context.get('directory_path', '未知目录'))
            header = f"# 活动上下文 - {dir_name}\n\n"
            
            self.logger.debug(f"Generated header for directory: {dir_name}")
            return header
        except Exception as e:
            self.logger.error(f"Error generating header: {e}")
            return "# 活动上下文 - 未知目录\n\n"
    
    def extract_header(self, content: str) -> str:
        """
        从现有内容中提取标题部分
        
        Args:
            content: 现有文件内容
            
        Returns:
            str: 提取的标题部分
        """
        try:
            # 提取标题部分（到第一个二级标题之前）
            header_match = re.search(r'^(.*?)(?=\n## )', content, re.DOTALL)
            if header_match:
                header = header_match.group(1).strip() + "\n\n"
                self.logger.debug("Successfully extracted header from existing content")
                return header
            else:
                self.logger.warning("No header found in existing content, using default")
                return "# 活动上下文\n\n"
        except Exception as e:
            self.logger.error(f"Error extracting header: {e}")
            return "# 活动上下文\n\n"
    
    def update_header(self, context: Dict[str, Any], existing_header: str) -> str:
        """
        更新现有的标题部分
        
        Args:
            context: 目录上下文字典
            existing_header: 现有的标题内容
            
        Returns:
            str: 更新后的标题内容
        """
        try:
            # 如果现有标题包含正确的目录名，则保留；否则更新
            dir_name = os.path.basename(context.get('directory_path', '未知目录'))
            
            if dir_name in existing_header and existing_header.strip():
                self.logger.debug(f"Keeping existing header for directory: {dir_name}")
                return existing_header
            else:
                self.logger.debug(f"Updating header for directory: {dir_name}")
                return self.generate_header(context)
        except Exception as e:
            self.logger.error(f"Error updating header: {e}")
            return self.generate_header(context) 