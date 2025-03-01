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

您可以通过以下几种方式加载插件：

1. 命令行参数：
   ```
   python -m autocoder.chat_auto_coder --plugin_dirs /path/to/plugins --plugins PluginClass1,PluginClass2
   ```

2. 配置文件：
   ```
   python -m autocoder.chat_auto_coder --plugin_config /path/to/config.json
   ```

3. 在运行时使用 `/plugins` 命令：
   ```
   /plugins list              # 列出可用插件
   /plugins load PluginClass  # 加载特定插件
   /plugins unload PluginName # 卸载插件
   /plugins                   # 显示已加载插件
   ```

## 创建插件

要创建插件，需要继承 `autocoder.plugins` 中的 `Plugin` 类：

```python
from autocoder.plugins import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    description = "我的自定义插件"
    version = "0.1.0"
    
    def __init__(self, config=None):
        super().__init__(config)
        # 初始化您的插件
    
    def initialize(self, manager):
        # 注册函数拦截
        manager.register_function_interception(self.name, "ask")
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
    
    def shutdown(self):
        # 清理资源
        pass
```

## 插件配置

插件可以使用 JSON 文件进行配置。示例：

```json
{
    "plugin_dirs": [
        "src/autocoder/plugins",
        "user_plugins"
    ],
    "plugins": {
        "MyPlugin": {
            "setting1": "value1",
            "setting2": 42
        }
    }
}
```

配置将传递给插件的构造函数。

## 内置插件

Chat Auto Coder 包含以下插件：

- `SamplePlugin`：演示基本功能的示例插件
- `GitHelperPlugin`：Git 命令插件

## 插件 API 参考

### Plugin 类

所有插件的基类：

- `name`：插件名称（字符串）
- `description`：插件描述（字符串）
- `version`：插件版本（字符串）
- `initialize(manager)`：插件加载时调用
- `get_commands()`：返回插件提供的命令字典
- `get_keybindings()`：返回插件提供的按键绑定列表
- `get_completions()`：返回命令补全字典
- `intercept_command(command, args)`：拦截并可能修改命令
- `intercept_function(func_name, args, kwargs)`：拦截并可能修改函数调用
- `post_function(func_name, result)`：处理函数结果
- `shutdown()`：插件卸载或应用程序退出时调用

### PluginManager 类

管理 Chat Auto Coder 的插件：

- `add_plugin_directory(directory)`：添加用于搜索插件的目录
- `discover_plugins()`：在插件目录中发现可用插件
- `load_plugin(plugin_class, config)`：加载并初始化插件
- `load_plugins_from_config(config)`：基于配置加载插件
- `get_plugin(name)`：通过名称获取插件
- `process_command(full_command)`：处理命令，允许插件拦截
- `wrap_function(original_func, func_name)`：包装函数以允许插件拦截
- `register_function_interception(plugin_name, func_name)`：注册插件对拦截函数的兴趣
- `get_all_commands()`：获取所有插件的所有命令
- `get_plugin_completions()`：获取所有插件的命令补全
- `shutdown_all()`：关闭所有插件 