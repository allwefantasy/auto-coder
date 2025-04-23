
---
description: 使用 watchfiles 实现文件系统监控
globs: ["*/*.py"]
alwaysApply: false
---

# 使用 watchfiles 实现高效的文件系统监控

## 简要说明
提供一个基于 `watchfiles` 和 `pathspec` 的文件监控器。它能在后台线程中监控指定目录（及其子目录）的文件变化（增、删、改），并允许注册针对特定文件、目录或模式（如 `*.py`, `data/**/*.csv`）的回调函数。适用于需要对文件系统变化做出实时响应的场景。

## 典型用法
```python
# 导入必要的库
import os
import time
import threading
from typing import Optional
from loguru import logger

# 假设 FileMonitor 类定义在 'my_file_monitor_module.py'
# from my_file_monitor_module import FileMonitor, Change
# 为了示例独立，我们直接使用 monitor.py 中的类
from autocoder.common.file_monitor.monitor import FileMonitor, Change, get_file_monitor

# --- 回调函数示例 ---
def handle_py_change(change_type: Change, changed_path: str):
    """处理 .py 文件变化的回调"""
    logger.info(f"Python 文件变更 ({change_type.name}): {changed_path}")
    # 在这里添加处理逻辑，例如重新加载模块、触发构建等

def handle_config_change(change_type: Change, changed_path: str):
    """处理 config.ini 文件变化的回调"""
    logger.info(f"配置文件变更 ({change_type.name}): {changed_path}")
    # 在这里添加重新加载配置的逻辑

# --- 主程序 ---
if __name__ == "__main__":
    # 1. 定义要监控的根目录
    project_root = os.path.abspath("./monitored_area") # 监控 ./monitored_area 目录
    os.makedirs(project_root, exist_ok=True) # 确保目录存在
    logger.info(f"监控根目录: {project_root}")

    # 2. 获取 FileMonitor 单例实例 (首次调用需提供 root_dir)
    try:
        file_monitor = get_file_monitor(root_dir=project_root)
        # 或者使用 FileMonitor(root_dir=project_root)
    except ImportError as e:
        logger.error(f"初始化 FileMonitor 失败: {e}")
        exit(1)
    except ValueError as e:
        logger.error(f"初始化 FileMonitor 失败: {e}")
        exit(1)

    # 3. 注册回调函数
    # 注册监控所有 Python 文件 (使用 glob 模式)
    file_monitor.register("**/*.py", handle_py_change)
    
    # 注册监控特定的配置文件 (精确路径)
    config_file_path = os.path.join(project_root, "config.ini")
    # 创建一个示例文件以便监控
    with open(config_file_path, "w") as f:
        f.write("[settings]\nkey=value\n")
    file_monitor.register(config_file_path, handle_config_change)

    # 注册监控特定目录 (目录内任何变化都会触发)
    data_dir = os.path.join(project_root, "data")
    os.makedirs(data_dir, exist_ok=True)
    def handle_data_dir_change(change_type: Change, changed_path: str):
        logger.info(f"Data 目录变更 ({change_type.name}): {changed_path}")
    file_monitor.register(data_dir, handle_data_dir_change)


    # 4. 启动监控 (在后台线程运行)
    if not file_monitor.is_running():
        file_monitor.start()
        logger.info("文件监控已启动...")
    else:
        logger.info("文件监控已在运行中。")

    # 5. 保持主线程运行 (或执行其他任务)
    try:
        logger.info("主线程运行中，按 Ctrl+C 停止...")
        # 模拟文件操作以触发回调
        time.sleep(5)
        logger.info("模拟创建 Python 文件...")
        with open(os.path.join(project_root, "new_script.py"), "w") as f: f.write("print('hello')")
        time.sleep(2)
        logger.info("模拟修改配置文件...")
        with open(config_file_path, "a") as f: f.write("new_key=new_value\n")
        time.sleep(2)
        logger.info("模拟在 data 目录创建文件...")
        with open(os.path.join(data_dir, "report.txt"), "w") as f: f.write("data report")
        time.sleep(5)

    except KeyboardInterrupt:
        logger.info("收到停止信号...")
    finally:
        # 6. 停止监控
        if file_monitor.is_running():
            logger.info("正在停止文件监控...")
            file_monitor.stop()
            logger.info("文件监控已停止。")
        # 可选：重置单例，以便下次重新初始化
        # FileMonitor.reset_instance()

```

## 依赖说明
- `watchfiles>=0.10.0`: 核心的文件监控库。 (`pip install watchfiles`)
- `pathspec>=0.9.0`: 用于高效处理 `.gitignore` 风格的路径模式匹配。 (`pip install pathspec`)
- `loguru` (可选, 用于日志记录): 示例中使用了 loguru，可替换为标准库 `logging`。 (`pip install loguru`)
- Python >= 3.7 (建议, `watchfiles` 可能有此要求)

## 学习来源
从 `/Users/allwefantasy/projects/auto-coder/src/autocoder/common/file_monitor/monitor.py` 文件中的 `FileMonitor` 类提取。该类封装了 `watchfiles` 的核心功能，并增加了 `pathspec` 支持和回调管理。
