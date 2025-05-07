"""
文件变更管理模块

该模块提供了一种可靠的机制来应用、记录和撤销对项目文件的修改。
主要功能包括：
1. 将影子系统中的文件变更安全地应用到用户的实际项目中
2. 记录每次变更的历史，支持多版本撤销功能
3. 提供简单直观的API，便于集成到现有的编辑流程中
"""

from autocoder.common.file_checkpoint.models import (
    FileChange, ChangeRecord, ApplyResult, UndoResult, DiffResult
)
from autocoder.common.file_checkpoint.manager import FileChangeManager
from autocoder.common.file_checkpoint.store import FileChangeStore
from autocoder.common.file_checkpoint.backup import FileBackupManager

__all__ = [
    'FileChange', 'ChangeRecord', 'ApplyResult', 'UndoResult', 'DiffResult',
    'FileChangeManager', 'FileChangeStore', 'FileBackupManager'
]
