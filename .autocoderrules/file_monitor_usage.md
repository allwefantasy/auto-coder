---
description: Explains how to use the FileMonitor singleton for file system monitoring.
globs:
  - src/autocoder/common/file_monitor/monitor.py
  - src/autocoder/common/file_monitor/__init__.py
  - examples/demo_file_monitor.py # If an example file exists
alwaysApply: false
---

# FileMonitor Usage Guide

The `FileMonitor` class, accessed via `get_file_monitor`, provides a singleton service for monitoring file system changes within a specified project root directory using `watchfiles` and `pathspec`.

## Key Steps:

1.  **Get Instance**: Use `get_file_monitor(root_dir)` to obtain the singleton instance. The `root_dir` is required on the first call.
    ```python
    from autocoder.common.file_monitor.monitor import get_file_monitor, Change
    monitor = get_file_monitor("/path/to/project/root")
    ```

2.  **Register Callbacks**: Use `monitor.register(path, callback)` to associate functions with file paths or patterns.
    *   `path`: Can be a specific file/directory path or a `pathspec` compatible pattern (e.g., `"**/*.py"`, `"data/"`). Patterns are relative to the root directory.
    *   `callback`: A function with the signature `callback(change_type: Change, changed_path: str)`.
    ```python
    def handle_change(change_type: Change, changed_path: str):
        print(f"Detected {change_type.name} in {changed_path}")

    # Register specific file
    monitor.register("config.yaml", handle_change)
    # Register directory (and its contents)
    monitor.register("src/utils/", handle_change)
    # Register pattern
    monitor.register("**/*.md", handle_change)
    ```

3.  **Start Monitoring**: Call `monitor.start()` to begin watching for changes in a background thread.
    ```python
    if not monitor.is_running():
        monitor.start()
    ```

4.  **Stop Monitoring**: Call `monitor.stop()` to halt the background thread.
    ```python
    monitor.stop()
    ```

5.  **Unregister**: Use `monitor.unregister(path, callback=None)` to remove callbacks.

## Example Callback:

```python
from watchfiles import Change

def my_custom_callback(change_type: Change, changed_path: str):
    if change_type == Change.added:
        print(f"New file added: {changed_path}")
    elif change_type == Change.modified:
        print(f"File modified: {changed_path}")
    elif change_type == Change.deleted:
        print(f"File deleted: {changed_path}")

# Register it
monitor.register("important_data.csv", my_custom_callback)
```

Remember to handle potential `ImportError` if `watchfiles` or `pathspec` are not installed, and `ValueError` if the root directory is invalid during the first initialization.