# -*- coding: utf-8 -*-
import os
import threading
import time
import tempfile
import shutil
from pathlib import Path
from typing import Callable, Optional

# 尝试导入 watchfiles，如果失败则提示用户安装
try:
    from watchfiles import watch, Change
except ImportError:
    print("错误：需要安装 'watchfiles' 库。请运行: pip install watchfiles")
    # 可以选择抛出异常或退出，这里仅打印信息
    # raise ImportError("watchfiles is required for FileMonitor")
    # 或者提供一个空的实现或禁用该功能
    Change = None # type: ignore
    watch = None # type: ignore

# 从原始模块导入 FileMonitor 类
# 注意：确保 PYTHONPATH 包含项目根目录，或者使用相对导入（如果结构允许）
try:
    # 假设项目根目录在 PYTHONPATH 中
    from autocoder.common.file_monitor.monitor import FileMonitor
except ImportError as e:
    print(f"无法导入 FileMonitor: {e}")
    print("请确保项目根目录在 PYTHONPATH 中，或者调整导入路径。")
    # 提供一个假的 FileMonitor 以便脚本至少能运行（但监控无效）
    class FileMonitor:
        _instance = None
        def __new__(cls, *args, **kwargs):
            if cls._instance is None:
                cls._instance = super(FileMonitor, cls).__new__(cls)
            return cls._instance
        def __init__(self, root_dir: str): print("警告：FileMonitor 未正确导入，监控将无法工作。")
        def register(self, path, callback): pass
        def unregister(self, path, callback=None): pass
        def start(self): pass
        def stop(self): pass
        def is_running(self): return False
        @classmethod
        def get_instance(cls): return cls._instance
        @classmethod
        def reset_instance(cls): cls._instance = None


# --- 示例用法 ---
if __name__ == '__main__':

    # 确保 watchfiles 可用
    if watch is None:
        print("Cannot run example: watchfiles is not installed.")
    else:
        # 创建临时目录作为监控根目录
        # 使用相对路径确保在项目内创建，如果需要的话
        # temp_root_dir = tempfile.mkdtemp(prefix="fm_root_")
        # 或者在 examples 目录下创建
        example_run_dir = os.path.join(os.path.dirname(__file__), "fm_run_temp")
        if os.path.exists(example_run_dir):
            shutil.rmtree(example_run_dir)
        os.makedirs(example_run_dir)
        temp_root_dir = example_run_dir

        print(f"Created temporary root directory for example: {temp_root_dir}")

        # 在根目录下创建子目录和文件
        sub_dir = os.path.join(temp_root_dir, "subdir")
        os.makedirs(sub_dir)
        file_in_root = os.path.join(temp_root_dir, "root_file.txt")
        file_in_sub = os.path.join(sub_dir, "sub_file.txt")

        with open(file_in_root, "w") as f:
            f.write("Root content")
        with open(file_in_sub, "w") as f:
            f.write("Sub content")

        print(f"Created test files/dirs:\n - {file_in_root}\n - {sub_dir}\n - {file_in_sub}")

        # 定义回调函数
        def root_file_callback(change_type: Change, changed_path: str):
            print(f"CALLBACK [Root File Specific]: Change '{change_type.name}' detected in '{changed_path}'")

        def subdir_callback_1(change_type: Change, changed_path: str):
            print(f"CALLBACK [Subdir 1]: Change '{change_type.name}' detected in '{changed_path}' (triggered by subdir watch)")

        def subdir_callback_2(change_type: Change, changed_path: str):
             print(f"CALLBACK [Subdir 2]: Change '{change_type.name}' detected in '{changed_path}' (another callback for subdir)")

        def any_change_callback(change_type: Change, changed_path: str):
            print(f"CALLBACK [Any Change in Root]: Change '{change_type.name}' detected in '{changed_path}' (triggered by root dir watch)")

        # 演示单例模式前清理任何可能存在的实例
        print("\n--- 重置 FileMonitor 单例，确保从一个干净的状态开始 ---")
        FileMonitor.reset_instance()
        
        # 初始化监控器 - 第一个实例将成为唯一的实例
        print("\n--- 创建第一个 FileMonitor 实例 ---")
        monitor1 = FileMonitor(root_dir=temp_root_dir)

        # 注册回调
        monitor1.register(file_in_root, root_file_callback)
        monitor1.register(sub_dir, subdir_callback_1)
        
        # 演示单例模式 - 第二个实例实际上是同一个对象
        print("\n--- 尝试创建第二个 FileMonitor 实例（会返回相同的单例） ---")
        monitor2 = FileMonitor(root_dir=os.path.join(temp_root_dir, "另一个目录"))  # 不同的目录，但会被忽略
        
        # 验证这是同一个实例
        print(f"monitor1 与 monitor2 是同一个对象: {monitor1 is monitor2}")
        
        # 使用第二个引用来添加更多回调
        monitor2.register(sub_dir, subdir_callback_2)  # 同一个目录注册第二个回调
        monitor2.register(temp_root_dir, any_change_callback)  # 监控根目录下的任何变化

        # 通过类方法获取实例
        print("\n--- 通过类方法获取实例 ---")
        monitor3 = FileMonitor.get_instance()
        print(f"通过 get_instance() 获取的实例与 monitor1 相同: {monitor1 is monitor3}")

        # 启动监控
        monitor1.start()  # 使用任何实例引用都可以
        print("Monitor started. Waiting for changes...")
        time.sleep(1) # 给点时间让监控器稳定

        try:
            # --- 执行一些文件操作来触发回调 ---
            print("\n--- Modifying root file ---")
            with open(file_in_root, "w") as f:
                f.write("Updated root content")
            time.sleep(1.5) # 等待 watchfiles 检测并处理

            print("\n--- Modifying file in subdir ---")
            with open(file_in_sub, "a") as f:
                f.write("\nAppended sub content")
            time.sleep(1.5)

            print("\n--- Creating new file in subdir ---")
            new_file_in_sub = os.path.join(sub_dir, "new_sub.txt")
            with open(new_file_in_sub, "w") as f:
                f.write("Newly created")
            time.sleep(1.5)

            print("\n--- Deleting file in subdir ---")
            os.remove(new_file_in_sub)
            time.sleep(1.5)

            print("\n--- Unregistering one subdir callback ---")
            monitor3.unregister(sub_dir, subdir_callback_1)  # 使用第三个引用来取消注册
            time.sleep(0.5)

            print("\n--- Modifying file in subdir again (only one subdir callback should fire) ---")
            with open(file_in_sub, "w") as f:
                f.write("Final sub content")
            time.sleep(1.5)


            print("\n--- Finished file operations ---")

        except Exception as e:
            print(f"An error occurred during file operations: {e}")
        finally:
            # 停止监控
            print("\n--- Stopping monitor ---")
            # 可以使用任何实例引用或类方法来停止
            print("使用 monitor2 停止监控...")
            monitor2.stop()
            
            # 清理临时文件和目录
            print("--- Cleaning up temporary directory ---")
            # shutil.rmtree(temp_root_dir, ignore_errors=True) # ignore_errors 以防万一
            # 在某些系统上，即使监控停止，文件句柄可能不会立即释放，导致 rmtree 失败
            # 增加一点延迟或重试逻辑可能有助于解决这个问题
            attempts = 3
            while attempts > 0:
                try:
                    shutil.rmtree(temp_root_dir)
                    print(f"Successfully removed temporary directory: {temp_root_dir}")
                    break
                except OSError as e:
                    attempts -= 1
                    print(f"Warning: Failed to remove temp directory (attempt {3-attempts}): {e}. Retrying in 1 second...")
                    if attempts == 0:
                        print(f"Error: Could not remove temporary directory {temp_root_dir} after multiple attempts.")
                    time.sleep(1)

            # 最后，重置单例
            print("\n--- 重置 FileMonitor 单例 ---")
            FileMonitor.reset_instance()
            print(f"监控器实例是否已重置? {FileMonitor.get_instance() is None}")
            print("Example finished.")
