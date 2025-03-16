import os
import threading
from typing import Optional, Dict, Any, List
import uuid
from datetime import datetime
import glob
import json
import re
from pathlib import Path
import byzerllm

from .event_manager import EventManager
from .event_store import EventStore, JsonlEventStore
from .event_types import Event, EventType
from loguru import logger


class EventManagerSingleton:
    """
    EventManager的单例包装器。确保整个应用程序中只有一个EventManager实例    
    """
    _default_instance: Optional[EventManager] = None
    _instances: Dict[str, EventManager] = {}
    _lock = threading.RLock()  # 用于线程安全操作的锁
    
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
                cls._default_instance = EventManager(JsonlEventStore(os.path.join(".auto-coder", "events", "events.jsonl")))
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
            cls._default_instance = None
    
    @classmethod
    def set_default_event_file(cls, event_file: str) -> None:
        """
        设置默认事件文件路径。
        仅在实例尚未创建时有效。
        
        Args:
            event_file: 新的默认事件文件路径
        """
        if cls._default_instance is None:
            with cls._lock:
                cls._default_event_file = event_file
        else:
            logger.warning("尝试更改默认事件文件，但实例已存在。请先调用reset_instance()。")

def get_event_file_path(file_id:str,project_path: Optional[str] = None) -> str:
    if project_path is None:
        return os.path.join(".auto-coder", "events", f"{file_id}.jsonl")
    else:
        return os.path.join(project_path, ".auto-coder", "events", f"{file_id}.jsonl")

def gengerate_event_file_path(project_path: Optional[str] = None) -> (str,str):
    """
    生成一个格式为 uuid_timestamp.jsonl 的事件文件名。
    timestamp 格式为 YYYYMMDD-HHMMSS。
    
    Returns:
        生成的事件文件路径
    """
    # 生成 UUID
    unique_id = str(uuid.uuid4())
    
    # 生成当前时间戳，格式为 YYYYMMDD-HHMMSS
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    
    file_id = f"{unique_id}_{timestamp}"
    # 组合文件名
    file_name = f"{file_id}.jsonl"
    
    if project_path is None:
        return os.path.join(".auto-coder", "events", file_name),file_id
    else:   
        return os.path.join(project_path, ".auto-coder", "events", file_name),file_id

@byzerllm.prompt()
def _format_events_prompt(event_files: List[Dict]) -> str:
    """       
    <recent_events>                
    最近的事件记录，从最新到最旧排序：
    
    {% for event_file in event_files %}
    ## 事件文件 {{ loop.index }}: {{ event_file.file_name }}
    
    {% if event_file.timestamp %}
    **时间**: {{ event_file.timestamp }}
    {% endif %}
    
    {% if event_file.events %}
    **事件内容**:
    {% for event in event_file.events %}
    - 类型: {{ event.event_type }}
      {% if event.content %}
      内容: 
      ```
      {{ event.content }}
      ```
      {% endif %}
      {% if event.metadata %}
      元数据: {{ event.metadata }}
      {% endif %}
    {% endfor %}
    {% endif %}
    
    {% if not loop.last %}
    ---
    {% endif %}
    {% endfor %}
    </recent_events>
    请注意上述最近的事件记录，以便更好地理解当前系统状态和交互历史。
    """

def to_events_prompt(limit: int = 5, project_path: Optional[str] = None) -> str:
    """
    获取最近的N条事件文件并读取其中的事件内容，返回格式化后的提示文本。
    排除类型为 STREAM 的事件，以减少输出内容的冗余。
    
    Args:
        limit: 最多返回的事件文件数量，默认为5
        project_path: 可选的项目路径，如果提供则在该路径下查找事件文件
        
    Returns:
        格式化后的事件提示文本
    """
    # 确定事件文件所在目录
    if project_path is None:
        events_dir = os.path.join(".auto-coder", "events")
    else:
        events_dir = os.path.join(project_path, ".auto-coder", "events")
    
    # 确保目录存在
    if not os.path.exists(events_dir):
        logger.warning(f"事件目录不存在: {events_dir}")
        return "未找到任何事件记录。"
    
    # 获取所有事件文件
    event_file_pattern = os.path.join(events_dir, "*.jsonl")
    event_files = glob.glob(event_file_pattern)
    
    if not event_files:
        logger.warning(f"未找到任何事件文件: {event_file_pattern}")
        return "未找到任何事件记录。"
    
    # 解析文件名中的时间戳，格式为 uuid_YYYYMMDD-HHMMSS.jsonl
    def extract_timestamp(file_path):
        file_name = os.path.basename(file_path)
        match = re.search(r'_(\d{8}-\d{6})\.jsonl$', file_name)
        if match:
            timestamp_str = match.group(1)
            try:
                return datetime.strptime(timestamp_str, "%Y%m%d-%H%M%S")
            except ValueError:
                return datetime.fromtimestamp(0)  # 默认最早时间
        return datetime.fromtimestamp(0)  # 默认最早时间
    
    # 按时间戳从新到旧排序
    sorted_files = sorted(event_files, key=extract_timestamp, reverse=True)
    limited_files = sorted_files[:limit]
    
    # 读取和解析事件文件
    event_data = []
    for file_path in limited_files:
        file_name = os.path.basename(file_path)
        timestamp = extract_timestamp(file_path).strftime("%Y-%m-%d %H:%M:%S")
        
        try:
            events = []
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            event_json = json.loads(line)
                            event = Event.from_dict(event_json)
                            
                            # 排除 STREAM 类型的事件
                            if event.event_type == EventType.STREAM:
                                continue
                                
                            events.append({
                                "event_type": event.event_type.name,
                                "content": json.dumps(event.content, ensure_ascii=False, indent=2) if event.content else "",
                                "metadata": json.dumps(event.metadata, ensure_ascii=False, indent=2) if event.metadata else ""
                            })
                        except json.JSONDecodeError:
                            logger.warning(f"无法解析事件行: {line}")
                        except Exception as e:
                            logger.warning(f"处理事件时出错: {e}")
            
            event_data.append({
                "file_name": file_name,
                "timestamp": timestamp,
                "events": events
            })
        except Exception as e:
            logger.error(f"读取事件文件出错 {file_path}: {e}")
            event_data.append({
                "file_name": file_name,
                "timestamp": timestamp,
                "error": str(e)
            })
    
    # 使用模板格式化事件数据
    return _format_events_prompt(event_data)

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