import os
from pathlib import Path
from threading import Lock
import pathspec

_DEFAULT_IGNORES = [
    '.git', '.auto-coder', 'node_modules', '.mvn', '.idea',
    '__pycache__', '.venv', 'venv', 'dist', 'build', '.gradle'
]

class IgnoreFileUtils:
    _instance = None
    _lock = Lock()

    def __new__(cls, project_root=None):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._init(project_root)
            return cls._instance

    def _init(self, project_root):
        self.project_root = Path(project_root).resolve() if project_root else Path.cwd().resolve()
        self.spec = self._load_ignore_spec()

    def _load_ignore_spec(self):
        ignore_file_paths = [
            self.project_root / '.autocoderignore',
            self.project_root / '.auto-coder' / '.autocoderignore'
        ]
        patterns = []

        # Try to load patterns from ignore files
        for path in ignore_file_paths:
            if path.is_file():
                with open(path, 'r', encoding='utf-8') as f:
                    patterns.extend(
                        line.strip() for line in f if line.strip() and not line.strip().startswith('#')
                    )
                break  # only load the first found ignore file

        # Always add default ignores
        patterns.extend(_DEFAULT_IGNORES)

        # Deduplicate
        patterns = list(set(patterns))

        return pathspec.PathSpec.from_lines('gitwildmatch', patterns)

    def should_ignore(self, path):
        """
        Check if the given path (file or directory) should be ignored.
        """
        p = Path(path)
        try:
            rel_path = p.resolve().relative_to(self.project_root)
        except ValueError:
            # Path is outside project root, don't ignore
            return False

        # Always use posix style for matching
        rel_path_str = rel_path.as_posix()
        # For directories, add trailing slash to match folder rules
        if p.is_dir():
            rel_path_str += '/'

        return self.spec.match_file(rel_path_str)

# Singleton accessor
def get_ignore_utils(project_root=None):
    return IgnoreFileUtils(project_root)