# -*- coding: utf-8 -*-
import os
import threading
import time
import fnmatch
from collections import defaultdict
from pathlib import Path
from typing import Callable, Dict, List, Set, Tuple, Union, Optional, Any
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

# 尝试导入 pathspec，如果失败则提示用户安装
try:
    import pathspec
except ImportError:
    logger.error("错误：需要安装 'pathspec' 库。请运行: pip install pathspec")
    pathspec = None  # type: ignore

# 用于区分普通路径和模式路径
class PathType:
    LITERAL = 'literal'  # 普通的精确路径
    PATTERN = 'pattern'  # 模式路径（glob, gitignore等）

# 注册的路径信息结构
class RegisteredPath:
    def __init__(self, path: str, path_type: str, spec=None):
        self.path = path
        self.path_type = path_type
        self.spec = spec  # pathspec规范对象，用于高效匹配
        
    def __eq__(self, other):
        if not isinstance(other, RegisteredPath):
            return False
        return self.path == other.path and self.path_type == other.path_type
    
    def __hash__(self):
        return hash((self.path, self.path_type))


class FileMonitor:
    """
    使用 watchfiles 库监控指定根目录下文件或目录的变化。

    允许动态注册特定路径的回调函数，当这些路径发生变化时触发。
    支持多种路径模式，包括glob模式，如 "**/*.py" 匹配任何Python文件。
    使用pathspec库实现高效的路径匹配。
    
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
             
        if pathspec is None:
             raise ImportError("pathspec is not installed or could not be imported.")

        self.root_dir = os.path.abspath(root_dir)
        if not os.path.isdir(self.root_dir):
            raise ValueError(f"Root directory '{self.root_dir}' does not exist or is not a directory.")

        # 存储回调: {registered_path: [callback1, callback2, ...]}
        # 回调函数签名: callback(change_type: Change, changed_path: str)
        self._callbacks: Dict[RegisteredPath, List[Callable[[Change, str], None]]] = defaultdict(list)
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

    def _is_pattern(self, path: str) -> bool:
        """
        判断一个路径是否为模式（包含通配符）。
        
        :param path: 要检查的路径
        :return: 如果路径包含通配符，则返回True
        """
        # 检查是否包含通配符字符
        return any(c in path for c in ['*', '?', '[', ']'])

    def _create_pathspec(self, pattern: str) -> Any:
        """
        创建一个pathspec匹配器。
        
        :param pattern: 匹配模式
        :return: pathspec匹配器对象
        """
        # 将单个模式转换为pathspec格式
        # 使用GitWildMatchPattern，它支持.gitignore样式的通配符，功能最全面
        return pathspec.PathSpec([pathspec.patterns.GitWildMatchPattern(pattern)])

    def register(self, path: Union[str, Path], callback: Callable[[Change, str], None]):
        """
        注册一个文件或目录路径以及对应的回调函数。
        
        支持多种模式路径，如 "**/*.py" 匹配任何Python文件。
        如果注册的是目录，则该目录本身或其内部任何文件的变化都会触发回调。
        路径必须位于初始化时指定的 root_dir 内部。

        :param path: 要监控的文件或目录的路径（绝对或相对于当前工作目录）。
                     支持多种模式，如 "src/**/*.py"。
        :param callback: 当路径发生变化时调用的回调函数。
                         接收两个参数：变化类型 (watchfiles.Change) 和变化的文件/目录路径 (str)。
        """
        path_str = str(path)
        
        # 检查是否是模式路径
        is_pattern = self._is_pattern(path_str)
        
        # 对于非模式路径，路径必须是绝对路径或相对于当前工作目录的路径
        if not is_pattern:
            abs_path = os.path.abspath(path_str)
            
            # 检查路径是否在 root_dir 内部
            if not abs_path.startswith(self.root_dir):
                logger.warning(f"Path '{abs_path}' is outside the monitored root directory '{self.root_dir}' and cannot be registered.")
                return
                
            reg_path = RegisteredPath(abs_path, PathType.LITERAL)
            
            with self._callback_lock:
                self._callbacks[reg_path].append(callback)
                logger.info(f"Registered callback for literal path: {abs_path}")
        else:
            # 对于模式路径，先处理路径格式
            if os.path.isabs(path_str):
                # 如果是绝对路径，检查是否在监控根目录下
                if not path_str.startswith(self.root_dir):
                    logger.warning(f"Pattern '{path_str}' is outside the monitored root directory '{self.root_dir}' and cannot be registered.")
                    return
                # 转换为相对于root_dir的路径用于pathspec匹配
                pattern = os.path.relpath(path_str, self.root_dir)
            else:
                # 对于相对路径，直接使用
                pattern = path_str
                
            # 创建pathspec匹配器
            path_spec = self._create_pathspec(pattern)
            
            # 注册带有pathspec的模式
            reg_path = RegisteredPath(pattern, PathType.PATTERN, spec=path_spec)
            
            with self._callback_lock:
                self._callbacks[reg_path].append(callback)
                logger.info(f"Registered callback for pattern: {pattern}")

    def unregister(self, path: Union[str, Path], callback: Optional[Callable[[Change, str], None]] = None):
        """
        取消注册一个文件或目录路径的回调函数。

        :param path: 要取消注册的文件或目录路径，包括模式路径。
        :param callback: 要取消注册的特定回调函数。如果为 None，则移除该路径的所有回调。
        """
        path_str = str(path)
        is_pattern = self._is_pattern(path_str)
        
        # 查找匹配的注册路径
        target_reg_path = None
        with self._callback_lock:
            if not is_pattern:
                abs_path = os.path.abspath(path_str)
                for reg_path in self._callbacks.keys():
                    if reg_path.path_type == PathType.LITERAL and reg_path.path == abs_path:
                        target_reg_path = reg_path
                        break
            else:
                # 对于模式路径，尝试找到完全匹配的模式
                if os.path.isabs(path_str):
                    pattern = os.path.relpath(path_str, self.root_dir)
                else:
                    pattern = path_str
                
                for reg_path in self._callbacks.keys():
                    if reg_path.path_type == PathType.PATTERN and reg_path.path == pattern:
                        target_reg_path = reg_path
                        break
            
            # 如果找到匹配的路径，执行取消注册
            if target_reg_path:
                if callback:
                    try:
                        self._callbacks[target_reg_path].remove(callback)
                        logger.info(f"Unregistered specific callback for path: {path_str}")
                        if not self._callbacks[target_reg_path]: # 如果列表为空，则删除键
                            del self._callbacks[target_reg_path]
                    except ValueError:
                        logger.warning(f"Callback not found for path: {path_str}")
                else:
                    del self._callbacks[target_reg_path]
                    logger.info(f"Unregistered all callbacks for path: {path_str}")
            else:
                logger.warning(f"No callbacks registered for path: {path_str}")

    def _path_matches(self, file_path: str, reg_path: RegisteredPath) -> bool:
        """
        检查文件路径是否匹配注册的路径。
        
        :param file_path: 要检查的文件路径
        :param reg_path: 注册的路径对象
        :return: 如果路径匹配，则返回True
        """
        if reg_path.path_type == PathType.LITERAL:
            # 对于精确路径，检查完全匹配或者是否在目录内
            if file_path == reg_path.path:
                return True
            if os.path.isdir(reg_path.path) and file_path.startswith(reg_path.path + os.sep):
                return True
            return False
        
        elif reg_path.path_type == PathType.PATTERN:
            # 对于模式路径，使用pathspec进行匹配
            if reg_path.spec:
                # 获取相对于根目录的路径进行匹配
                rel_path = os.path.relpath(file_path, self.root_dir)
                return reg_path.spec.match_file(rel_path)
            return False
        
        return False

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

                        # 遍历所有注册的路径和回调
                        for reg_path, callbacks in self._callbacks.items():
                            # 使用优化后的路径匹配方法
                            if self._path_matches(abs_changed_path, reg_path):
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


def get_file_monitor(root_dir: str) -> FileMonitor:
    """
    获取 FileMonitor 的单例实例。
    """
    return FileMonitor(root_dir)

