
import os
from pathlib import Path
from threading import Lock
import pathspec

DEFAULT_EXCLUDES = [
    '.git', '.auto-coder', 'node_modules', '.mvn', '.idea',
    '__pycache__', '.venv', 'venv', 'dist', 'build', '.gradle',".next"
]

import os
from pathlib import Path
from threading import Lock
import pathspec

DEFAULT_EXCLUDES = [
    '.git', '.auto-coder', 'node_modules', '.mvn', '.idea',
    '__pycache__', '.venv', 'venv', 'dist', 'build', '.gradle',".next"
]

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
        if hasattr(self, '_initialized') and self._initialized:
            return
        self._initialized = True
        self._spec = None
        self._ignore_file_paths = []
        self._project_root = Path(os.getcwd())
        self._ignore_file_paths = [
            self._project_root / '.autocoderignore',
            self._project_root / '.auto-coder' / '.autocoderignore'
        ]
        self._load_ignore_spec()
        self._setup_file_monitor()

    def _load_ignore_spec(self):
        ignore_patterns = []
        for ignore_file in self._ignore_file_paths:
            if ignore_file.is_file():
                with open(ignore_file, 'r', encoding='utf-8') as f:
                    ignore_patterns = f.read().splitlines()
                break

        # 添加默认排除目录
        ignore_patterns.extend(DEFAULT_EXCLUDES)
        self._spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)

    def _setup_file_monitor(self):
        try:
            from autocoder.common.file_monitor.monitor import FileMonitor
            from watchfiles import Change
        except Exception:
            # 监控不可用则跳过
            return

        # 只监控已存在的 ignore 文件
        for ignore_file in self._ignore_file_paths:
            if ignore_file.is_file():
                monitor = FileMonitor(root_dir=str(self._project_root))
                def make_reload_callback(ignore_file_path):
                    def _reload_callback(change_type, changed_path):
                        if change_type.name in ('modified', 'added', 'deleted'):
                            print(f"[IgnoreFileManager] Detected change ({change_type.name}) in {changed_path}, reloading ignore spec.")
                            self._load_ignore_spec()
                    return _reload_callback
                monitor.register(str(ignore_file), make_reload_callback(str(ignore_file)))
        # Note: 不做 unregister，ignore 文件一般不频繁变化

    def should_ignore(self, path: str) -> bool:
        rel_path = os.path.relpath(path, os.getcwd())
        # 标准化分隔符
        rel_path = rel_path.replace(os.sep, '/')
        return self._spec.match_file(rel_path)

# 对外提供单例
_ignore_manager = IgnoreFileManager()

def should_ignore(path: str) -> bool:
    return _ignore_manager.should_ignore(path)