import os
from pathlib import Path
from threading import Lock
import pathspec

from typing import Callable, List

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
except ImportError:
    Observer = None
    FileSystemEventHandler = object

DEFAULT_EXCLUDES = [
    '.git', '.auto-coder', 'node_modules', '.mvn', '.idea',
    '__pycache__', '.venv', 'venv', 'dist', 'build', '.gradle', ".next"
]

class _IgnoreFileEventHandler(FileSystemEventHandler):
    def __init__(self, manager, file_path):
        super().__init__()
        self.manager = manager
        self.file_path = file_path

    def on_modified(self, event):
        # 只关心本文件的变化
        if os.path.abspath(event.src_path) == os.path.abspath(self.file_path):
            self.manager._on_ignore_file_changed(self.file_path)

    def on_created(self, event):
        if os.path.abspath(event.src_path) == os.path.abspath(self.file_path):
            self.manager._on_ignore_file_changed(self.file_path)

class IgnoreFileManager:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(IgnoreFileManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if hasattr(self, "_initialized") and self._initialized:
            return
        self._initialized = True
        self._spec = None
        self._ignore_file_paths = []
        self._callbacks: List[Callable[[], None]] = []
        self._observer = None
        self._event_handlers = []
        self._load_ignore_spec()
        self._setup_file_watchers()

    def _load_ignore_spec(self):
        ignore_patterns = []
        project_root = Path(os.getcwd())

        ignore_file_paths = [
            project_root / '.autocoderignore',
            project_root / '.auto-coder' / '.autocoderignore'
        ]
        self._ignore_file_paths = []
        for ignore_file in ignore_file_paths:
            if ignore_file.is_file():
                with open(ignore_file, 'r', encoding='utf-8') as f:
                    ignore_patterns = f.read().splitlines()
                self._ignore_file_paths.append(str(ignore_file))
                break  # 只用第一个找到的文件
        else:
            # 记录尝试过但不存在的文件
            for ignore_file in ignore_file_paths:
                self._ignore_file_paths.append(str(ignore_file))

        # 添加默认排除目录
        ignore_patterns.extend(DEFAULT_EXCLUDES)

        self._spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)

    def should_ignore(self, path: str) -> bool:
        rel_path = os.path.relpath(path, os.getcwd())
        # 标准化分隔符
        rel_path = rel_path.replace(os.sep, '/')
        return self._spec.match_file(rel_path)

    def _on_ignore_file_changed(self, file_path: str):
        # 重新加载规则
        self._load_ignore_spec()
        # 调用所有注册的回调
        for cb in self._callbacks:
            try:
                cb()
            except Exception as e:
                print(f"Error in ignore file event callback: {e}")

    def _setup_file_watchers(self):
        if Observer is None:
            print("警告：未安装 watchdog 库，无法监控 .autocoderignore 文件变化")
            return
        # 只设置一次
        if hasattr(self, "_watcher_started") and self._watcher_started:
            return
        self._watcher_started = True
        self._observer = Observer()
        # 监控所有可能的 ignore 文件路径
        for file_path in self._ignore_file_paths:
            parent = os.path.dirname(file_path)
            handler = _IgnoreFileEventHandler(self, file_path)
            self._event_handlers.append(handler)
            self._observer.schedule(handler, parent, recursive=False)
        self._observer.daemon = True
        self._observer.start()

    def register_file_event_callback(self, cb: Callable[[], None]):
        """注册 .autocoderignore 文件变化事件回调。"""
        if cb not in self._callbacks:
            self._callbacks.append(cb)

    def unregister_file_event_callback(self, cb: Callable[[], None]):
        if cb in self._callbacks:
            self._callbacks.remove(cb)

    def stop_watcher(self):
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None

# 对外提供单例
_ignore_manager = IgnoreFileManager()

def should_ignore(path: str) -> bool:
    return _ignore_manager.should_ignore(path)

def register_ignore_file_event_callback(cb: Callable[[], None]):
    """对外注册 .autocoderignore 文件变化回调接口"""
    _ignore_manager.register_file_event_callback(cb)

def unregister_ignore_file_event_callback(cb: Callable[[], None]):
    _ignore_manager.unregister_file_event_callback(cb)