"""
文件变更存储器

负责存储和管理文件变更历史记录，支持按组、按时间等方式查询变更记录。
"""

import os
import json
import sqlite3
import logging
import threading
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime

from autocoder.common.file_checkpoint.models import ChangeRecord

logger = logging.getLogger(__name__)


class FileChangeStore:
    """负责存储和管理文件变更历史记录"""
    
    def __init__(self, store_dir: Optional[str] = None, max_history: int = 50):
        """
        初始化变更存储
        
        Args:
            store_dir: 存储目录，如果为None则使用默认目录
            max_history: 最大保存的历史版本数量
        """
        if store_dir is None:
            # 默认存储目录为项目根目录下的.auto-coder/checkpoint
            store_dir = os.path.join(os.getcwd(), ".auto-coder", "checkpoint")
        
        self.store_dir = store_dir
        self.max_history = max_history
        self.db_file = os.path.join(store_dir, "changes.db")
        self.lock = threading.RLock()
        
        # 确保存储目录存在
        os.makedirs(store_dir, exist_ok=True)
        
        # 初始化数据库
        self._init_db()
    
    def save_change(self, change_record: ChangeRecord) -> str:
        """
        保存一条变更记录
        
        Args:
            change_record: 变更记录对象
            
        Returns:
            str: 变更记录ID
        """
        with self.lock:
            try:
                # 将变更记录保存到数据库
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    INSERT INTO changes 
                    (change_id, timestamp, file_path, backup_id, is_new, is_deletion, group_id, data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        change_record.change_id,
                        change_record.timestamp,
                        change_record.file_path,
                        change_record.backup_id,
                        int(change_record.is_new),
                        int(change_record.is_deletion),
                        change_record.group_id,
                        json.dumps(change_record.to_dict())
                    )
                )
                
                conn.commit()
                
                # 保存变更记录到JSON文件
                self._save_change_to_file(change_record)
                
                # 清理过旧的历史记录
                self._clean_old_history()
                
                logger.debug(f"已保存变更记录 {change_record.change_id}")
                return change_record.change_id
            
            except Exception as e:
                logger.error(f"保存变更记录失败: {str(e)}")
                raise
    
    def get_change(self, change_id: str) -> Optional[ChangeRecord]:
        """
        获取指定ID的变更记录
        
        Args:
            change_id: 变更记录ID
            
        Returns:
            ChangeRecord: 变更记录对象，如果不存在则返回None
        """
        with self.lock:
            try:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT data FROM changes WHERE change_id = ?",
                    (change_id,)
                )
                
                row = cursor.fetchone()
                if row is None:
                    return None
                
                data = json.loads(row[0])
                return ChangeRecord.from_dict(data)
            
            except Exception as e:
                logger.error(f"获取变更记录 {change_id} 失败: {str(e)}")
                return None
    
    def get_changes_by_group(self, group_id: str) -> List[ChangeRecord]:
        """
        获取指定组的所有变更记录
        
        Args:
            group_id: 变更组ID
            
        Returns:
            List[ChangeRecord]: 变更记录列表
        """
        with self.lock:
            try:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT data FROM changes WHERE group_id = ? ORDER BY timestamp DESC",
                    (group_id,)
                )
                
                changes = []
                for row in cursor.fetchall():
                    data = json.loads(row[0])
                    changes.append(ChangeRecord.from_dict(data))
                
                return changes
            
            except Exception as e:
                logger.error(f"获取变更组 {group_id} 的记录失败: {str(e)}")
                return []
    
    def get_latest_changes(self, limit: int = 10) -> List[ChangeRecord]:
        """
        获取最近的变更记录
        
        Args:
            limit: 返回的记录数量限制
            
        Returns:
            List[ChangeRecord]: 变更记录列表
        """
        with self.lock:
            try:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT data FROM changes ORDER BY timestamp DESC LIMIT ?",
                    (limit,)
                )
                
                changes = []
                for row in cursor.fetchall():
                    data = json.loads(row[0])
                    changes.append(ChangeRecord.from_dict(data))
                
                return changes
            
            except Exception as e:
                logger.error(f"获取最近变更记录失败: {str(e)}")
                return []
    
    def get_changes_by_file(self, file_path: str, limit: int = 10) -> List[ChangeRecord]:
        """
        获取指定文件的变更记录
        
        Args:
            file_path: 文件路径
            limit: 返回的记录数量限制
            
        Returns:
            List[ChangeRecord]: 变更记录列表
        """
        with self.lock:
            try:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "SELECT data FROM changes WHERE file_path = ? ORDER BY timestamp DESC LIMIT ?",
                    (file_path, limit)
                )
                
                changes = []
                for row in cursor.fetchall():
                    data = json.loads(row[0])
                    changes.append(ChangeRecord.from_dict(data))
                
                return changes
            
            except Exception as e:
                logger.error(f"获取文件 {file_path} 的变更记录失败: {str(e)}")
                return []
    
    def delete_change(self, change_id: str) -> bool:
        """
        删除指定的变更记录
        
        Args:
            change_id: 变更记录ID
            
        Returns:
            bool: 删除是否成功
        """
        with self.lock:
            try:
                # 获取变更记录
                change = self.get_change(change_id)
                if change is None:
                    return False
                
                # 删除数据库中的记录
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    "DELETE FROM changes WHERE change_id = ?",
                    (change_id,)
                )
                
                conn.commit()
                
                # 删除JSON文件
                json_file = os.path.join(self.store_dir, f"{change_id}.json")
                if os.path.exists(json_file):
                    os.remove(json_file)
                
                logger.debug(f"已删除变更记录 {change_id}")
                return True
            
            except Exception as e:
                logger.error(f"删除变更记录 {change_id} 失败: {str(e)}")
                return False
    
    def get_change_groups(self, limit: int = 10) -> List[Tuple[str, float, int]]:
        """
        获取变更组列表
        
        Args:
            limit: 返回的组数量限制
            
        Returns:
            List[Tuple[str, float, int]]: 变更组ID、最新时间戳和变更数量的列表
        """
        with self.lock:
            try:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                cursor.execute(
                    """
                    SELECT group_id, MAX(timestamp) as latest_time, COUNT(*) as count
                    FROM changes
                    WHERE group_id IS NOT NULL
                    GROUP BY group_id
                    ORDER BY latest_time DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
                
                groups = []
                for row in cursor.fetchall():
                    groups.append((row[0], row[1], row[2]))
                
                return groups
            
            except Exception as e:
                logger.error(f"获取变更组列表失败: {str(e)}")
                return []
    
    def _init_db(self) -> None:
        """初始化数据库"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 创建变更记录表
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS changes (
                    change_id TEXT PRIMARY KEY,
                    timestamp REAL NOT NULL,
                    file_path TEXT NOT NULL,
                    backup_id TEXT,
                    is_new INTEGER NOT NULL DEFAULT 0,
                    is_deletion INTEGER NOT NULL DEFAULT 0,
                    group_id TEXT,
                    data TEXT NOT NULL
                )
                """
            )
            
            # 创建索引
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_changes_timestamp ON changes (timestamp)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_changes_file_path ON changes (file_path)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_changes_group_id ON changes (group_id)"
            )
            
            conn.commit()
        
        except Exception as e:
            logger.error(f"初始化数据库失败: {str(e)}")
            raise
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_file)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _save_change_to_file(self, change_record: ChangeRecord) -> None:
        """将变更记录保存到JSON文件"""
        try:
            json_file = os.path.join(self.store_dir, f"{change_record.change_id}.json")
            
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(change_record.to_dict(), f, indent=2)
        
        except Exception as e:
            logger.error(f"保存变更记录到文件失败: {str(e)}")
    
    def _clean_old_history(self) -> None:
        """清理过旧的历史记录"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # 获取记录总数
            cursor.execute("SELECT COUNT(*) FROM changes")
            total_count = cursor.fetchone()[0]
            
            # 如果记录数超过最大限制，删除最旧的记录
            if total_count > self.max_history:
                # 计算需要删除的记录数
                delete_count = total_count - self.max_history
                
                # 获取要删除的记录ID
                cursor.execute(
                    "SELECT change_id FROM changes ORDER BY timestamp ASC LIMIT ?",
                    (delete_count,)
                )
                
                change_ids = [row[0] for row in cursor.fetchall()]
                
                # 删除记录
                for change_id in change_ids:
                    self.delete_change(change_id)
                
                logger.debug(f"已清理 {len(change_ids)} 条过旧的变更记录")
        
        except Exception as e:
            logger.error(f"清理过旧的历史记录失败: {str(e)}")
