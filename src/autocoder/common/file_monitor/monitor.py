# -*- coding: utf-8 -*-
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Set, Tuple, Union, Optional
from loguru import logger

# 尝试导入 watchfiles，如果失败则提示用户安装
try:
    from watchfiles import watch, Change
except ImportError:
    logger.error("错误：需要安装 'watchfiles' 库。请运行: pip install watchfiles")
    # 可以选择抛出异常或退出，这里仅打印信息
    # raise ImportError("watchfiles is required for FileMonitor")
    # 或者提供一个空的实现或禁用该功能
    Change = None # type: ignore
    watch = None # type: ignore


class FileMonitor:
    """
    使用 watchfiles 库监控指定根目录下文件或目录的变化。

    允许动态注册特定路径的回调函数，当这些路径发生变化时触发。
    
    此类实现了单例模式，确保全局只有一个监控实例。
    """
    
    # 单例实例
    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls, root_dir: Optional[str] = None):
        """
        实现单例模式。确保只创建一个 FileMonitor 实例。
        
        :param root_dir: 需要监控的根目录。如果已存在实例且提供了新的根目录，不会更改现有实例的根目录。
        :return: FileMonitor 的单例实例
        """
        with cls._instance_lock:
            if cls._instance is None:
                if root_dir is None:
                    raise ValueError("First initialization of FileMonitor requires a valid root_dir")
                cls._instance = super(FileMonitor, cls).__new__(cls)
                cls._instance._initialized = False  # 标记是否已初始化
            elif root_dir is not None and cls._instance.root_dir != os.path.abspath(root_dir):
                logger.warning(f"FileMonitor is already initialized with root directory '{cls._instance.root_dir}'.")
                logger.warning(f"New root directory '{root_dir}' will be ignored.")
        return cls._instance

    def __init__(self, root_dir: str):
        """
        初始化 FileMonitor。由于是单例，只有首次创建实例时才会执行初始化。

        :param root_dir: 需要监控的根目录。watchfiles 将监控此目录及其所有子目录。
        """
        # 如果已经初始化过，则跳过
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        if watch is None:
             raise ImportError("watchfiles is not installed or could not be imported.")

        self.root_dir = os.path.abspath(root_dir)
        if not os.path.isdir(self.root_dir):
            raise ValueError(f"Root directory '{self.root_dir}' does not exist or is not a directory.")

        # 存储回调: {absolute_path: [callback1, callback2, ...]}
        # 回调函数签名: callback(change_type: Change, changed_path: str)
        self._callbacks: Dict[str, List[Callable[[Change, str], None]]] = defaultdict(list)
        self._callback_lock = threading.Lock() # 保护 _callbacks 的访问

        self._stop_event = threading.Event() # 用于通知监控循环停止
        self._monitor_thread: Optional[threading.Thread] = None
        self._watch_stop_event = threading.Event() # watchfiles 停止事件

        self._initialized = True
        logger.info(f"FileMonitor singleton initialized for root directory: {self.root_dir}")

    @classmethod
    def get_instance(cls) -> Optional['FileMonitor']:
        """
        获取 FileMonitor 的单例实例。
        
        :return: FileMonitor 实例，如果尚未初始化则返回 None
        """
        return cls._instance

    @classmethod
    def reset_instance(cls):
        """
        重置单例实例。
        如果当前实例正在运行，则先停止它。
        """
        with cls._instance_lock:
            if cls._instance is not None:
                if cls._instance.is_running():
                    cls._instance.stop()
                cls._instance = None
                logger.info("FileMonitor singleton has been reset.")

    def register(self, path: Union[str, Path], callback: Callable[[Change, str], None]):
        """
        注册一个文件或目录路径以及对应的回调函数。

        如果注册的是目录，则该目录本身或其内部任何文件的变化都会触发回调。
        路径必须位于初始化时指定的 root_dir 内部。

        :param path: 要监控的文件或目录的路径（绝对或相对于当前工作目录）。
        :param callback: 当路径发生变化时调用的回调函数。
                         接收两个参数：变化类型 (watchfiles.Change) 和变化的文件/目录路径 (str)。
        """
        abs_path = os.path.abspath(str(path))

        # 检查路径是否在 root_dir 内部
        if not abs_path.startswith(self.root_dir):
            logger.warning(f"Path '{abs_path}' is outside the monitored root directory '{self.root_dir}' and cannot be registered.")
            return

        with self._callback_lock:
            self._callbacks[abs_path].append(callback)
            logger.info(f"Registered callback for path: {abs_path}")

    def unregister(self, path: Union[str, Path], callback: Optional[Callable[[Change, str], None]] = None):
        """
        取消注册一个文件或目录路径的回调函数。

        :param path: 要取消注册的文件或目录路径。
        :param callback: 要取消注册的特定回调函数。如果为 None，则移除该路径的所有回调。
        """
        abs_path = os.path.abspath(str(path))
        with self._callback_lock:
            if abs_path in self._callbacks:
                if callback:
                    try:
                        self._callbacks[abs_path].remove(callback)
                        logger.info(f"Unregistered specific callback for path: {abs_path}")
                        if not self._callbacks[abs_path]: # 如果列表为空，则删除键
                            del self._callbacks[abs_path]
                    except ValueError:
                        logger.warning(f"Callback not found for path: {abs_path}")
                else:
                    del self._callbacks[abs_path]
                    logger.info(f"Unregistered all callbacks for path: {abs_path}")
            else:
                 logger.warning(f"No callbacks registered for path: {abs_path}")

    def _monitor_loop(self):
        """
        监控线程的主循环，使用 watchfiles.watch。
        """
        logger.info(f"File monitor loop started for {self.root_dir}...")
        try:
            # watchfiles.watch 会阻塞直到 stop_event 被设置或发生错误
            for changes in watch(self.root_dir, stop_event=self._watch_stop_event, yield_on_timeout=True):
                if self._stop_event.is_set(): # 检查外部停止信号
                    logger.info("External stop signal received.")
                    break

                if not changes: # 超时时 changes 可能为空
                    continue

                # changes 是一个集合: {(Change.added, '/path/to/file'), (Change.modified, '/path/to/another')}
                triggered_callbacks: List[Tuple[Callable, Change, str]] = []

                with self._callback_lock:
                    # 检查每个变化是否与注册的路径匹配
                    for change_type, changed_path in changes:
                        abs_changed_path = os.path.abspath(changed_path)

                        # 检查是否有完全匹配的回调
                        if abs_changed_path in self._callbacks:
                            for cb in self._callbacks[abs_changed_path]:
                                triggered_callbacks.append((cb, change_type, abs_changed_path))

                        # 检查是否有父目录匹配的回调（如果变化发生在注册的目录下）
                        for registered_path, callbacks in self._callbacks.items():
                             # 确保检查的是目录且不是完全匹配（避免重复添加）
                            if os.path.isdir(registered_path) and \
                               abs_changed_path != registered_path and \
                               abs_changed_path.startswith(registered_path + os.sep):
                                for cb in callbacks:
                                     # 避免重复添加同一回调对于同一事件
                                     if (cb, change_type, abs_changed_path) not in triggered_callbacks:
                                        triggered_callbacks.append((cb, change_type, abs_changed_path))

                # 在锁外部执行回调，避免阻塞监控循环
                if triggered_callbacks:
                    for cb, ct, cp in triggered_callbacks:
                        try:
                            cb(ct, cp)
                        except Exception as e:
                            logger.error(f"Error executing callback {getattr(cb, '__name__', str(cb))} for change {ct} on {cp}: {e}")

        except Exception as e:
            logger.error(f"Error in file monitor loop: {e}")
        finally:
            logger.info("File monitor loop stopped.")

    def start(self):
        """
        启动文件监控后台线程。
        如果监控已在运行，则不执行任何操作。
        """
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            logger.info("Monitor is already running.")
            return

        logger.info("Starting file monitor...")
        self._stop_event.clear() # 重置外部停止事件
        self._watch_stop_event.clear() # 重置 watchfiles 停止事件
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info("File monitor started in background thread.")

    def stop(self):
        """
        停止文件监控线程。
        """
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            logger.info("Monitor is not running.")
            return

        logger.info("Stopping file monitor...")
        self._stop_event.set() # 设置外部停止标志
        self._watch_stop_event.set() # 触发 watchfiles 内部停止

        if self._monitor_thread:
             # 等待一小段时间让 watch() 循环检测到事件并退出
             # join() 超时是为了防止 watch() 因某些原因卡住导致主线程无限等待
             self._monitor_thread.join(timeout=5.0)
             if self._monitor_thread.is_alive():
                 logger.warning("Monitor thread did not stop gracefully after 5 seconds.")
             else:
                 logger.info("Monitor thread joined.")

        self._monitor_thread = None
        logger.info("File monitor stopped.")

    def is_running(self) -> bool:
        """
        检查监控线程是否正在运行。
        """
        return self._monitor_thread is not None and self._monitor_thread.is_alive()

