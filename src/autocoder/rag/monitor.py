
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from loguru import logger
from typing import Optional, List, Callable

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            self.callback(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self.callback(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self.callback(event.src_path)

class FileMonitor:
    def __init__(self, path: str, callback: Callable, required_exts: Optional[List[str]] = None):
        self.path = path
        self.callback = callback
        self.required_exts = required_exts or []
        self.observer = Observer()
        self.handler = FileChangeHandler(self._filter_and_callback)

    def _filter_and_callback(self, file_path: str):
        if not self.required_exts or any(file_path.endswith(ext) for ext in self.required_exts):
            self.callback(file_path)

    def start(self):
        if not os.path.isdir(self.path):
            logger.error(f"Source directory does not exist: {self.path}")
            return False

        logger.info(f"Starting file monitor for directory: {self.path}")
        self.observer.schedule(self.handler, self.path, recursive=True)
        self.observer.start()
        return True

    def stop(self):
        self.observer.stop()
        self.observer.join()
        logger.info("File monitor stopped")

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.stop()
