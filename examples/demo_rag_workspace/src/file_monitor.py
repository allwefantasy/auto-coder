
import os
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileChangeHandler(FileSystemEventHandler):
    def __init__(self, callback=None):
        self.callback = callback
        
    def on_modified(self, event):
        if not event.is_directory:
            print(f"文件被修改: {event.src_path}")
            if self.callback:
                self.callback(event.src_path)
                
    def on_created(self, event):
        if not event.is_directory:
            print(f"文件被创建: {event.src_path}")
            if self.callback:
                self.callback(event.src_path)
                
    def on_deleted(self, event):
        if not event.is_directory:
            print(f"文件被删除: {event.src_path}")
            if self.callback:
                self.callback(event.src_path)

class FileMonitor:
    def __init__(self, path, callback=None):
        self.path = path
        self.observer = Observer()
        self.handler = FileChangeHandler(callback)
        self.running = False
        
    def start(self):
        self.observer.schedule(self.handler, self.path, recursive=True)
        self.observer.start()
        self.running = True
        print(f"开始监控目录: {self.path}")
        
    def stop(self):
        if self.running:
            self.observer.stop()
            self.observer.join()
            self.running = False
            print(f"停止监控目录: {self.path}")
            
    def is_running(self):
        return self.running

# 使用示例
if __name__ == "__main__":
    def on_file_change(file_path):
        print(f"检测到文件变化: {file_path}")
        
    monitor = FileMonitor("./", on_file_change)
    try:
        monitor.start()
        # 保持程序运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        monitor.stop()
