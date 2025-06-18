"""
文件存储实现

基于JSON文件的对话存储实现，支持原子写入和数据完整性检查。
"""

import os
import json
import tempfile
import re
from typing import Optional, List, Dict, Any
from pathlib import Path

from .base_storage import BaseStorage
from ..exceptions import DataIntegrityError


class FileStorage(BaseStorage):
    """基于文件的存储实现"""
    
    def __init__(self, storage_path: str):
        """
        初始化文件存储
        
        Args:
            storage_path: 存储目录路径
        """
        self.storage_path = Path(storage_path)
        self._ensure_storage_directory()
    
    def _ensure_storage_directory(self):
        """确保存储目录存在"""
        self.storage_path.mkdir(parents=True, exist_ok=True)
    
    def _get_conversation_file_path(self, conversation_id: str) -> Path:
        """
        获取对话文件路径
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Path: 对话文件路径
        """
        # 清理文件名中的特殊字符
        safe_filename = self._sanitize_filename(conversation_id)
        return self.storage_path / f"{safe_filename}.json"
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        清理文件名，移除或替换特殊字符
        
        Args:
            filename: 原始文件名
            
        Returns:
            str: 安全的文件名
        """
        # 移除或替换不安全的字符
        safe_filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 确保文件名不为空
        if not safe_filename or safe_filename.isspace():
            safe_filename = 'unnamed'
        return safe_filename
    
    def _validate_conversation_data(self, conversation_data: Dict[str, Any]) -> bool:
        """
        验证对话数据的完整性
        
        Args:
            conversation_data: 对话数据
            
        Returns:
            bool: 数据有效返回True
        """
        if not isinstance(conversation_data, dict):
            return False
        
        # 检查必需字段
        required_fields = ['conversation_id']
        for field in required_fields:
            if field not in conversation_data:
                return False
            if not conversation_data[field]:
                return False
        
        return True
    
    def _atomic_write_file(self, file_path: Path, data: Dict[str, Any]) -> bool:
        """
        原子写入文件
        
        Args:
            file_path: 目标文件路径
            data: 要写入的数据
            
        Returns:
            bool: 写入成功返回True
        """
        temp_fd = None
        temp_path = None
        
        try:
            # 创建临时文件
            temp_fd, temp_path = tempfile.mkstemp(
                suffix='.tmp',
                prefix=file_path.name + '.',
                dir=file_path.parent
            )
            
            # 写入数据到临时文件
            with os.fdopen(temp_fd, 'w', encoding='utf-8') as temp_file:
                temp_fd = None  # 文件已关闭，避免重复关闭
                json.dump(data, temp_file, ensure_ascii=False, indent=2)
            
            # 原子重命名
            os.rename(temp_path, file_path)
            return True
            
        except (OSError, IOError, PermissionError, TypeError, ValueError):
            # 清理临时文件
            if temp_fd is not None:
                try:
                    os.close(temp_fd)
                except OSError:
                    pass
            
            if temp_path and os.path.exists(temp_path):
                try:
                    os.unlink(temp_path)
                except OSError:
                    pass
            
            return False
    
    def save_conversation(self, conversation_data: Dict[str, Any]) -> bool:
        """
        保存对话数据
        
        Args:
            conversation_data: 对话数据字典
            
        Returns:
            bool: 保存成功返回True
        """
        if not self._validate_conversation_data(conversation_data):
            return False
        
        conversation_id = conversation_data['conversation_id']
        file_path = self._get_conversation_file_path(conversation_id)
        
        return self._atomic_write_file(file_path, conversation_data)
    
    def load_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        加载对话数据
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            Optional[Dict[str, Any]]: 对话数据，不存在返回None
        """
        file_path = self._get_conversation_file_path(conversation_id)
        
        if not file_path.exists():
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 验证加载的数据
            if not self._validate_conversation_data(data):
                raise DataIntegrityError(f"对话数据无效: {conversation_id}")
            
            return data
            
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise DataIntegrityError(f"对话文件损坏: {conversation_id}, 错误: {str(e)}")
        except (OSError, IOError) as e:
            # 文件读取错误，返回None
            return None
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除对话数据
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            bool: 删除成功返回True
        """
        file_path = self._get_conversation_file_path(conversation_id)
        
        if not file_path.exists():
            return False
        
        try:
            file_path.unlink()
            return True
        except (OSError, IOError):
            return False
    
    def conversation_exists(self, conversation_id: str) -> bool:
        """
        检查对话是否存在
        
        Args:
            conversation_id: 对话ID
            
        Returns:
            bool: 存在返回True
        """
        file_path = self._get_conversation_file_path(conversation_id)
        return file_path.exists()
    
    def list_conversations(
        self, 
        limit: Optional[int] = None, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        列出对话
        
        Args:
            limit: 限制返回数量
            offset: 偏移量
            
        Returns:
            List[Dict[str, Any]]: 对话数据列表
        """
        conversations = []
        
        try:
            # 获取所有JSON文件
            json_files = list(self.storage_path.glob("*.json"))
            
            # 按修改时间排序（最新的在前）
            json_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            
            # 应用偏移量和限制
            if limit is not None:
                json_files = json_files[offset:offset + limit]
            else:
                json_files = json_files[offset:]
            
            # 加载对话数据
            for file_path in json_files:
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # 验证数据
                    if self._validate_conversation_data(data):
                        conversations.append(data)
                        
                except (json.JSONDecodeError, UnicodeDecodeError, OSError, IOError):
                    # 跳过损坏的文件
                    continue
                    
        except OSError:
            # 目录访问错误，返回空列表
            pass
        
        return conversations 