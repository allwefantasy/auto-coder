"""
单例模式的事件管理器。
提供全局访问EventManager的方法，默认使用.auto-coder/auto-coder.web/events.jsonl文件存储事件。
"""

import os
import threading
from typing import Optional, Dict, Any

from .event_manager import EventManager
from .event_types import Event, EventType, ResponseEvent
from loguru import logger


class EventManagerSingleton:
    """
    EventManager的单例包装器。确保整个应用程序中只有一个EventManager实例。
    默认使用.auto-coder/auto-coder.web/events.jsonl文件存储事件。
    """
    _instance: Optional[EventManager] = None
    _lock = threading.Lock()
    _default_event_file = os.path.join(".auto-coder", "auto-coder.web", "events.jsonl")
    
    @classmethod
    def get_instance(cls, event_file: Optional[str] = None) -> EventManager:
        """
        获取EventManager的单例实例。
        
        Args:
            event_file: 事件文件路径，如果为None则使用默认路径
            
        Returns:
            EventManager实例
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    # 如果未提供event_file，使用默认路径
                    if event_file is None:
                        event_file = cls._default_event_file
                    
                    # 确保目录存在
                    os.makedirs(os.path.dirname(event_file), exist_ok=True)
                    
                    logger.debug(f"创建EventManager单例，使用文件路径: {event_file}")
                    cls._instance = EventManager.create(event_file)
        
        return cls._instance
    
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
    
    Args:
        event_file: 事件文件路径，如果为None则使用默认路径
        
    Returns:
        EventManager实例
    """
    return EventManagerSingleton.get_instance(event_file) 