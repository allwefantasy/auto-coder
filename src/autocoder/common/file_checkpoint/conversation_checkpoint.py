import os
import json
import time
import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from loguru import logger


class ConversationCheckpoint(BaseModel):
    """对话检查点，用于保存特定时刻的对话状态"""
    
    checkpoint_id: str  # 检查点ID，与变更组ID对应
    timestamp: float  # 创建时间戳
    conversations: List[Dict[str, Any]]  # 对话历史
    metadata: Optional[Dict[str, Any]] = None  # 元数据，可包含额外信息


class ConversationCheckpointStore:
    """对话检查点存储管理器"""
    
    def __init__(self, store_dir: Optional[str] = None, max_history: int = 50):
        """
        初始化对话检查点存储
        
        Args:
            store_dir: 存储目录，默认为用户主目录下的.autocoder/conversation_checkpoints
            max_history: 最大保存的历史版本数量
        """
        if store_dir is None:
            home_dir = os.path.expanduser("~")
            store_dir = os.path.join(home_dir, ".autocoder", "conversation_checkpoints")
        
        self.store_dir = os.path.abspath(store_dir)
        self.max_history = max_history
        
        # 确保存储目录存在
        os.makedirs(self.store_dir, exist_ok=True)
        logger.info(f"对话检查点存储目录: {self.store_dir}")
    
    def save_checkpoint(self, checkpoint: ConversationCheckpoint) -> str:
        """
        保存对话检查点
        
        Args:
            checkpoint: 对话检查点对象
            
        Returns:
            str: 检查点ID
        """
        # 确保检查点有ID
        if not checkpoint.checkpoint_id:
            checkpoint.checkpoint_id = str(uuid.uuid4())
        
        # 确保时间戳存在
        if not checkpoint.timestamp:
            checkpoint.timestamp = time.time()
        
        # 构建文件路径
        file_path = os.path.join(self.store_dir, f"{checkpoint.checkpoint_id}.json")
        
        # 保存为JSON文件
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(checkpoint.model_dump_json(ensure_ascii=False, indent=2))
            
            logger.info(f"已保存对话检查点: {checkpoint.checkpoint_id}")
            
            # 检查并清理过期的检查点
            self._cleanup_old_checkpoints()
            
            return checkpoint.checkpoint_id
        except Exception as e:
            logger.error(f"保存对话检查点失败: {str(e)}")
            return ""
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[ConversationCheckpoint]:
        """
        获取指定ID的对话检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            Optional[ConversationCheckpoint]: 对话检查点对象，如果不存在则返回None
        """
        file_path = os.path.join(self.store_dir, f"{checkpoint_id}.json")
        
        if not os.path.exists(file_path):
            logger.warning(f"对话检查点不存在: {checkpoint_id}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return ConversationCheckpoint(**data)
        except Exception as e:
            logger.error(f"读取对话检查点失败: {str(e)}")
            return None
    
    def get_latest_checkpoint(self) -> Optional[ConversationCheckpoint]:
        """
        获取最新的对话检查点
        
        Returns:
            Optional[ConversationCheckpoint]: 最新的对话检查点对象，如果不存在则返回None
        """
        checkpoints = self._get_all_checkpoints()
        
        if not checkpoints:
            return None
        
        # 按时间戳降序排序
        checkpoints.sort(key=lambda x: x.timestamp, reverse=True)
        
        return checkpoints[0] if checkpoints else None
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        删除指定的对话检查点
        
        Args:
            checkpoint_id: 检查点ID
            
        Returns:
            bool: 是否成功删除
        """
        file_path = os.path.join(self.store_dir, f"{checkpoint_id}.json")
        
        if not os.path.exists(file_path):
            logger.warning(f"要删除的对话检查点不存在: {checkpoint_id}")
            return False
        
        try:
            os.remove(file_path)
            logger.info(f"已删除对话检查点: {checkpoint_id}")
            return True
        except Exception as e:
            logger.error(f"删除对话检查点失败: {str(e)}")
            return False
    
    def _get_all_checkpoints(self) -> List[ConversationCheckpoint]:
        """
        获取所有对话检查点
        
        Returns:
            List[ConversationCheckpoint]: 对话检查点列表
        """
        checkpoints = []
        
        try:
            for filename in os.listdir(self.store_dir):
                if filename.endswith('.json'):
                    file_path = os.path.join(self.store_dir, filename)
                    
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        checkpoint = ConversationCheckpoint(**data)
                        checkpoints.append(checkpoint)
                    except Exception as e:
                        logger.error(f"读取对话检查点文件失败 {filename}: {str(e)}")
        except Exception as e:
            logger.error(f"获取所有对话检查点失败: {str(e)}")
        
        return checkpoints
    
    def _cleanup_old_checkpoints(self):
        """清理过期的检查点，保持历史记录数量在限制范围内"""
        checkpoints = self._get_all_checkpoints()
        
        if len(checkpoints) <= self.max_history:
            return
        
        # 按时间戳降序排序
        checkpoints.sort(key=lambda x: x.timestamp, reverse=True)
        
        # 删除超出限制的旧检查点
        for checkpoint in checkpoints[self.max_history:]:
            self.delete_checkpoint(checkpoint.checkpoint_id)
