"""
文件变更管理模块的数据模型

定义了表示文件变更、变更记录和操作结果的数据类。
"""

import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Union


@dataclass
class FileChange:
    """表示单个文件的变更信息"""
    file_path: str
    content: str
    is_new: bool = False
    is_deletion: bool = False
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'FileChange':
        """从字典创建FileChange对象"""
        return cls(
            file_path=data['file_path'],
            content=data['content'],
            is_new=data.get('is_new', False),
            is_deletion=data.get('is_deletion', False)
        )
    
    def to_dict(self) -> Dict:
        """将FileChange对象转换为字典"""
        return {
            'file_path': self.file_path,
            'content': self.content,
            'is_new': self.is_new,
            'is_deletion': self.is_deletion
        }


@dataclass
class ChangeRecord:
    """表示一条变更记录，包含变更的元数据和详细信息"""
    change_id: str
    timestamp: float
    file_path: str
    backup_id: Optional[str]
    is_new: bool = False
    is_deletion: bool = False
    group_id: Optional[str] = None
    
    @classmethod
    def create(cls, file_path: str, backup_id: Optional[str], 
               is_new: bool = False, is_deletion: bool = False, 
               group_id: Optional[str] = None) -> 'ChangeRecord':
        """创建一个新的变更记录"""
        return cls(
            change_id=str(uuid.uuid4()),
            timestamp=datetime.now().timestamp(),
            file_path=file_path,
            backup_id=backup_id,
            is_new=is_new,
            is_deletion=is_deletion,
            group_id=group_id
        )
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'ChangeRecord':
        """从字典创建ChangeRecord对象"""
        return cls(
            change_id=data['change_id'],
            timestamp=data['timestamp'],
            file_path=data['file_path'],
            backup_id=data.get('backup_id'),
            is_new=data.get('is_new', False),
            is_deletion=data.get('is_deletion', False),
            group_id=data.get('group_id')
        )
    
    def to_dict(self) -> Dict:
        """将ChangeRecord对象转换为字典"""
        return {
            'change_id': self.change_id,
            'timestamp': self.timestamp,
            'file_path': self.file_path,
            'backup_id': self.backup_id,
            'is_new': self.is_new,
            'is_deletion': self.is_deletion,
            'group_id': self.group_id
        }


@dataclass
class DiffResult:
    """表示文件差异比较的结果"""
    file_path: str
    old_content: Optional[str]
    new_content: str
    is_new: bool = False
    is_deletion: bool = False
    
    def get_diff_summary(self) -> str:
        """获取差异摘要"""
        if self.is_new:
            return f"新文件: {self.file_path}"
        elif self.is_deletion:
            return f"删除文件: {self.file_path}"
        else:
            old_lines = 0 if self.old_content is None else len(self.old_content.splitlines())
            new_lines = len(self.new_content.splitlines())
            return f"修改文件: {self.file_path} (原始行数: {old_lines}, 新行数: {new_lines})"


@dataclass
class ApplyResult:
    """表示变更应用的结果"""
    success: bool
    change_ids: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    
    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def add_error(self, file_path: str, error_message: str) -> None:
        """添加错误信息"""
        self.errors[file_path] = error_message
        self.success = False
    
    def add_change_id(self, change_id: str) -> None:
        """添加成功应用的变更ID"""
        self.change_ids.append(change_id)


@dataclass
class UndoResult:
    """表示变更撤销的结果"""
    success: bool
    restored_files: List[str] = field(default_factory=list)
    errors: Dict[str, str] = field(default_factory=dict)
    
    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0
    
    def add_error(self, file_path: str, error_message: str) -> None:
        """添加错误信息"""
        self.errors[file_path] = error_message
        self.success = False
    
    def add_restored_file(self, file_path: str) -> None:
        """添加成功恢复的文件"""
        self.restored_files.append(file_path)
