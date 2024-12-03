from autocoder.rag.cache.base_cache import BaseCacheManager
from typing import Dict, List,Any,Optional
import os
import threading
from loguru import logger
from watchfiles import watch, Change
from autocoder.rag.variable_holder import VariableHolder
from autocoder.common import SourceCode
from autocoder.rag.utils import process_file_in_multi_process,process_file_local
from watchfiles import Change, DefaultFilter, awatch, watch


class AutoCoderRAGDocListener(BaseCacheManager):
    cache: Dict[str, Dict] = {}
    ignore_dirs = [
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".venv",
        ".cache",
        ".idea",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".hypothesis",
    ]
    ignore_entity_patterns = [
        r"\.py[cod]$",
        r"\.___jb_...___$",
        r"\.sw.$",
        "~$",
        r"^\.\#",
        r"^\.DS_Store$",
        r"^flycheck_",
        r"^test.*$",
    ]

    def __init__(self, path: str, ignore_spec, required_exts: List) -> None:
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.stop_event = threading.Event()

        # connect list
        self.ignore_entity_patterns.extend(self._load_ignore_file())
        self.file_filter = DefaultFilter(
            ignore_dirs=self.ignore_dirs,
            ignore_paths=[],
            ignore_entity_patterns=self.ignore_entity_patterns,
        )
        self.load_first()
        # 创建一个新线程来执行open_watch
        self.watch_thread = threading.Thread(target=self.open_watch)
        # 将线程设置为守护线程,这样主程序退出时,这个线程也会自动退出
        self.watch_thread.daemon = True
        # 启动线程
        self.watch_thread.start()

    def stop(self):
        self.stop_event.set()
        self.watch_thread.join()

    def __del__(self):
        self.stop()

    def load_first(self):
        files_to_process = self.get_all_files()
        if not files_to_process:
            return
        for item in files_to_process:
            self.update_cache(item)

    def update_cache(self, file_path):
        source_code = process_file_local(file_path)
        self.cache[file_path] = {
            "file_path": file_path,
            "content": [c.model_dump() for c in source_code],
        }
        logger.info(f"update cache: {file_path}")
        logger.info(f"current cache: {self.cache.keys()}")

    def remove_cache(self, file_path):
        del self.cache[file_path]
        logger.info(f"remove cache: {file_path}")
        logger.info(f"current cache: {self.cache.keys()}")

    def open_watch(self):
        logger.info(f"start monitor: {self.path}...")
        for changes in watch(
            self.path, watch_filter=self.file_filter, stop_event=self.stop_event
        ):
            for change in changes:
                (action, path) = change
                if action == Change.added or action == Change.modified:
                    self.update_cache(path)
                elif action == Change.deleted:
                    self.remove_cache(path)

    def get_cache(self,options:Optional[Dict[str,Any]]=None):
        return self.cache

    def _load_ignore_file(self):
        serveignore_path = os.path.join(self.path, ".serveignore")
        gitignore_path = os.path.join(self.path, ".gitignore")

        if os.path.exists(serveignore_path):
            with open(serveignore_path, "r") as ignore_file:
                patterns = ignore_file.readlines()
                return [pattern.strip() for pattern in patterns]
        elif os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as ignore_file:
                patterns = ignore_file.readlines()
                return [pattern.strip() for pattern in patterns]
        return []

    def get_all_files(self) -> List[str]:
        all_files = []
        for root, dirs, files in os.walk(self.path,followlinks=True):
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            if self.ignore_spec:
                relative_root = os.path.relpath(root, self.path)
                dirs[:] = [
                    d
                    for d in dirs
                    if not self.ignore_spec.match_file(os.path.join(relative_root, d))
                ]
                files = [
                    f
                    for f in files
                    if not self.ignore_spec.match_file(os.path.join(relative_root, f))
                ]

            for file in files:
                if self.required_exts and not any(
                    file.endswith(ext) for ext in self.required_exts
                ):
                    continue

                file_path = os.path.join(root, file)
                absolute_path = os.path.abspath(file_path)
                all_files.append(absolute_path)

        return all_files