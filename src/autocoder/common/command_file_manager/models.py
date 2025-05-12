"""
命令管理模块的数据模型

定义了表示命令文件、命令内容和操作结果的数据类。
"""

import os
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


@dataclass
class CommandFile:
    """表示单个命令文件的信息"""
    file_path: str
    file_name: str
    content: str
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CommandFile':
        """从字典创建CommandFile对象"""
        return cls(
            file_path=data['file_path'],
            file_name=data['file_name'],
            content=data['content']
        )
    
    def to_dict(self) -> Dict:
        """将CommandFile对象转换为字典"""
        return {
            'file_path': self.file_path,
            'file_name': self.file_name,
            'content': self.content
        }


@dataclass
class JinjaVariable:
    """表示从命令文件中提取的Jinja2变量"""
    name: str
    default_value: Optional[str] = None
    description: Optional[str] = None
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'JinjaVariable':
        """从字典创建JinjaVariable对象"""
        return cls(
            name=data['name'],
            default_value=data.get('default_value'),
            description=data.get('description')
        )
    
    def to_dict(self) -> Dict:
        """将JinjaVariable对象转换为字典"""
        return {
            'name': self.name,
            'default_value': self.default_value,
            'description': self.description
        }


@dataclass
class CommandFileAnalysisResult:
    """表示命令文件分析的结果"""
    file_path: str
    file_name: str
    variables: List[JinjaVariable] = field(default_factory=list)
    raw_variables: Set[str] = field(default_factory=set)
    
    def add_variable(self, variable: JinjaVariable) -> None:
        """添加一个变量"""
        self.variables.append(variable)
        self.raw_variables.add(variable.name)
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CommandFileAnalysisResult':
        """从字典创建CommandFileAnalysisResult对象"""
        result = cls(
            file_path=data['file_path'],
            file_name=data['file_name'],
            raw_variables=set(data.get('raw_variables', []))
        )
        
        for var_data in data.get('variables', []):
            result.variables.append(JinjaVariable.from_dict(var_data))
        
        return result
    
    def to_dict(self) -> Dict:
        """将CommandFileAnalysisResult对象转换为字典"""
        return {
            'file_path': self.file_path,
            'file_name': self.file_name,
            'variables': [var.to_dict() for var in self.variables],
            'raw_variables': list(self.raw_variables)
        }


@dataclass
class ListCommandsResult:
    """表示列出命令文件的结果"""
    success: bool
    command_files: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    
    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def add_error(self, path: str, error_message: str) -> None:
        """添加错误信息"""
        self.errors[path] = error_message
        self.success = False
    
    def add_command_file(self, file_path: str) -> None:
        """添加命令文件路径"""
        self.command_files.append(file_path)
