# Chat Auto Coder 插件开发指南

## 第一部分：插件开发教程 - GitHelperPlugin开发流程

我们以内置的 `git_helper` 插件为例，介绍插件的开发流程。

### 1. 插件基础结构

首先，我们创建一个基本的插件类：

```python
"""
Git Helper Plugin for Chat Auto Coder.
Provides convenient Git commands and information display.
"""

import os
import subprocess
from typing import Any, Callable, Dict, List, Optional, Tuple

from autocoder.plugins import Plugin, PluginManager


class GitHelperPlugin(Plugin):
    """Git helper plugin for the Chat Auto Coder."""

    name = "git_helper"
    description = "Git helper plugin providing Git commands and status"
    version = "0.1.0"
```

### 2. 实现初始化逻辑

在初始化方法中设置插件基础配置和检测环境：

```python
def __init__(self, manager: PluginManager, config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None):
    """Initialize the Git helper plugin."""
    super().__init__(manager, config, config_path)
    self.git_available = self._check_git_available()
    self.default_branch = self.config.get("default_branch", "main")

def _check_git_available(self) -> bool:
    """Check if Git is available."""
    try:
        subprocess.run(
            ["git", "--version"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=True,
        )
        return True
    except Exception:
        return False

def initialize(self) -> bool:
    """Initialize the plugin.

    Returns:
        True if initialization was successful
    """
    if not self.git_available:
        print(f"[{self.name}] 警告: Git不可用，某些功能受限")
        return True

    print(f"[{self.name}] Git助手插件已初始化")
    return True
```

### 3. 注册命令接口

定义插件提供的命令列表：

```python
def get_commands(self) -> Dict[str, Tuple[Callable, str]]:
    """Get commands provided by this plugin.

    Returns:
        A dictionary of command name to handler and description
    """
    return {
        "git/status": (self.git_status, "显示Git仓库状态"),
        "git/commit": (self.git_commit, "提交更改"),
        "git/branch": (self.git_branch, "显示或创建分支"),
        "git/checkout": (self.git_checkout, "切换分支"),
        "git/diff": (self.git_diff, "显示更改差异"),
        "git/log": (self.git_log, "显示提交历史"),
        "git/pull": (self.git_pull, "拉取远程更改"),
        "git/push": (self.git_push, "推送本地更改到远程"),
        "git/reset": (self.handle_reset, "重置当前分支到指定状态 (hard/soft/mixed)"),
    }
```

### 4. 实现命令补全功能

为命令提供静态和动态补全：

```python
def get_completions(self) -> Dict[str, List[str]]:
    """Get completions provided by this plugin.

    Returns:
        A dictionary mapping command prefixes to completion options
    """
    completions = {
        "/git/status": [],
        "/git/commit": [],
        "/git/branch": [],
        "/git/checkout": [],
        "/git/diff": [],
        "/git/log": [],
        "/git/pull": [],
        "/git/push": [],
        "/git/reset": ["hard", "soft", "mixed"],
    }

    # 添加分支补全
    if self.git_available:
        try:
            branches = self._get_git_branches()
            completions["/git/checkout"] = branches
            completions["/git/branch"] = branches + [
                "--delete",
                "--all",
                "--remote",
                "new",
            ]
        except Exception:
            pass

    return completions
```

### 5. 实现通用工具方法

创建复用的工具方法，处理Git命令执行：

```python
def _run_git_command(self, args: List[str]) -> Tuple[int, str, str]:
    """Run a Git command.

    Args:
        args: The command arguments

    Returns:
        A tuple of (return_code, stdout, stderr)
    """
    if not self.git_available:
        return 1, "", "Git不可用"

    try:
        process = subprocess.run(
            ["git"] + args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        return process.returncode, process.stdout, process.stderr
    except Exception as e:
        return 1, "", str(e)

def _get_git_branches(self) -> List[str]:
    """Get Git branches.

    Returns:
        A list of branch names
    """
    code, stdout, _ = self._run_git_command(
        ["branch", "--list", "--format=%(refname:short)"]
    )
    if code == 0:
        return [b.strip() for b in stdout.splitlines() if b.strip()]
    return []
```

### 6. 实现具体命令处理逻辑

以下是几个典型命令的实现示例：

```python
def git_status(self, args: str) -> None:
    """Handle the git/status command."""
    code, stdout, stderr = self._run_git_command(["status"])
    if code == 0:
        print(f"\n{stdout}")
    else:
        print(f"Error: {stderr}")

def git_commit(self, args: str) -> None:
    """Handle the git/commit command."""
    if not args:
        print("请提供提交信息，例如: /git/commit 'Fix bug in login'")
        return

    # 首先执行添加所有更改 (git add .)
    self._run_git_command(["add", "."])

    # 执行提交
    code, stdout, stderr = self._run_git_command(["commit", "-m", args])
    if code == 0:
        print(f"\n{stdout}")
    else:
        print(f"Error: {stderr}")

def handle_reset(self, args: str) -> None:
    """Handle the git/reset command.
    
    Args:
        args: The reset mode (hard/soft/mixed) and optional commit hash
    """
    if not args:
        print("请提供重置模式 (hard/soft/mixed) 和可选的提交哈希")
        return
        
    args_list = args.split()
    mode = args_list[0]
    commit = args_list[1] if len(args_list) > 1 else "HEAD"
    
    if mode not in ["hard", "soft", "mixed"]:
        print(f"错误: 无效的重置模式 '{mode}'，必须是 hard/soft/mixed 之一")
        return
        
    code, stdout, stderr = self._run_git_command(["reset", f"--{mode}", commit])
    if code == 0:
        print(f"\n{stdout}")
        print(f"成功将仓库重置为 {mode} 模式到 {commit}")
    else:
        print(f"Error: {stderr}")
```

### 7. 实现插件关闭方法

最后，实现资源清理和关闭逻辑：

```python
def shutdown(self) -> None:
    """Shutdown the plugin."""
    print(f"[{self.name}] Git助手插件已关闭")
```

---

## 第二部分：核心API参考

### Plugin 基类

插件必须继承 `Plugin` 基类并实现以下主要方法：

| 方法/属性 | 描述 | 返回值 |
|---------|------|-------|
| `name` | 插件名称（小写+下划线） | `str` |
| `description` | 插件功能描述 | `str` |
| `version` | 插件版本号 | `str` |
| `initialize()` | 插件初始化方法 | `bool` |
| `get_commands()` | 返回提供的命令 | `Dict[str, Tuple[Callable, str]]` |
| `get_keybindings()` | 返回提供的键绑定 | `List[Tuple[str, Callable, str]]` |
| `get_completions()` | 返回静态补全选项 | `Dict[str, List[str]]` |
| `get_dynamic_completions()` | 返回动态补全选项 | `List[str]` |
| `intercept_command()` | 拦截命令执行 | `Tuple[bool, str, str]` |
| `intercept_function()` | 拦截函数调用 | `Tuple[bool, Tuple, Dict]` |
| `post_function()` | 处理函数结果 | `Any` |
| `export_config()` | 导出插件配置 | `Dict[str, Any]` |
| `shutdown()` | 插件关闭清理 | `None` |

### PluginManager 关键方法

插件管理器提供以下核心功能：

```python
# 插件目录管理
manager.add_plugin_directory(directory)  # 添加项目级插件目录
manager.add_global_plugin_directory(directory)  # 添加全局插件目录
manager.clear_plugin_directories()  # 清除项目级插件目录

# 插件发现与加载
manager.discover_plugins()  # 在插件目录中查找插件
manager.load_plugin(plugin_class, config)  # 加载特定插件类
manager.get_plugin(name)  # 根据名称获取已加载插件

# 拦截功能
manager.register_function_interception(plugin_name, func_name)  # 注册函数拦截
manager.process_command(full_command)  # 处理命令，允许插件拦截

# 补全支持
manager.get_all_commands()  # 获取所有插件命令
manager.get_plugin_completions()  # 获取所有插件的补全
manager.get_dynamic_completions(command, current_input)  # 获取动态补全

# 配置管理
manager.load_runtime_cfg()  # 加载插件配置
manager.save_runtime_cfg()  # 保存插件配置
```

---

## 第三部分：插件开发最佳实践

### 1. 命令结构设计

使用分层命名可以让命令更有组织性：

```python
def get_commands(self):
    return {
        "namespace/command": (self.handler, "描述"),
        "namespace/subnamespace/command": (self.handler, "描述"),
    }
```

例如，Git插件使用 `git/` 前缀为所有命令分组。

### 2. 错误处理与用户反馈

始终在命令处理中捕获异常并提供友好的错误提示：

```python
def git_branch(self, args: str) -> None:
    try:
        # ... 代码逻辑 ...
    except Exception as e:
        print(f"分支操作失败: {str(e)}")
        # 可以提供帮助信息
        print("使用格式: /git/branch [name] 或 /git/branch --list")
```

### 3. 合理使用工具方法

将常用功能抽象为通用工具方法，避免代码重复：

```python
# GitHelperPlugin 中的工具方法示例
def _run_git_command(self, args: List[str]) -> Tuple[int, str, str]:
    # 统一处理Git命令执行
    # ... 代码实现 ...
```

### 4. 命令补全设计

补全既可以是静态的，也可以是动态生成的：

```python
# 静态补全
def get_completions(self):
    return {"/git/reset": ["hard", "soft", "mixed"]}

# 动态补全 (例如根据仓库中的实际分支)
def _get_git_branches(self):
    # 动态获取Git分支列表
    # ... 代码实现 ...
```

### 5. 优雅的初始化与关闭

确保插件能够优雅地处理各种环境情况：

```python
def initialize(self):
    if not self._check_dependency():
        print("警告: 依赖不可用，部分功能受限")
        return True  # 依然允许插件加载，但功能受限
    return True

def shutdown(self):
    # 清理资源，关闭连接等
    print(f"[{self.name}] 插件已关闭")
```

### 6. 配置持久化管理

使用配置机制保存插件状态：

```python
def export_config(self, config_path=None):
    return {
        "default_branch": self.default_branch,
        "other_setting": self.some_value,
    }
```

### 7. 资源管理与性能优化

缓存开销大的操作结果，特别是外部命令调用：

```python
def _get_git_branches(self):
    # 可以添加缓存机制，避免频繁调用外部命令
    if not hasattr(self, "_cached_branches") or time.time() - self._last_branch_update > 60:
        self._cached_branches = self._fetch_branches()
        self._last_branch_update = time.time()
    return self._cached_branches
```

### 8. 用户体验优化

为复杂命令添加帮助信息和交互引导：

```python
def git_reset(self, args: str) -> None:
    if not args or args == "help":
        print("用法: /git/reset [mode] [commit]")
        print("模式:")
        print("  - hard: 丢弃工作区和暂存区的修改")
        print("  - soft: 保留工作区和暂存区的修改")
        print("  - mixed: 默认模式，保留工作区但重置暂存区")
        return
    # ... 继续实现 ...
```

### 9. 插件文档和注释

为插件添加详细文档和代码注释，帮助用户和其他开发者理解：

```python
"""
Git Helper Plugin for Chat Auto Coder.
提供Git操作集成，包括状态查询、提交、分支管理等功能。

使用方法:
- /git/status: 显示当前仓库状态
- /git/commit <message>: 提交所有更改
...
"""
```

---

通过学习Git插件的实现，你可以掌握Chat Auto Coder插件开发的核心模式。插件系统的灵活性允许你扩展和定制Auto Coder，使其适应各种开发场景和工作流程。
```
