import os
import threading
from typing import Optional, Dict, Any, List, Tuple
import uuid
from datetime import datetime
import glob
import json
import re
import time
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
    _cleanup_thread: Optional[threading.Thread] = None
    _stop_cleanup = threading.Event()
    _max_event_files = 100  # 最大保留的事件文件数量
    _cleanup_interval = 60  # 清理线程执行间隔，单位秒
    
    @classmethod
    def get_instance(cls, event_file: Optional[str] = None) -> EventManager:
        """
        Get an EventManager instance for the specified event file.
        
        Args:
            event_file: Event file path to use as key. If None, returns the default instance.
            
        Returns:
            EventManager: The appropriate EventManager instance
        """
        # 确保清理线程已启动
        cls._ensure_cleanup_thread_started()
        
        if event_file is None:
            # Use default instance logic
            if cls._default_instance is None:
                logger.info("Creating new default EventManager instance.")
                event_store_path = os.path.join(".auto-coder", "events", "events.jsonl")
                logger.debug(f"Default EventManager using event store: {event_store_path}")
                cls._default_instance = EventManager(JsonlEventStore(event_store_path))
            else:
                logger.debug("Returning existing default EventManager instance.")
            return cls._default_instance
        
        # If event_file is provided, use it as a key to store/retrieve EventManager instances
        if event_file not in cls._instances:
            logger.info(f"Creating new EventManager instance for event file: {event_file}")
            cls._instances[event_file] = EventManager(JsonlEventStore(event_file))  
        else:
            logger.debug(f"Returning existing EventManager instance for event file: {event_file}")
        
        return cls._instances[event_file]
    
    @classmethod
    def reset_instance(cls) -> None:
        """
        重置单例实例。主要用于测试或需要更改事件文件时。
        """
        with cls._lock:
            if cls._default_instance is not None:
                logger.info("Resetting default EventManager instance.")
                cls._default_instance = None
            else:
                logger.debug("Default EventManager instance was already None. No reset needed.")
    
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
    
    @classmethod
    def _ensure_cleanup_thread_started(cls) -> None:
        """
        确保清理线程已启动。如果尚未启动，则启动线程。
        """
        with cls._lock:
            if cls._cleanup_thread is None or not cls._cleanup_thread.is_alive():
                logger.info("启动事件文件清理线程")
                cls._stop_cleanup.clear()
                cls._cleanup_thread = threading.Thread(
                    target=cls._cleanup_event_files_thread,
                    daemon=True,
                    name="EventFilesCleanupThread"
                )
                cls._cleanup_thread.start()
    
    @classmethod
    def _cleanup_event_files_thread(cls) -> None:
        """
        定时清理线程的主函数。定期执行清理操作，确保事件目录只保留最新的指定数量文件。
        """
        logger.info(f"事件文件清理线程已启动，将保留最新的{cls._max_event_files}个文件")
        while not cls._stop_cleanup.is_set():
            try:
                cls._cleanup_event_files()
                # 等待指定时间或直到停止信号
                cls._stop_cleanup.wait(cls._cleanup_interval)
            except Exception as e:
                logger.error(f"事件文件清理过程中发生错误: {e}")
                # 出错后等待一段时间再重试
                time.sleep(60)
    
    @classmethod
    def _cleanup_event_files(cls) -> None:
        """
        清理事件文件，只保留最新的指定数量文件。
        """
        logger.info("开始清理事件文件...")
        
        # 确定事件文件所在目录
        events_dir = os.path.join(os.getcwd(),".auto-coder", "events")
        
        # 确保目录存在
        if not os.path.exists(events_dir):
            logger.warning(f"事件目录不存在: {events_dir}")
            return
        
        # 获取所有事件文件
        event_file_pattern = os.path.join(events_dir, "*.jsonl")
        event_files = glob.glob(event_file_pattern)
        
        if not event_files:
            logger.info(f"未找到任何事件文件: {event_file_pattern}")
            return
        
        # 排除默认的events.jsonl文件
        event_files = [f for f in event_files if os.path.basename(f) != "events.jsonl"]
        
        if len(event_files) <= cls._max_event_files:            
            return
        
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
        
        # 保留最新的文件，删除其余文件
        files_to_keep = sorted_files[:cls._max_event_files]
        files_to_delete = sorted_files[cls._max_event_files:]
        
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
                logger.info(f"已删除旧事件文件: {file_path}")
            except Exception as e:
                logger.error(f"删除事件文件失败 {file_path}: {e}")
        
        logger.info(f"事件文件清理完成，删除了{len(files_to_delete)}个旧文件，保留了{len(files_to_keep)}个最新文件")
    
    @classmethod
    def stop_cleanup_thread(cls) -> None:
        """
        停止清理线程，通常在应用程序退出时调用。
        """
        logger.info("正在停止事件文件清理线程...")
        cls._stop_cleanup.set()
        if cls._cleanup_thread and cls._cleanup_thread.is_alive():
            cls._cleanup_thread.join(timeout=5)
            if cls._cleanup_thread.is_alive():
                logger.warning("清理线程未在指定时间内停止")
            else:
                logger.info("清理线程已成功停止")

def get_event_file_path(file_id:str,project_path: Optional[str] = None) -> str:
    if project_path is None:
        return os.path.join(os.getcwd(),".auto-coder", "events", f"{file_id}.jsonl")
    else:
        return os.path.join(project_path, ".auto-coder", "events", f"{file_id}.jsonl")

def gengerate_event_file_path(project_path: Optional[str] = None) -> Tuple[str,str]:
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
    
    # 要使用绝对路径，否则会被认为产生两个event_manager
    if project_path is None:
        full_path = os.path.join(os.getcwd(),".auto-coder", "events", file_name)
    else:   
        full_path = os.path.join(project_path, ".auto-coder", "events", file_name)
    
    logger.info(f"Generated event file path: {full_path}, file_id: {file_id}")
    return full_path, file_id

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
    logger.info(f"Generating events prompt with limit={limit}, project_path={project_path}")
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
        logger.info(f"No event files found in pattern: {event_file_pattern}")
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