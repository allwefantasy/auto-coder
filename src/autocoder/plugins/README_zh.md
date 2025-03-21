# Chat Auto Coder 插件系统

本目录包含 Chat Auto Coder 的插件系统，允许在运行时扩展应用程序的功能。

## 插件系统特性

- 向 Chat Auto Coder 添加新命令
- 拦截和修改现有命令
- 拦截和修改函数调用
- 添加自定义键绑定
- 提供命令补全功能
- 非侵入式架构（不需要修改现有代码）

## 使用插件

在运行时使用 `/plugins` 命令：
   ```
   /plugins /list              # 列出可用插件
   /plugins /load PluginClass  # 加载特定插件
   /plugins /unload PluginName # 卸载插件
   /plugins                   # 显示已加载插件
   ```

## 插件目录

Chat Auto Coder 支持两种类型的插件目录：

1. **项目特定插件目录**：仅在当前项目中可用。
2. **全局插件目录**：对当前用户的所有项目都可用。

### 管理插件目录

您可以使用 `/plugins/dirs` 命令管理插件目录：

```
/plugins/dirs                # 列出所有插件目录（全局和项目特定）
/plugins/dirs /add <path>    # 添加项目特定插件目录
/plugins/dirs /remove <path> # 删除项目特定插件目录
/plugins/dirs /clear         # 清除所有项目特定插件目录
```

全局插件目录存储在 `~/.auto-coder/plugins/global_plugin_dirs` 文件中，并在 Chat Auto Coder 启动时自动加载。它们在所有项目中保持可用。

要添加全局插件目录，您需要直接编辑全局插件目录文件，或使用代码中的API。

## 创建插件

要创建插件，需要继承 `autocoder.plugins` 中的 `Plugin` 类：

```python
from autocoder.plugins import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    description = "我的自定义插件"
    version = "0.1.0"
    
    def __init__(self, manager, config=None, config_path=None):
        super().__init__(manager, config, config_path)
        # 初始化您的插件
    
    def initialize(self):
        # 此方法用于插件自身的初始化
        # 您可以在这里设置资源、注册事件处理程序或执行任何启动任务
        # 下面的register_function_interception只是一个示例，说明您可能在这里做什么
        self.manager.register_function_interception(self.name, "ask")
        return True
    
    def get_commands(self):
        return {
            "my_command": (self.my_command_handler, "我的自定义命令"),
        }
    
    def my_command_handler(self, args):
        print(f"我的命令已执行，参数: {args}")
    
    def get_keybindings(self):
        return [
            ("c-m", self.my_keybinding_handler, "我的自定义按键绑定"),
        ]
    
    def my_keybinding_handler(self, event):
        print("我的按键被按下！")
    
    def intercept_command(self, command, args):
        # 返回 True, command, args 允许正常处理
        # 返回 False, new_command, new_args 接管处理
        return True, command, args
    
    def intercept_function(self, func_name, args, kwargs):
        # 根据需要修改 args 或 kwargs
        return True, args, kwargs
    
    def post_function(self, func_name, result):
        # 根据需要修改结果
        return result
    
    def export_config(self, config_path=None):
        # 导出插件配置用于持久化存储
        # 如果不需要配置，返回 None
        return self.config
    
    def shutdown(self):
        # 清理资源
        pass
```

## 插件配置

每个插件的配置单独存储在项目的 `.auto-coder/plugins/{plugin_id}/config.json` 目录中。插件管理器负责加载和保存这些配置。

全局插件目录存储在 `~/.auto-coder/plugins/global_plugin_dirs` 文件中，并对所有项目自动加载。

## 内置插件

Chat Auto Coder 包含以下插件：

- `SamplePlugin`：演示基本功能的示例插件
- `DynamicCompletionExamplePlugin`：演示动态命令补全功能的插件
- `GitHelperPlugin`：Git 命令插件


## 插件标识

每个插件通过 `id_name()` 类方法获取完整的模块和类名作为唯一标识符：

```python
@classmethod
def id_name(cls) -> str:
    """返回插件的唯一标识符，包括模块路径"""
    return f"{cls.__module__}.{cls.__name__}"
```

此标识符用于插件注册、加载和配置管理。

## 插件 API 参考

### Plugin 类

所有插件的基类：

- `name`：插件名称（字符串）
- `description`：插件描述（字符串）
- `version`：插件版本（字符串）
- `dynamic_cmds`：需要动态补全的命令列表（字符串列表）。此列表指定哪些命令应该根据当前上下文使用动态补全。例如，插件可以将其设置为 `["/my_command"]` 来表示 `/my_command` 应该有动态补全。
- `initialize()`：插件加载时调用。用于插件自身初始化，例如设置资源、连接服务或任何其他启动任务。初始化成功返回`True`，否则返回`False`。
- `get_commands()`：返回插件提供的命令字典
- `get_keybindings()`：返回插件提供的按键绑定列表
- `get_completions()`：返回命令补全字典
- `get_dynamic_completions(command, current_input)`：根据输入上下文返回动态补全选项
- `intercept_command(command, args)`：拦截并可能修改命令
- `intercept_function(func_name, args, kwargs)`：拦截并可能修改函数调用
- `post_function(func_name, result)`：处理函数结果
- `export_config(config_path)`：导出插件配置
- `shutdown()`：插件卸载或应用程序退出时调用

### PluginManager 类

管理 Chat Auto Coder 的插件：

- `add_plugin_directory(directory)`：添加用于搜索插件的目录（项目特定）
- `add_global_plugin_directory(directory)`：添加用于搜索插件的全局目录（对所有项目可用）
- `remove_plugin_directory(directory)`：删除项目特定插件目录
- `clear_plugin_directories()`：清除所有项目特定插件目录
- `load_global_plugin_dirs()`：从 ~/.auto-coder/plugins/global_plugin_dirs 加载全局插件目录
- `save_global_plugin_dirs()`：保存全局插件目录到 ~/.auto-coder/plugins/global_plugin_dirs
- `discover_plugins()`：在插件目录中发现可用插件
- `load_plugin(plugin_class, config)`：加载并初始化插件
- `load_plugins_from_config(config)`：基于配置加载插件
- `get_plugin(name)`：通过名称获取插件
- `process_command(full_command)`：处理命令，允许插件拦截
- `wrap_function(original_func, func_name)`：包装函数以允许插件拦截
- `register_function_interception(plugin_name, func_name)`：注册插件对拦截函数的兴趣
- `get_all_commands()`：获取所有插件的所有命令
- `get_plugin_completions()`：获取所有插件的命令补全
- `get_dynamic_completions(command, current_input)`：根据当前输入获取动态补全选项
- `load_runtime_cfg()`：加载插件的运行时配置
- `save_runtime_cfg()`：保存插件的运行时配置
- `shutdown_all()`：关闭所有插件

### 模块级别函数

`autocoder.plugins` 模块还提供以下函数：

- `register_global_plugin_dir(directory)`：在插件安装过程中将目录注册为全局插件目录。这是为插件安装脚本提供的便捷函数。

## 插件安装与注册

在创建插件安装脚本时，您可以使用 `register_global_plugin_dir` 模块级别函数自动将插件目录注册为全局插件目录。这使得插件对用户机器上的所有项目都可用。

### 示例：插件安装脚本

```python
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def install_plugin():
    """安装插件并全局注册。"""
    # 获取当前目录（插件代码所在位置）
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # 导入插件管理器模块
        sys.path.insert(0, str(Path(plugin_dir).parent))
        from autocoder.plugins import register_global_plugin_dir
        
        # 使用模块函数将插件目录全局注册
        register_global_plugin_dir(plugin_dir)
        print(f"✅ 成功注册插件目录：{plugin_dir}")
        print(f"该插件现在可用于所有 Chat Auto Coder 项目。")
            
        return True
    except Exception as e:
        print(f"❌ 插件安装过程中出错：{str(e)}")
        return False

if __name__ == "__main__":
    if install_plugin():
        print("安装成功完成！")
    else:
        print("安装失败。请查看上面的错误信息。") 