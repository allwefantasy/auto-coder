import os
import threading
from typing import Optional
from .manager import PersistConversationManager
from .config import ConversationManagerConfig


class ConversationManagerSingleton:
    """对话管理器的单例类，确保全局只有一个实例"""
    
    _instance: Optional[PersistConversationManager] = None
    _lock = threading.Lock()
    _config: Optional[ConversationManagerConfig] = None
    
    @classmethod
    def get_instance(cls, config: Optional[ConversationManagerConfig] = None) -> PersistConversationManager:
        """
        获取对话管理器实例
        
        Args:
            config: 配置对象，如果为None则使用默认配置
            
        Returns:
            PersistConversationManager实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    if config is None:
                        config = cls._get_default_config()
                    cls._config = config
                    cls._instance = PersistConversationManager(config)
        return cls._instance
    
    @classmethod
    def reset_instance(cls, config: Optional[ConversationManagerConfig] = None):
        """
        重置实例，用于测试或配置更改时
        
        Args:
            config: 新的配置对象
        """
        with cls._lock:
            cls._instance = None
            cls._config = None
            if config is not None:
                cls._instance = PersistConversationManager(config)
                cls._config = config
    
    @classmethod
    def _get_default_config(cls) -> ConversationManagerConfig:
        """获取默认配置"""
        # 默认存储路径为当前工作目录下的 .auto-coder/conversations
        default_storage_path = os.path.join(os.getcwd(), ".auto-coder", "conversations")
        
        return ConversationManagerConfig(
            storage_path=default_storage_path,
            max_cache_size=100,
            cache_ttl=300.0,
            lock_timeout=10.0,
            backup_enabled=True,
            backup_interval=3600.0,
            max_backups=10
        )
    
    @classmethod
    def get_config(cls) -> Optional[ConversationManagerConfig]:
        """获取当前使用的配置"""
        return cls._config


def get_conversation_manager(config: Optional[ConversationManagerConfig] = None) -> PersistConversationManager:
    """
    获取全局对话管理器实例
    
    这是一个便捷函数，内部使用单例模式确保全局只有一个实例。
    首次调用时会创建实例，后续调用会返回同一个实例。
    
    Args:
        config: 可选的配置对象。如果为None，将使用默认配置。
               注意：只有在首次调用时，config参数才会生效。
    
    Returns:
        PersistConversationManager: 对话管理器实例
        
    Example:
        ```python
        # 使用默认配置
        manager = get_conversation_manager()
        
        # 使用自定义配置（仅在首次调用时生效）
        config = ConversationManagerConfig(
            storage_path="./my_conversations",
            max_cache_size=200
        )
        manager = get_conversation_manager(config)
        
        # 创建对话
        conv_id = manager.create_conversation(
            name="测试对话",
            description="这是一个测试对话"
        )
        ```
    """
    return ConversationManagerSingleton.get_instance(config)


def reset_conversation_manager(config: Optional[ConversationManagerConfig] = None):
    """
    重置全局对话管理器实例
    
    用于测试或需要更改配置时重置实例。
    
    Args:
        config: 新的配置对象，如果为None则在下次调用get_conversation_manager时使用默认配置
        
    Example:
        ```python
        # 重置为默认配置
        reset_conversation_manager()
        
        # 重置为新配置
        new_config = ConversationManagerConfig(storage_path="./new_path")
        reset_conversation_manager(new_config)
        ```
    """
    ConversationManagerSingleton.reset_instance(config)


def get_conversation_manager_config() -> Optional[ConversationManagerConfig]:
    """
    获取当前对话管理器使用的配置
    
    Returns:
        当前配置对象，如果还未初始化则返回None
    """
    return ConversationManagerSingleton.get_config()


# 便捷别名
get_manager = get_conversation_manager
reset_manager = reset_conversation_manager
get_manager_config = get_conversation_manager_config
