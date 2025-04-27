import os
from pathlib import Path
from threading import Lock
import pathspec
import threading
from typing import Optional  # 添加Optional导入

# 尝试导入 FileMonitor
try:
    from autocoder.common.file_monitor.monitor import FileMonitor, Change
except ImportError:
    # 如果导入失败，提供一个空的实现
    print("警告: 无法导入 FileMonitor，忽略文件变更监控将不可用")
    FileMonitor = None
    Change = None

DEFAULT_EXCLUDES = [
    '.git', '.auto-coder', 'node_modules', '.mvn', '.idea',
    '__pycache__', '.venv', 'venv', 'dist', 'build', '.gradle',".next"
]


class IgnoreFileManager:
    _instance = None
    _lock = Lock()

    def __new__(cls, project_root: Optional[str] = None):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(IgnoreFileManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, project_root: Optional[str] = None):
        if self._initialized:
            return
        self._initialized = True
        self._spec = None
        self._ignore_file_path = None
        self._file_monitor = None
        self._project_root = project_root if project_root is not None else os.getcwd()
        self._load_ignore_spec()
        self._setup_file_monitor()

    def _load_ignore_spec(self):
        """加载忽略规则文件并解析规则"""
        ignore_patterns = []
        project_root = Path(self._project_root)

        ignore_file_paths = [
            project_root / '.autocoderignore',
            project_root / '.auto-coder' / '.autocoderignore'
        ]

        for ignore_file in ignore_file_paths:
            if ignore_file.is_file():
                with open(ignore_file, 'r', encoding='utf-8') as f:
                    ignore_patterns = f.read().splitlines()
                self._ignore_file_path = str(ignore_file)
                break

        # 添加默认排除目录
        ignore_patterns.extend(DEFAULT_EXCLUDES)

        self._spec = pathspec.PathSpec.from_lines('gitwildmatch', ignore_patterns)

    def _setup_file_monitor(self):
        """设置文件监控，当忽略文件变化时重新加载规则"""
        if FileMonitor is None or not self._ignore_file_path:
            return
        
        try:
            # 获取或创建 FileMonitor 实例
            root_dir = os.path.dirname(self._ignore_file_path)
            self._file_monitor = FileMonitor(root_dir=root_dir)
            
            # 注册忽略文件的回调
            self._file_monitor.register(self._ignore_file_path, self._on_ignore_file_changed)
                        
        except Exception as e:
            print(f"设置忽略文件监控时出错: {e}")

    def _on_ignore_file_changed(self, change_type: Change, changed_path: str):
        """当忽略文件发生变化时的回调函数"""
        if os.path.abspath(changed_path) == os.path.abspath(self._ignore_file_path):
            print(f"检测到忽略文件变化 ({change_type.name}): {changed_path}")
            self._load_ignore_spec()
            print("已重新加载忽略规则")

    def should_ignore(self, path: str) -> bool:
        """判断指定路径是否应该被忽略"""
        rel_path = os.path.relpath(path, self._project_root)
        # 标准化分隔符
        rel_path = rel_path.replace(os.sep, '/')
        return self._spec.match_file(rel_path)


# 对外提供的单例管理器
_ignore_manager = None

def should_ignore(path: str, project_root: Optional[str] = None) -> bool:
    """判断指定路径是否应该被忽略"""
    global _ignore_manager
    if _ignore_manager is None:
        _ignore_manager = IgnoreFileManager(project_root=project_root)
    return _ignore_manager.should_ignore(path)
