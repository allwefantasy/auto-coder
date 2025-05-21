"""
命令管理器

整个模块的主入口，提供高层次的API接口，用于列出、读取和分析命令文件。
"""

import os
import logging
from typing import Dict, List, Optional, Set, Tuple

from autocoder.common.command_file_manager.models import (
    CommandFile, JinjaVariable, CommandFileAnalysisResult, ListCommandsResult
)
from autocoder.common.command_file_manager.utils import (
    extract_jinja2_variables, extract_jinja2_variables_with_metadata,
    analyze_command_file, is_command_file
)

logger = logging.getLogger(__name__)


class CommandManager:
    """命令管理器，提供高层次的API接口"""
    
    def __init__(self, commands_dir: str):
        """
        初始化命令管理器
        
        Args:
            commands_dir: 命令文件目录路径
        """
        self.commands_dir = os.path.abspath(commands_dir)
        
        # 确保目录存在
        if not os.path.exists(self.commands_dir):
            logger.warning(f"命令目录不存在: {self.commands_dir}")
            os.makedirs(self.commands_dir, exist_ok=True)
            logger.info(f"已创建命令目录: {self.commands_dir}")
    
    def list_command_files(self, recursive: bool = True) -> ListCommandsResult:
        """
        列出命令目录中的所有命令文件
        
        Args:
            recursive: 是否递归搜索子目录
            
        Returns:
            ListCommandsResult: 列出结果
        """
        result = ListCommandsResult(success=True)
        
        try:
            if recursive:
                for root, _, files in os.walk(self.commands_dir):
                    for file in files:
                        if is_command_file(file):
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, self.commands_dir)
                            result.add_command_file(rel_path)
            else:
                for item in os.listdir(self.commands_dir):
                    item_path = os.path.join(self.commands_dir, item)
                    if os.path.isfile(item_path) and is_command_file(item):
                        result.add_command_file(item)
        except Exception as e:
            logger.error(f"列出命令文件时出错: {str(e)}")
            result.add_error(self.commands_dir, f"列出命令文件时出错: {str(e)}")
        
        return result
    
    def read_command_file(self, file_name: str) -> Optional[CommandFile]:
        """
        读取指定的命令文件
        
        Args:
            file_name: 命令文件名或相对路径
            
        Returns:
            Optional[CommandFile]: 命令文件对象，如果文件不存在则返回None
        """
        file_path = os.path.join(self.commands_dir, file_name)
        
        if not os.path.isfile(file_path):
            logger.warning(f"命令文件不存在: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            return CommandFile(
                file_path=file_path,
                file_name=os.path.basename(file_path),
                content=content
            )
        except Exception as e:
            logger.error(f"读取命令文件时出错: {str(e)}")
            return None
    
    def analyze_command_file(self, file_name: str) -> Optional[CommandFileAnalysisResult]:
        """
        分析指定的命令文件，提取其中的Jinja2变量
        
        Args:
            file_name: 命令文件名或相对路径
            
        Returns:
            Optional[CommandFileAnalysisResult]: 分析结果，如果文件不存在则返回None
        """
        command_file = self.read_command_file(file_name)
        if command_file is None:
            return None
        
        try:
            return analyze_command_file(command_file.file_path, command_file.content)
        except Exception as e:
            logger.error(f"分析命令文件时出错: {str(e)}")
            return None
    
    def get_all_variables(self, recursive: bool = False) -> Dict[str, Set[str]]:
        """
        获取所有命令文件中的变量
        
        Args:
            recursive: 是否递归搜索子目录
            
        Returns:
            Dict[str, Set[str]]: 文件路径到变量集合的映射
        """
        result: Dict[str, Set[str]] = {}
        
        list_result = self.list_command_files(recursive)
        if not list_result.success:
            logger.error("获取命令文件列表失败")
            return result
        
        for file_name in list_result.command_files:
            command_file = self.read_command_file(file_name)
            if command_file is None:
                continue
            
            try:
                variables = extract_jinja2_variables(command_file.content)
                result[file_name] = variables
            except Exception as e:
                logger.error(f"提取文件 {file_name} 的变量时出错: {str(e)}")
        
        return result
    
    def get_command_file_path(self, file_name: str) -> str:
        """
        获取命令文件的完整路径
        
        Args:
            file_name: 命令文件名或相对路径
            
        Returns:
            str: 命令文件的完整路径
        """
        return os.path.join(self.commands_dir, file_name)
    
    def _get_absolute_path(self, file_path: str) -> str:
        """
        获取文件的绝对路径
        
        Args:
            file_path: 文件相对路径或绝对路径
            
        Returns:
            str: 文件的绝对路径
        """
        if os.path.isabs(file_path):
            return file_path
        else:
            return os.path.join(self.commands_dir, file_path)
