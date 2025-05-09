"""
文件变更管理器

整个模块的主入口，提供高层次的API接口，用于应用、记录和撤销文件变更。
"""

import os
import uuid
import logging
import difflib
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from autocoder.common.file_checkpoint.models import (
    FileChange, ChangeRecord, ApplyResult, UndoResult, DiffResult
)
from autocoder.common.file_checkpoint.backup import FileBackupManager
from autocoder.common.file_checkpoint.store import FileChangeStore

logger = logging.getLogger(__name__)


class FileChangeManager:
    """文件变更管理器，提供高层次的API接口"""
    
    def __init__(self, project_dir: str, backup_dir: Optional[str] = None, 
                 store_dir: Optional[str] = None, max_history: int = 50):
        """
        初始化文件变更管理器
        
        Args:
            project_dir: 用户项目的根目录
            backup_dir: 备份文件存储目录，默认为用户主目录下的.autocoder/backups
            store_dir: 变更记录存储目录，默认为用户主目录下的.autocoder/changes
            max_history: 最大保存的历史版本数量
        """
        self.project_dir = os.path.abspath(project_dir)
        self.backup_manager = FileBackupManager(backup_dir)
        self.change_store = FileChangeStore(store_dir, max_history)
    
    def apply_changes(self, changes: Dict[str, FileChange], change_group_id: Optional[str] = None) -> ApplyResult:
        """
        应用一组文件变更
        
        Args:
            changes: 文件变更字典，格式为 {file_path: FileChange}
            change_group_id: 变更组ID，用于将相关变更归为一组
            
        Returns:
            ApplyResult: 应用结果对象
        """
        # 如果没有提供变更组ID，生成一个新的
        if change_group_id is None:
            change_group_id = str(uuid.uuid4())
        
        result = ApplyResult(success=True)
        
        # 处理每个文件的变更
        for file_path, change in changes.items():
            try:
                # 获取文件的绝对路径
                abs_file_path = self._get_absolute_path(file_path)
                
                # 确定文件是否是新文件
                is_new = not os.path.exists(abs_file_path)
                
                # 备份原文件（如果存在）
                backup_id = None
                if not is_new and not change.is_deletion:
                    backup_id = self.backup_manager.backup_file(abs_file_path)
                
                # 处理文件变更
                if change.is_deletion:
                    # 如果是删除操作，先备份再删除
                    backup_id = self.backup_manager.backup_file(abs_file_path)
                    if os.path.exists(abs_file_path):
                        os.remove(abs_file_path)
                else:
                    # 确保目录存在
                    dir_path = os.path.dirname(abs_file_path)
                    if dir_path:
                        os.makedirs(dir_path, exist_ok=True)
                    
                    # 写入文件内容
                    with open(abs_file_path, 'w', encoding='utf-8') as f:
                        f.write(change.content)
                
                # 创建变更记录
                change_record = ChangeRecord.create(
                    file_path=file_path,
                    backup_id=backup_id,
                    is_new=is_new,
                    is_deletion=change.is_deletion,
                    group_id=change_group_id
                )
                
                # 保存变更记录
                change_id = self.change_store.save_change(change_record)
                result.add_change_id(change_id)
                
                logger.info(f"已应用变更到文件 {file_path}")
            
            except Exception as e:
                error_message = f"应用变更到文件 {file_path} 失败: {str(e)}"
                logger.error(error_message)
                result.add_error(file_path, error_message)
        
        return result
    
    def preview_changes(self, changes: Dict[str, FileChange]) -> Dict[str, DiffResult]:
        """
        预览变更的差异
        
        Args:
            changes: 文件变更字典
            
        Returns:
            Dict[str, DiffResult]: 每个文件的差异结果
        """
        diff_results = {}
        
        for file_path, change in changes.items():
            try:
                # 获取文件的绝对路径
                abs_file_path = self._get_absolute_path(file_path)
                
                # 确定文件是否是新文件
                is_new = not os.path.exists(abs_file_path)
                
                # 获取原文件内容
                old_content = None
                if not is_new and not change.is_deletion:
                    try:
                        with open(abs_file_path, 'r', encoding='utf-8') as f:
                            old_content = f.read()
                    except Exception as e:
                        logger.error(f"读取文件 {abs_file_path} 失败: {str(e)}")
                
                # 创建差异结果
                diff_result = DiffResult(
                    file_path=file_path,
                    old_content=old_content,
                    new_content=change.content,
                    is_new=is_new,
                    is_deletion=change.is_deletion
                )
                
                diff_results[file_path] = diff_result
            
            except Exception as e:
                logger.error(f"预览文件 {file_path} 的变更差异失败: {str(e)}")
        
        return diff_results
    
    def undo_last_change(self) -> UndoResult:
        """
        撤销最近的一次变更
        
        Returns:
            UndoResult: 撤销结果对象
        """
        # 获取最近的变更记录
        latest_changes = self.change_store.get_latest_changes(limit=1)
        if not latest_changes:
            return UndoResult(success=False, errors={"general": "没有找到最近的变更记录"})
        
        latest_change = latest_changes[0]
        
        # 如果最近的变更属于一个组，撤销整个组
        if latest_change.group_id:
            return self.undo_change_group(latest_change.group_id)
        else:
            # 否则只撤销这一个变更
            return self.undo_change(latest_change.change_id)
    
    def undo_change(self, change_id: str) -> UndoResult:
        """
        撤销指定的变更
        
        Args:
            change_id: 变更记录ID
            
        Returns:
            UndoResult: 撤销结果对象
        """
        # 获取变更记录
        change_record = self.change_store.get_change(change_id)
        if change_record is None:
            return UndoResult(success=False, errors={"general": f"变更记录 {change_id} 不存在"})
        
        result = UndoResult(success=True)
        
        try:
            # 获取文件的绝对路径
            abs_file_path = self._get_absolute_path(change_record.file_path)
            
            # 根据变更类型执行撤销操作
            if change_record.is_new:
                # 如果是新建文件的变更，删除该文件
                if os.path.exists(abs_file_path):
                    os.remove(abs_file_path)
                    result.add_restored_file(change_record.file_path)
            elif change_record.is_deletion:
                # 如果是删除文件的变更，从备份恢复
                if change_record.backup_id:
                    success = self.backup_manager.restore_file(abs_file_path, change_record.backup_id)
                    if success:
                        result.add_restored_file(change_record.file_path)
                    else:
                        result.add_error(change_record.file_path, "从备份恢复文件失败")
                else:
                    result.add_error(change_record.file_path, "没有找到文件备份")
            else:
                # 如果是修改文件的变更，从备份恢复
                if change_record.backup_id:
                    success = self.backup_manager.restore_file(abs_file_path, change_record.backup_id)
                    if success:
                        result.add_restored_file(change_record.file_path)
                    else:
                        result.add_error(change_record.file_path, "从备份恢复文件失败")
                else:
                    result.add_error(change_record.file_path, "没有找到文件备份")
            
            # 删除变更记录
            self.change_store.delete_change(change_id)
            
            logger.info(f"已撤销变更 {change_id}")
        
        except Exception as e:
            error_message = f"撤销变更 {change_id} 失败: {str(e)}"
            logger.error(error_message)
            result.add_error(change_record.file_path, error_message)
            result.success = False
        
        return result
            
    def undo_change_group(self, group_id: str) -> UndoResult:
        """
        撤销指定组的所有变更
        
        Args:
            group_id: 变更组ID
            
        Returns:
            UndoResult: 撤销结果对象
        """
        # 获取组内的所有变更记录
        changes = self.change_store.get_changes_by_group(group_id)
        if not changes:
            return UndoResult(success=False, errors={"general": f"变更组 {group_id} 不存在或为空"})
        
        result = UndoResult(success=True)
        
        # 按时间戳降序排序，确保按照相反的顺序撤销
        changes.sort(key=lambda x: x.timestamp, reverse=True)
        
        # 逐个撤销变更
        for change in changes:
            change_result = self.undo_change(change.change_id)
            
            # 合并结果
            result.success = result.success and change_result.success
            result.restored_files.extend(change_result.restored_files)
            result.errors.update(change_result.errors)
        
        return result
    
    def undo_to_version(self, version_id: str) -> UndoResult:
        """
        撤销到指定的历史版本
        
        Args:
            version_id: 目标版本ID（变更记录ID）
            
        Returns:
            UndoResult: 撤销结果对象
        """
        # 获取目标版本的变更记录
        target_change = self.change_store.get_change(version_id)
        if target_change is None:
            return UndoResult(success=False, errors={"general": f"变更记录 {version_id} 不存在"})
        
        # 获取最近的变更记录
        latest_changes = self.change_store.get_latest_changes()
        if not latest_changes:
            return UndoResult(success=False, errors={"general": "没有找到最近的变更记录"})
        
        # 找出需要撤销的变更记录
        changes_to_undo = []
        for change in latest_changes:
            if change.timestamp > target_change.timestamp:
                changes_to_undo.append(change)
        
        if not changes_to_undo:
            return UndoResult(success=True, restored_files=[])
        
        result = UndoResult(success=True)
        
        # 按时间戳降序排序，确保按照相反的顺序撤销
        changes_to_undo.sort(key=lambda x: x.timestamp, reverse=True)
        
        # 逐个撤销变更
        for change in changes_to_undo:
            change_result = self.undo_change(change.change_id)
            
            # 合并结果
            result.success = result.success and change_result.success
            result.restored_files.extend(change_result.restored_files)
            result.errors.update(change_result.errors)
        
        return result
    
    def get_change_history(self, limit: int = 10) -> List[ChangeRecord]:
        """
        获取变更历史记录
        
        Args:
            limit: 返回的历史记录数量限制
            
        Returns:
            List[ChangeRecord]: 变更记录列表
        """
        return self.change_store.get_latest_changes(limit)
    
    def get_file_history(self, file_path: str, limit: int = 10) -> List[ChangeRecord]:
        """
        获取指定文件的变更历史
        
        Args:
            file_path: 文件路径
            limit: 返回的历史记录数量限制
            
        Returns:
            List[ChangeRecord]: 变更记录列表
        """
        return self.change_store.get_changes_by_file(file_path, limit)
    
    def get_changes_by_group(self, group_id: str) -> List[ChangeRecord]:
        """
        获取指定变更组的所有变更记录
        
        Args:
            group_id: 变更组ID
            
        Returns:
            List[ChangeRecord]: 变更记录列表
        """
        return self.change_store.get_changes_by_group(group_id)
    
    def get_change_groups(self, limit: int = 10) -> List[Tuple[str, float, int]]:
        """
        获取变更组列表
        
        Args:
            limit: 返回的组数量限制
            
        Returns:
            List[Tuple[str, float, int]]: 变更组ID、最新时间戳和变更数量的列表
        """
        return self.change_store.get_change_groups(limit)
    
    def get_diff_text(self, old_content: str, new_content: str) -> str:
        """
        获取两个文本内容的差异文本
        
        Args:
            old_content: 原始内容
            new_content: 新内容
            
        Returns:
            str: 差异文本
        """
        if old_content is None:
            return "新文件"
        
        if new_content is None:
            return "文件已删除"
        
        old_lines = old_content.splitlines()
        new_lines = new_content.splitlines()
        
        diff = difflib.unified_diff(
            old_lines,
            new_lines,
            lineterm='',
            n=3  # 上下文行数
        )
        
        return '\n'.join(diff)
    
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
            return os.path.join(self.project_dir, file_path)
