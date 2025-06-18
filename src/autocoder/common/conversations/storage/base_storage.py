"""
存储基类定义

定义了对话存储的抽象接口，所有存储实现都必须继承此基类。
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any


class BaseStorage(ABC):
    """存储基类，定义对话存储的抽象接口"""
    
    @abstractmethod
    def save_conversation(self, conversation_data: Dict[str, Any]) -> bool:
        """
        保存对话数据
        
        Args:
            conversation_data: 对话数据字典，必须包含conversation_id
            
        Returns:
            bool: 保存成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def load_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        加载对话数据
        
        Args:
            conversation_id: 对话唯一标识符
            
        Returns:
            Optional[Dict[str, Any]]: 对话数据字典，不存在返回None
        """
        pass
    
    @abstractmethod
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        删除对话数据
        
        Args:
            conversation_id: 对话唯一标识符
            
        Returns:
            bool: 删除成功返回True，失败返回False
        """
        pass
    
    @abstractmethod
    def conversation_exists(self, conversation_id: str) -> bool:
        """
        检查对话是否存在
        
        Args:
            conversation_id: 对话唯一标识符
            
        Returns:
            bool: 存在返回True，不存在返回False
        """
        pass
    
    @abstractmethod
    def list_conversations(
        self, 
        limit: Optional[int] = None, 
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        列出对话
        
        Args:
            limit: 限制返回数量，None表示无限制
            offset: 偏移量
            
        Returns:
            List[Dict[str, Any]]: 对话数据列表
        """
        pass 