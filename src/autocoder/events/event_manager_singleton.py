"""
单例模式的事件管理器。
提供全局访问EventManager的方法，默认使用.auto-coder/auto-coder.web/events.jsonl文件存储事件。
"""

import os
import threading
from typing import Optional, Dict, Any

from .event_manager import EventManager
from .event_store import EventStore, JsonlEventStore
from loguru import logger


class EventManagerSingleton:
    """
    EventManager的单例包装器。确保整个应用程序中只有一个EventManager实例。
    默认使用.auto-coder/auto-coder.web/events.jsonl文件存储事件。
    """
    _default_instance: Optional[EventManager] = None
    _instances: Dict[str, EventManager] = {}
    
    @classmethod
    def get_instance(cls, event_file: Optional[str] = None) -> EventManager:
        """
        Get an EventManager instance for the specified event file.
        
        Args:
            event_file: Event file path to use as key. If None, returns the default instance.
            
        Returns:
            EventManager: The appropriate EventManager instance
        """
        if event_file is None:
            # Use default instance logic
            if cls._default_instance is None:
                cls._default_instance = EventManager(JsonlEventStore(os.path.join(".auto-coder", "auto-coder.web", "events.jsonl")))
            return cls._default_instance
        
        # If event_file is provided, use it as a key to store/retrieve EventManager instances
        if event_file not in cls._instances:
            cls._instances[event_file] = EventManager(JsonlEventStore(event_file))  
        
        return cls._instances[event_file]
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例实例。主要用于测试或需要更改事件文件时。
        """
        with cls._lock:
            cls._instance = None
    
    @classmethod
    def set_default_event_file(cls, event_file: str) -> None:
        """
        设置默认事件文件路径。
        仅在实例尚未创建时有效。
        
        Args:
            event_file: 新的默认事件文件路径
        """
        if cls._instance is None:
            with cls._lock:
                cls._default_event_file = event_file
        else:
            logger.warning("尝试更改默认事件文件，但实例已存在。请先调用reset_instance()。")


# 便捷函数，可以直接导入使用
def get_event_manager(event_file: Optional[str] = None) -> EventManager:
    """
    获取EventManager的单例实例。
    
    如果没有提供event_file，将返回默认的EventManager实例。
    如果提供了event_file，将返回或创建与该文件关联的EventManager实例。
    
    Args:
        event_file: 事件文件路径，如果为None则使用默认路径
        
    Returns:
        EventManager实例
    """
    return EventManagerSingleton.get_instance(event_file) 