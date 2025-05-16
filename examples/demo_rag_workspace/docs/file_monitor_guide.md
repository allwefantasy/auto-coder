
# 文件监控系统使用指南

## 概述

文件监控系统用于实时监控目录中的文件变化，并在文件被创建、修改或删除时触发回调函数。

## 主要功能

1. 监控指定目录及其子目录中的文件变化
2. 支持自定义回调函数处理文件变化事件
3. 可以启动和停止监控

## 使用方法

### 初始化监控器

```python
from file_monitor import FileMonitor

# 创建监控器实例
monitor = FileMonitor("/path/to/directory", callback_function)
```

### 启动监控

```python
# 启动监控
monitor.start()
```

### 停止监控

```python
# 停止监控
monitor.stop()
```

### 检查监控状态

```python
# 检查监控是否正在运行
is_running = monitor.is_running()
```

## 注意事项

1. 监控器使用 watchdog 库实现，确保已安装该依赖
2. 回调函数应该是轻量级的，避免在回调中执行耗时操作
3. 在程序退出前记得调用 stop() 方法停止监控
