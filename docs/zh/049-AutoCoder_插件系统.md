# Chat Auto Coder 插件系统综合指南

## 核心设计理念
Chat Auto Coder 的插件系统采用轻量级非侵入架构，通过动态加载机制实现功能扩展。系统设计遵循以下原则：
1. **运行时扩展**：运行时即可加载/卸载插件
2. **功能拦截**：可修改现有命令和函数行为
3. **配置隔离**：每个插件的配置独立存储管理
4. **多级目录**：支持项目级和全局两种插件目录

---

## 核心功能特性
### 功能扩展
- **命令系统**：注册自定义交互命令（如 `/git/commit`）
- **键位绑定**：定义快捷键组合触发特定操作
- **智能补全**：提供静态/动态两种命令和参数补全方式
- **行为拦截**：
  - 命令拦截：修改/接管已有命令处理流程
  - 函数拦截：在函数执行前后注入自定义逻辑

### 配置管理

- **独立存储**：插件配置可存储在项目根目录 `.auto-coder/plugins/{插件}/`

## 实战使用指南

### 插件管理操作

```bash
coding@auto-coder.chat:~$ /plugins # 查看已加载插件
Loaded Plugins:
- git_helper (v0.1.0): Git helper plugin providing Git commands and status

coding@auto-coder.chat:~$ /plugins /list # 查看所有可用插件
Available Plugins:
- DynamicCompletionExamplePlugin (dynamic_completion_example): Demonstrates the dynamic completion feature
- GitHelperPlugin (git_helper): Git helper plugin providing Git commands and status
- SamplePlugin (sample_plugin): A sample plugin demonstrating the plugin system features

# 加载指定插件
coding@auto-coder.chat:~$ /plugins /load git_helper
# 卸载指定插件 
coding@auto-coder.chat:~$ /plugins /unload git_helper

# 管理项目插件目录
# 查看当前项目插件目录
coding@auto-coder.chat:~$ /plugins/dirs
# 添加项目级目录
coding@auto-coder.chat:~$ /plugins/dirs /add ./custom_plugins
# 清除所有项目级目录
coding@auto-coder.chat:~$ /plugins/dirs /clear
```

### 插件使用建议
1. **项目级插件**：适合特定项目使用场景，注册在项目根目录的 `plugins/` 下
2. **全局插件**：适合通用的工具类插件，注册在 `~/.auto-coder/plugins/`
3. **配置设计**：复杂插件建议实现 `export_config()` 可以实现配置持久化，下次启动时自动加载

---

## 插件开发模板
```python
from autocoder.plugins import Plugin

class CustomPlugin(Plugin):
    name = "demo_plugin"
    description = "示例功能插件"
    version = "1.0.0"
    
    def initialize(self):
        # 注册函数拦截（示例拦截ask）
        self.manager.register_function_interception(self.name, "ask")
        return True
    
    def get_commands(self):
        return {
            "/demo": (self.handle_demo, "示例命令")
        }
    
    def handle_demo(self, args):
        print(f"执行参数: {args}")
        return "命令执行成功"
```

### 插件分发和安装建议

- 插件开发包名建议使用 `autocoder-plugin-<plugin-name>`
- 插件安装到 AutoCoder 相同的 Env 中, 使用 `pip install autocoder-plugin-<plugin-name>` 安装
- 插件开发者建议提供一个安装脚本, 让用户将插件的目录添加到 AutoCoder 的插件全局目录列表，方便用户在所有项目中使用

---

## 最佳实践建议
1. **插件粒度**：单个插件聚焦解决特定问题域
2. **错误处理**：在关键函数添加 try-except 块保证系统稳定性
3. **性能优化**：耗时操作建议异步执行
4. **版本兼容**：在 `shutdown()` 方法中做好资源清理
5. **指令动态参数补全**：通过 `get_dynamic_completions()` 实现上下文感知参数的动态补全

---

## 内置工具插件

| 插件名称               | 功能描述                     |
|-----------------------|----------------------------|
| GitHelperPlugin       | Git常用操作集成           |

