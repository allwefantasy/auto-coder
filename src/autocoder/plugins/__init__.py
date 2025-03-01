"""
Plugin system for Chat Auto Coder.
This module provides the base classes and functionality for creating and managing plugins.
"""

import importlib
import inspect
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union


class Plugin:
    """Base class for all plugins."""

    name: str = "base_plugin"
    description: str = "Base plugin class"
    version: str = "0.1.0"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize the plugin.

        Args:
            config: Optional configuration dictionary for the plugin
        """
        self.config = config or {}

    def initialize(self, manager: "PluginManager") -> bool:
        """Initialize the plugin. Called when the plugin is loaded.

        Args:
            manager: The plugin manager instance

        Returns:
            True if initialization was successful, False otherwise
        """
        return True

    def get_commands(self) -> Dict[str, Tuple[Callable, str]]:
        """Get the commands provided by this plugin.

        Returns:
            A dictionary mapping command names to (handler, description) tuples
        """
        return {}

    def get_keybindings(self) -> List[Tuple[str, Callable, str]]:
        """Get the keybindings provided by this plugin.

        Returns:
            A list of (key_combination, handler, description) tuples
        """
        return []

    def get_completions(self) -> Dict[str, List[str]]:
        """Get the completions provided by this plugin.

        Returns:
            A dictionary mapping command prefixes to lists of completion options
        """
        return {}

    def export_config(self) -> Optional[Dict[str, Any]]:
        """导出插件配置，用于持久化存储。

        默认实现会返回插件的 self.config 属性。
        子类可以覆盖此方法，以提供自定义的配置导出逻辑。

        Returns:
            包含插件配置的字典，如果没有配置需要导出则返回 None
        """
        return self.config if self.config else None

    def get_dynamic_completions(
        self, command: str, current_input: str
    ) -> List[Tuple[str, str]]:
        """Get dynamic completions based on the current command context.

        This method provides context-aware completions for commands that need
        dynamic options based on the current state or user input.

        Args:
            command: The base command (e.g., "/example select")
            current_input: The full current input including the command

        Returns:
            A list of tuples containing (completion_text, display_text)
        """
        return []

    def intercept_command(
        self, command: str, args: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Intercept a command before it's processed.

        Args:
            command: The command name (without the /)
            args: The command arguments

        Returns:
            A tuple of (should_continue, modified_command, modified_args)
            If should_continue is False, the original command processing will be skipped
        """
        return True, command, args

    def intercept_function(
        self, func_name: str, args: List[Any], kwargs: Dict[str, Any]
    ) -> Tuple[bool, List[Any], Dict[str, Any]]:
        """Intercept a function call before it's executed.

        Args:
            func_name: The name of the function
            args: The positional arguments
            kwargs: The keyword arguments

        Returns:
            A tuple of (should_continue, modified_args, modified_kwargs)
            If should_continue is False, the original function call will be skipped
        """
        return True, args, kwargs

    def post_function(self, func_name: str, result: Any) -> Any:
        """Process a function result after it's executed.

        Args:
            func_name: The name of the function
            result: The result of the function call

        Returns:
            The possibly modified result
        """
        return result

    def shutdown(self) -> None:
        """Shutdown the plugin. Called when the application is exiting."""
        pass


class PluginManager:
    """Manages plugins for the Chat Auto Coder."""

    def __init__(self):
        """Initialize the plugin manager."""
        self.plugins: Dict[str, Plugin] = {}
        self.command_handlers: Dict[str, Tuple[Callable, str, str]] = (
            {}
        )  # command -> (handler, description, plugin_name)
        self.intercepted_functions: Dict[str, List[str]] = (
            {}
        )  # function_name -> [plugin_names]
        self.plugin_dirs: List[str] = []
        self.runtime_cfg_path = None
        self._discover_plugins_cache: List[Type[Plugin]] = None  # type: ignore

    @property
    def cached_discover_plugins(self) -> List[Type[Plugin]]:
        if self._discover_plugins_cache is None:
            self._discover_plugins_cache = self.discover_plugins()
        return self._discover_plugins_cache

    def add_plugin_directory(self, directory: str) -> None:
        """Add a directory to search for plugins.

        Args:
            directory: The directory path
        """
        if os.path.isdir(directory) and directory not in self.plugin_dirs:
            self.plugin_dirs.append(directory)
            if directory not in sys.path:
                sys.path.append(directory)
            # 当目录变化时保存配置
            self.save_runtime_cfg()
            self._discover_plugins_cache = None  # type: ignore

    def discover_plugins(self) -> List[Type[Plugin]]:
        """Discover available plugins in the plugin directories.

        Returns:
            A list of plugin classes
        """
        discovered_plugins: List[Type[Plugin]] = []

        for plugin_dir in self.plugin_dirs:
            for filename in os.listdir(plugin_dir):
                if filename.endswith(".py") and not filename.startswith("_"):
                    module_name = filename[:-3]
                    try:
                        # Fully qualify module name with path information
                        plugin_dir_basename = os.path.basename(plugin_dir)
                        parent_dir = os.path.basename(os.path.dirname(plugin_dir))

                        if (
                            parent_dir == "autocoder"
                            and plugin_dir_basename == "plugins"
                        ):
                            # For built-in plugins
                            full_module_name = f"autocoder.plugins.{module_name}"
                        else:
                            # For external plugins
                            full_module_name = module_name

                        # Try to import using the determined module name
                        try:
                            module = importlib.import_module(full_module_name)
                        except ImportError:
                            # Fallback to direct module name
                            module = importlib.import_module(module_name)

                        for name, obj in inspect.getmembers(module):
                            if (
                                inspect.isclass(obj)
                                and issubclass(obj, Plugin)
                                and obj is not Plugin
                            ):
                                discovered_plugins.append(obj)
                    except (ImportError, AttributeError) as e:
                        print(f"Error loading plugin module {module_name}: {e}")

        return discovered_plugins

    def load_plugin(
        self, plugin_class: Type[Plugin], config: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Load and initialize a plugin.

        Args:
            plugin_class: The plugin class to load
            config: Optional configuration for the plugin

        Returns:
            True if the plugin was loaded successfully, False otherwise
        """
        try:
            plugin = plugin_class(config)
            if plugin.initialize(self):
                self.plugins[plugin.name] = plugin

                # Register commands
                for cmd, (handler, desc) in plugin.get_commands().items():
                    self.command_handlers[f"/{cmd}"] = (handler, desc, plugin.name)

                # 当插件加载成功时保存配置
                self.save_runtime_cfg()
                return True
            return False
        except Exception as e:
            print(f"Error loading plugin {plugin_class.__name__}: {e}")
            return False

    def load_plugins_from_config(self, config: Dict[str, Any]) -> None:
        """Load plugins based on configuration.

        Args:
            config: Configuration dictionary with plugin settings
        """
        if "plugin_dirs" in config:
            for directory in config["plugin_dirs"]:
                self.add_plugin_directory(directory)

        if "plugins" in config:
            discovered_plugins = {p.__name__: p for p in self.discover_plugins()}
            for plugin_name, plugin_config in config["plugins"].items():
                if plugin_name in discovered_plugins:
                    self.load_plugin(discovered_plugins[plugin_name], plugin_config)

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name.

        Args:
            name: The name of the plugin

        Returns:
            The plugin instance, or None if not found
        """
        return self.plugins.get(name)

    def process_command(
        self, full_command: str
    ) -> Optional[Tuple[str, Callable, List[str]]]:
        """Process a command, allowing plugins to intercept it.

        Args:
            full_command: The full command string including the /

        Returns:
            A tuple of (plugin_name, handler, args) if a plugin should handle the command,
            None if it should be handled by the main program
        """
        if not full_command.startswith("/"):
            return None

        parts = full_command.split(maxsplit=1)
        command = parts[0]
        args = parts[1] if len(parts) > 1 else ""

        # Check if any plugin wants to intercept this command
        command_without_slash = command[1:] if command.startswith("/") else command

        for plugin_name, plugin in self.plugins.items():
            should_continue, modified_command, modified_args = plugin.intercept_command(
                command_without_slash, args
            )
            if not should_continue:
                if modified_command and modified_command in self.command_handlers:
                    handler, _, handler_plugin = self.command_handlers[modified_command]
                    return handler_plugin, handler, [modified_args]
                return plugin_name, None, [modified_command, modified_args]

        # Check if this is a registered plugin command
        if command in self.command_handlers:
            handler, _, plugin_name = self.command_handlers[command]
            return plugin_name, handler, [args]

        return None

    def wrap_function(self, original_func: Callable, func_name: str) -> Callable:
        """Wrap a function to allow plugins to intercept it.

        Args:
            original_func: The original function
            func_name: The name of the function

        Returns:
            A wrapped function that allows plugin interception
        """

        def wrapped(*args, **kwargs):
            # Pre-processing by plugins
            should_continue = True
            for plugin_name in self.intercepted_functions.get(func_name, []):
                plugin = self.plugins[plugin_name]
                plugin_continue, args, kwargs = plugin.intercept_function(
                    func_name, list(args), kwargs
                )
                should_continue = should_continue and plugin_continue

            # Execute the original function if no plugin cancelled it
            if should_continue:
                result = original_func(*args, **kwargs)

                # Post-processing by plugins
                for plugin_name in self.intercepted_functions.get(func_name, []):
                    plugin = self.plugins[plugin_name]
                    result = plugin.post_function(func_name, result)

                return result
            return None

        return wrapped

    def register_function_interception(self, plugin_name: str, func_name: str) -> None:
        """Register a plugin's interest in intercepting a function.

        Args:
            plugin_name: The name of the plugin
            func_name: The name of the function to intercept
        """
        if func_name not in self.intercepted_functions:
            self.intercepted_functions[func_name] = []

        if plugin_name not in self.intercepted_functions[func_name]:
            self.intercepted_functions[func_name].append(plugin_name)

    def get_all_commands(self) -> Dict[str, Tuple[str, str]]:
        """Get all commands from all plugins.

        Returns:
            A dictionary mapping command names to (description, plugin_name) tuples
        """
        return {
            cmd: (desc, plugin)
            for cmd, (_, desc, plugin) in self.command_handlers.items()
        }

    def get_plugin_completions(self) -> Dict[str, List[str]]:
        """Get command completions from all plugins.

        Returns:
            A dictionary mapping command prefixes to lists of completion options
        """
        completions = {}

        # Add built-in completions for commands
        # 为内置命令和子命令添加补全选项
        completions["/plugins"] = ["list", "load", "unload"]

        # 可以在这里添加更多内置命令的补全
        # 例如: completions["/conf"] = ["export", "import"]
        # 例如: completions["/index"] = ["query", "build", "export", "import"]

        # Get completions from plugins
        for plugin in self.plugins.values():
            plugin_completions = plugin.get_completions()
            for prefix, options in plugin_completions.items():
                if prefix not in completions:
                    completions[prefix] = []
                completions[prefix].extend(options)
        return completions

    def get_dynamic_completions(
        self, command: str, current_input: str
    ) -> List[Tuple[str, str]]:
        """Get dynamic completions based on the current command context.

        This method provides context-aware completions for commands that need
        dynamic options based on the current state or user input.

        Args:
            command: The base command (e.g., "/plugins load")
            current_input: The full current input including the command

        Returns:
            A list of tuples containing (completion_text, display_text)
        """
        # Split the input to analyze command parts
        parts = current_input.split(maxsplit=2)
        completions = []

        # Handle built-in /plugins subcommands
        if command == "/plugins load":
            # 提供可用插件列表作为补全选项
            plugin_prefix = ""
            if len(parts) > 2:
                plugin_prefix = parts[2]

            # 获取所有可用的插件
            discovered_plugins = {p.__name__: p for p in self.cached_discover_plugins}

            # 过滤出与前缀匹配的插件名称
            for plugin_name in discovered_plugins.keys():
                if plugin_name.startswith(plugin_prefix):
                    completions.append((plugin_name, plugin_name))

        elif command == "/plugins unload":
            # 提供已加载插件列表作为补全选项
            plugin_prefix = ""
            if len(parts) > 2:
                plugin_prefix = parts[2]

            # 获取所有已加载的插件
            for plugin_name in self.plugins.keys():
                if plugin_name.startswith(plugin_prefix):
                    completions.append((plugin_name, plugin_name))

        # 检查是否有插件提供了此命令的动态补全
        for plugin in self.plugins.values():
            # 检查插件是否有 get_dynamic_completions 方法
            if hasattr(plugin, "get_dynamic_completions") and callable(
                getattr(plugin, "get_dynamic_completions")
            ):
                plugin_completions = plugin.get_dynamic_completions(
                    command, current_input
                )
                if plugin_completions:
                    completions.extend(plugin_completions)

        # 更多命令的动态补全逻辑可以在这里添加
        # 例如：处理 "/git/checkout" 提供分支名补全等

        return completions

    def register_dynamic_completion_provider(
        self, plugin_name: str, command_prefixes: List[str]
    ) -> None:
        """注册一个插件作为特定命令的动态补全提供者。

        Args:
            plugin_name: 插件名称
            command_prefixes: 需要提供动态补全的命令前缀列表
        """
        # 此功能可以在未来拓展，例如维护一个映射
        # 从命令前缀到能够提供其动态补全的插件
        pass

    def load_runtime_cfg(self, cfg_path: Optional[str] = None) -> None:
        """从指定路径或默认路径加载运行时配置。

        Args:
            cfg_path: 配置文件路径，默认为项目根目录下的 .auto-coder/plugins.json
        """
        import json
        import os

        if cfg_path:
            self.runtime_cfg_path = cfg_path
        else:
            # 尝试找到项目根目录，从当前目录开始向上查找
            current_dir = os.getcwd()
            self.runtime_cfg_path = os.path.join(
                current_dir, ".auto-coder", "plugins.json"
            )

        # 确保配置目录存在
        os.makedirs(os.path.dirname(self.runtime_cfg_path), exist_ok=True)

        # 如果配置文件存在，则加载它
        if os.path.exists(self.runtime_cfg_path):
            try:
                with open(self.runtime_cfg_path, "r") as f:
                    config = json.load(f)

                # 添加插件目录
                if "plugin_dirs" in config:
                    for directory in config["plugin_dirs"]:
                        if os.path.isdir(directory):
                            self.add_plugin_directory(directory)

                # 加载插件
                if "plugins" in config:
                    discovered_plugins = {
                        p.__name__: p for p in self.discover_plugins()
                    }
                    for plugin_name in config["plugins"]:
                        if (
                            plugin_name in discovered_plugins
                            and plugin_name not in self.plugins
                        ):
                            plugin_config = config.get("plugin_config", {}).get(
                                plugin_name, {}
                            )
                            self.load_plugin(
                                discovered_plugins[plugin_name], plugin_config
                            )

                print(f"Loaded plugin configuration from {self.runtime_cfg_path}")
            except Exception as e:
                print(f"Error loading plugin configuration: {e}")
        else:
            print(f"No plugin configuration found at {self.runtime_cfg_path}")

    def save_runtime_cfg(self) -> None:
        """将当前插件配置保存到运行时配置文件。"""
        import json
        import os

        if not self.runtime_cfg_path:
            current_dir = os.getcwd()
            self.runtime_cfg_path = os.path.join(
                current_dir, ".auto-coder", "plugins.json"
            )

        # 确保配置目录存在
        os.makedirs(os.path.dirname(self.runtime_cfg_path), exist_ok=True)

        # 构建配置字典
        config = {
            "plugin_dirs": self.plugin_dirs,
            "plugins": list(self.plugins.keys()),
            "plugin_config": {},
        }

        # 添加插件配置（如果插件提供了配置导出功能）
        for name, plugin in self.plugins.items():
            if hasattr(plugin, "export_config") and callable(
                getattr(plugin, "export_config")
            ):
                try:
                    plugin_config = plugin.export_config()
                    if plugin_config:
                        config["plugin_config"][name] = plugin_config
                except Exception as e:
                    print(f"Error exporting config for plugin {name}: {e}")

        try:
            with open(self.runtime_cfg_path, "w") as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            print(f"Error saving plugin configuration: {e}")

    def shutdown_all(self) -> None:
        """Shutdown all plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.shutdown()
            except Exception as e:
                print(f"Error shutting down plugin {plugin.name}: {e}")

        # 保存配置
        self.save_runtime_cfg()

    def handle_plugins_command(self, args: List[str]) -> str:
        """处理 /plugins 命令。

        此方法处理插件的列出、加载和卸载等操作。

        Args:
            args: 命令参数列表，例如 ["list"]、["load", "plugin_name"] 等

        Returns:
            命令的输出结果
        """
        import io

        output = io.StringIO()

        if not args:
            # 列出所有已加载的插件
            print("\033[1;34mLoaded Plugins:\033[0m", file=output)
            for name, plugin in self.plugins.items():
                print(
                    f"  - {name} (v{plugin.version}): {plugin.description}", file=output
                )

        elif args[0] == "list":
            # 列出所有可用的插件
            discovered_plugins = self.discover_plugins()
            print("\033[1;34mAvailable Plugins:\033[0m", file=output)
            for plugin_class in discovered_plugins:
                print(f"  - {plugin_class.__name__}", file=output)

        elif args[0] == "load" and len(args) > 1:
            # 加载特定的插件
            plugin_name = args[1]
            discovered_plugins = {p.__name__: p for p in self.cached_discover_plugins}
            if plugin_name in discovered_plugins:
                if self.load_plugin(discovered_plugins[plugin_name]):
                    print(f"Plugin '{plugin_name}' loaded successfully", file=output)
                    # 加载插件后已在 load_plugin 方法中保存配置
                else:
                    print(f"Failed to load plugin '{plugin_name}'", file=output)
            else:
                print(f"Plugin '{plugin_name}' not found", file=output)

        elif args[0] == "unload" and len(args) > 1:
            # 卸载特定的插件
            plugin_name = args[1]
            if plugin_name in self.plugins:
                plugin = self.plugins.pop(plugin_name)
                plugin.shutdown()
                print(f"Plugin '{plugin_name}' unloaded", file=output)
                # 卸载插件后保存配置
                self.save_runtime_cfg()
            else:
                print(f"Plugin '{plugin_name}' not loaded", file=output)

        else:
            # 在找不到命令的情况下显示用法信息
            print("Usage: /plugins [list|load <name>|unload <name>]", file=output)

        return output.getvalue()
