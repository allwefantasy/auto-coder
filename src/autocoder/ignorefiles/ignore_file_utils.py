
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
        if self._initialized:
            return
        self._initialized = True
        self._spec = None
        self._load_ignore_spec()

    def _load_ignore_spec(self):
        ignore_patterns = []
        project_root = Path(os.getcwd())

        ignore_file_paths = [
            project_root / '.autocoderignore',
            project_root / '.auto-coder' / '.autocoderignore'
        ]

        for ignore_file in ignore_file_paths:
            if ignore_file.is_file():
                with open(ignore_file, 'r', encoding='utf-8') as f:
                    ignore_patterns = f.read().splitlines()
                break

        # 添加默认排除目录
        ignore_patterns.extend(DEFAULT_EXCLUDES)

        self._spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)

    def should_ignore(self, path: str) -> bool:
        rel_path = os.path.relpath(path, os.getcwd())
        # 标准化分隔符
        rel_path = rel_path.replace(os.sep, '/')
        return self._spec.match_file(rel_path)


# 对外提供单例
_ignore_manager = IgnoreFileManager()

def should_ignore(path: str) -> bool:
    return _ignore_manager.should_ignore(path)
