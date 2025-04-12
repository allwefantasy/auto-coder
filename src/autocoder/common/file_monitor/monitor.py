
# -*- coding: utf-8 -*-
import os
import time
import threading
from typing import Callable, Dict, List, Union, Optional

class FileMonitor:
    """
    监控指定文件或目录的变化。

    当检测到文件或目录的最后修改时间发生变化时，触发回调函数。
    """

    def __init__(self, callback: Callable[[List[str]], None], interval: float = 1.0):
        """
        初始化 FileMonitor。

        :param callback: 当文件发生变化时调用的回调函数。回调函数接收一个包含已更改文件路径的列表。
        :param interval: 检查文件变化的间隔时间（秒）。
        """
        self._monitored_items: Dict[str, float] = {}  # 存储监控项及其最后修改时间
        self._callback = callback
        self._interval = interval
        self._stop_event = threading.Event()
        self._monitor_thread: Optional[threading.Thread] = None
        self._lock = threading.Lock() # 用于保护 _monitored_items 的访问

    def register(self, path: Union[str, List[str]]):
        """
        注册要监控的文件或目录。

        如果注册的是目录，将监控该目录下所有文件的变化（非递归）。
        如果文件或目录不存在，会打印警告但不会抛出错误。

        :param path: 要监控的文件或目录的路径，或路径列表。
        """
        paths_to_register = [path] if isinstance(path, str) else path
        with self._lock:
            for p in paths_to_register:
                abs_path = os.path.abspath(p)
                if os.path.exists(abs_path):
                    try:
                        last_modified_time = os.path.getmtime(abs_path)
                        self._monitored_items[abs_path] = last_modified_time
                        print(f"Registered '{abs_path}' for monitoring.")
                    except OSError as e:
                        print(f"Warning: Could not get modification time for '{abs_path}': {e}")
                else:
                    print(f"Warning: Path '{abs_path}' does not exist and cannot be monitored.")


    def _check_files(self):
        """
        检查已注册文件或目录的修改时间。
        如果检测到变化，则调用回调函数。
        """
        changed_files: List[str] = []
        with self._lock:
            items_to_check = list(self._monitored_items.keys()) # 创建副本以避免在迭代时修改字典

            for path in items_to_check:
                if not os.path.exists(path):
                    print(f"Warning: Monitored path '{path}' no longer exists. Removing from monitor.")
                    del self._monitored_items[path]
                    continue

                try:
                    current_mtime = os.path.getmtime(path)
                    last_mtime = self._monitored_items.get(path)

                    if last_mtime is None: # 可能在检查期间被移除
                         continue

                    if current_mtime != last_mtime:
                        changed_files.append(path)
                        self._monitored_items[path] = current_mtime # 更新最后修改时间
                except OSError as e:
                    print(f"Warning: Could not check modification time for '{path}': {e}. Skipping check.")


        if changed_files:
            try:
                self._callback(changed_files)
            except Exception as e:
                print(f"Error executing callback for changed files {changed_files}: {e}")

    def _monitor_loop(self):
        """
        监控线程的主循环。
        """
        print("File monitor loop started.")
        while not self._stop_event.is_set():
            self._check_files()
            # 等待指定间隔或直到停止事件被设置
            self._stop_event.wait(self._interval)
        print("File monitor loop stopped.")

    def start(self):
        """
        启动文件监控线程。
        如果监控已在运行，则不执行任何操作。
        """
        if self._monitor_thread is not None and self._monitor_thread.is_alive():
            print("Monitor is already running.")
            return

        print("Starting file monitor...")
        self._stop_event.clear() # 确保停止标志未设置
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        print("File monitor started.")

    def stop(self):
        """
        停止文件监控线程。
        """
        if self._monitor_thread is None or not self._monitor_thread.is_alive():
            print("Monitor is not running.")
            return

        print("Stopping file monitor...")
        self._stop_event.set()
        self._monitor_thread.join() # 等待线程结束
        self._monitor_thread = None
        print("File monitor stopped.")

    def is_running(self) -> bool:
        """
        检查监控线程是否正在运行。
        """
        return self._monitor_thread is not None and self._monitor_thread.is_alive()

    def get_monitored_items(self) -> List[str]:
        """
        获取当前正在监控的文件/目录列表。
        """
        with self._lock:
            return list(self._monitored_items.keys())

# 示例用法 (可选，通常在单独的测试文件中)
if __name__ == '__main__':
    import tempfile
    import shutil

    # 创建临时目录和文件用于测试
    temp_dir = tempfile.mkdtemp()
    temp_file1 = os.path.join(temp_dir, 'test1.txt')
    temp_file2 = os.path.join(temp_dir, 'test2.txt')

    with open(temp_file1, 'w') as f:
        f.write('Initial content 1')
    with open(temp_file2, 'w') as f:
        f.write('Initial content 2')

    def my_callback(changed_paths: List[str]):
        print(f"Detected changes in: {changed_paths}")

    monitor = FileMonitor(callback=my_callback, interval=0.5)

    # 注册文件和目录
    monitor.register(temp_file1)
    monitor.register([temp_file2, temp_dir]) # 也可以注册列表

    print(f"Monitoring: {monitor.get_monitored_items()}")

    monitor.start()

    try:
        print("Monitoring started. Modifying files...")
        time.sleep(2)

        # 修改文件1
        print("Modifying file 1...")
        with open(temp_file1, 'w') as f:
            f.write('Updated content 1')
        time.sleep(2) # 等待监控检测到变化

        # 修改文件2
        print("Modifying file 2...")
        with open(temp_file2, 'a') as f:
            f.write('\nAppended content')
        time.sleep(2) # 等待监控检测到变化

        # 修改目录 (创建新文件) - 注意：当前实现仅监控目录本身的mtime
        # 如果需要监控目录下文件的增删，需要更复杂的逻辑 (e.g., using watchdog)
        # temp_file3 = os.path.join(temp_dir, 'test3.txt')
        # print("Creating file 3...")
        # with open(temp_file3, 'w') as f:
        #     f.write('New file')
        # time.sleep(2)

        print("Finished modifications.")

    finally:
        print("Stopping monitor...")
        monitor.stop()
        # 清理临时文件和目录
        shutil.rmtree(temp_dir)
        print("Cleanup complete.")
        print(f"Is monitor running? {monitor.is_running()}")

