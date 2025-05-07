"""
文件变更管理模块的工具函数

提供一些常用的工具函数，简化文件变更管理模块的使用。
"""

import os
import json
from typing import Dict, List, Optional, Any

from autocoder.common.file_checkpoint.models import FileChange
from autocoder.common.file_checkpoint.manager import FileChangeManager


def apply_shadow_changes(source_dir: str, changes: Dict[str, Any]) -> Dict[str, Any]:
    """
    将影子系统的变更应用到用户项目中
    
    Args:
        source_dir: 用户项目的根目录
        changes: 影子系统的变更字典，格式为 {file_path: {content: str}}
        
    Returns:
        Dict: 应用结果，包含成功和失败的信息
    """
    # 创建文件变更管理器
    manager = FileChangeManager(source_dir)
    
    # 将影子系统的变更转换为 FileChange 对象
    file_changes = {}
    for file_path, change in changes.items():
        # 确定文件是否是新文件
        abs_file_path = os.path.join(source_dir, file_path)
        is_new = not os.path.exists(abs_file_path)
        
        file_changes[file_path] = FileChange(
            file_path=file_path,
            content=change.get('content', ''),
            is_new=is_new,
            is_deletion=change.get('is_deletion', False)
        )
    
    # 应用变更
    result = manager.apply_changes(file_changes)
    
    # 返回结果
    return {
        'success': result.success,
        'change_ids': result.change_ids,
        'errors': result.errors,
        'changed_files': list(file_changes.keys())
    }


def undo_last_changes(source_dir: str, steps: int = 1) -> Dict[str, Any]:
    """
    撤销最近的变更
    
    Args:
        source_dir: 用户项目的根目录
        steps: 要撤销的步骤数
        
    Returns:
        Dict: 撤销结果，包含成功和失败的信息
    """
    # 创建文件变更管理器
    manager = FileChangeManager(source_dir)
    
    # 执行多步撤销
    all_restored_files = []
    all_errors = {}
    success = True
    
    for _ in range(steps):
        result = manager.undo_last_change()
        if not result.success:
            success = False
            all_errors.update(result.errors)
            break
        
        all_restored_files.extend(result.restored_files)
    
    # 返回结果
    return {
        'success': success,
        'restored_files': all_restored_files,
        'errors': all_errors
    }


def get_change_history(source_dir: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    获取变更历史记录
    
    Args:
        source_dir: 用户项目的根目录
        limit: 返回的历史记录数量限制
        
    Returns:
        List[Dict]: 变更记录列表
    """
    # 创建文件变更管理器
    manager = FileChangeManager(source_dir)
    
    # 获取变更历史
    changes = manager.get_change_history(limit)
    
    # 转换为字典列表
    return [
        {
            'change_id': change.change_id,
            'timestamp': change.timestamp,
            'file_path': change.file_path,
            'is_new': change.is_new,
            'is_deletion': change.is_deletion,
            'group_id': change.group_id
        }
        for change in changes
    ]
