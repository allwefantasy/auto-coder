"""
文件备份管理器

负责文件的备份和恢复操作，支持多版本文件备份。
"""

import os
import uuid
import shutil
import logging
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import json
import threading

logger = logging.getLogger(__name__)


class FileBackupManager:
    """负责文件的备份和恢复操作"""
    
    def __init__(self, backup_dir: Optional[str] = None):
        """
        初始化备份管理器
        
        Args:
            backup_dir: 备份文件存储目录，如果为None则使用默认目录
        """
        if backup_dir is None:
            # 默认备份目录为项目根目录下的.auto-coder/checkpoint
            backup_dir = os.path.join(os.getcwd(), ".auto-coder", "checkpoint")
        
        self.backup_dir = backup_dir
        self.metadata_file = os.path.join(backup_dir, "backup_metadata.json")
        self.lock = threading.RLock()
        
        # 确保备份目录存在
        os.makedirs(backup_dir, exist_ok=True)
        
        # 加载备份元数据
        self.metadata = self._load_metadata()
    
    def backup_file(self, file_path: str) -> Optional[str]:
        """
        备份指定文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 备份文件ID，如果文件不存在则返回None
        """
        if not os.path.exists(file_path):
            return None
        
        with self.lock:
            # 生成唯一的备份ID
            backup_id = str(uuid.uuid4())
            
            # 构建备份文件路径
            backup_file_path = os.path.join(self.backup_dir, backup_id)
            
            try:
                # 复制文件到备份目录
                shutil.copy2(file_path, backup_file_path)
                
                # 更新元数据
                self.metadata[backup_id] = {
                    "original_path": file_path,
                    "timestamp": datetime.now().timestamp(),
                    "size": os.path.getsize(file_path)
                }
                
                # 保存元数据
                self._save_metadata()
                
                logger.debug(f"已备份文件 {file_path} 到 {backup_file_path}")
                return backup_id
            
            except Exception as e:
                logger.error(f"备份文件 {file_path} 失败: {str(e)}")
                # 清理可能部分创建的备份文件
                if os.path.exists(backup_file_path):
                    os.remove(backup_file_path)
                return None
    
    def restore_file(self, file_path: str, backup_id: str) -> bool:
        """
        从备份恢复文件
        
        Args:
            file_path: 目标文件路径
            backup_id: 备份文件ID
            
        Returns:
            bool: 恢复是否成功
        """
        with self.lock:
            # 检查备份ID是否存在
            if backup_id not in self.metadata:
                logger.error(f"备份ID {backup_id} 不存在")
                return False
            
            # 构建备份文件路径
            backup_file_path = os.path.join(self.backup_dir, backup_id)
            
            # 检查备份文件是否存在
            if not os.path.exists(backup_file_path):
                logger.error(f"备份文件 {backup_file_path} 不存在")
                return False
            
            try:
                # 确保目标目录存在
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                
                # 复制备份文件到目标路径
                shutil.copy2(backup_file_path, file_path)
                
                logger.debug(f"已从 {backup_file_path} 恢复文件到 {file_path}")
                return True
            
            except Exception as e:
                logger.error(f"恢复文件 {file_path} 失败: {str(e)}")
                return False
    
    def get_backup_content(self, backup_id: str) -> Optional[str]:
        """
        获取备份文件的内容
        
        Args:
            backup_id: 备份文件ID
            
        Returns:
            str: 备份文件内容，如果备份不存在则返回None
        """
        with self.lock:
            # 检查备份ID是否存在
            if backup_id not in self.metadata:
                logger.error(f"备份ID {backup_id} 不存在")
                return None
            
            # 构建备份文件路径
            backup_file_path = os.path.join(self.backup_dir, backup_id)
            
            # 检查备份文件是否存在
            if not os.path.exists(backup_file_path):
                logger.error(f"备份文件 {backup_file_path} 不存在")
                return None
            
            try:
                # 读取备份文件内容
                with open(backup_file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            except Exception as e:
                logger.error(f"读取备份文件 {backup_file_path} 失败: {str(e)}")
                return None
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        删除指定的备份文件
        
        Args:
            backup_id: 备份文件ID
            
        Returns:
            bool: 删除是否成功
        """
        with self.lock:
            # 检查备份ID是否存在
            if backup_id not in self.metadata:
                logger.error(f"备份ID {backup_id} 不存在")
                return False
            
            # 构建备份文件路径
            backup_file_path = os.path.join(self.backup_dir, backup_id)
            
            try:
                # 删除备份文件
                if os.path.exists(backup_file_path):
                    os.remove(backup_file_path)
                
                # 更新元数据
                del self.metadata[backup_id]
                
                # 保存元数据
                self._save_metadata()
                
                logger.debug(f"已删除备份 {backup_id}")
                return True
            
            except Exception as e:
                logger.error(f"删除备份 {backup_id} 失败: {str(e)}")
                return False
    
    def clean_old_backups(self, max_age_days: int = 30) -> int:
        """
        清理过旧的备份文件
        
        Args:
            max_age_days: 最大保留天数
            
        Returns:
            int: 清理的备份文件数量
        """
        with self.lock:
            now = datetime.now().timestamp()
            max_age_seconds = max_age_days * 24 * 60 * 60
            
            backup_ids_to_delete = []
            
            # 找出过旧的备份
            for backup_id, metadata in self.metadata.items():
                if now - metadata["timestamp"] > max_age_seconds:
                    backup_ids_to_delete.append(backup_id)
            
            # 删除过旧的备份
            deleted_count = 0
            for backup_id in backup_ids_to_delete:
                if self.delete_backup(backup_id):
                    deleted_count += 1
            
            return deleted_count
    
    def get_backups_for_file(self, file_path: str) -> List[Tuple[str, float]]:
        """
        获取指定文件的所有备份
        
        Args:
            file_path: 文件路径
            
        Returns:
            List[Tuple[str, float]]: 备份ID和时间戳的列表，按时间戳降序排序
        """
        with self.lock:
            backups = []
            
            for backup_id, metadata in self.metadata.items():
                if metadata["original_path"] == file_path:
                    backups.append((backup_id, metadata["timestamp"]))
            
            # 按时间戳降序排序
            backups.sort(key=lambda x: x[1], reverse=True)
            
            return backups
    
    def _load_metadata(self) -> Dict:
        """加载备份元数据"""
        if os.path.exists(self.metadata_file):
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载备份元数据失败: {str(e)}")
        
        return {}
    
    def _save_metadata(self) -> None:
        """保存备份元数据"""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2)
        except Exception as e:
            logger.error(f"保存备份元数据失败: {str(e)}")
