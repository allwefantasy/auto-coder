"""
Plugin system for Chat Auto Coder.
This module provides the base classes and functionality for creating and managing plugins.
"""

import importlib
import inspect
import os
import sys
from typing import Any, Callable, Dict, List, Optional, Set, Tuple, Type, Union
from autocoder.plugins.utils import load_json_file, save_json_file


class Plugin:
    """Base class for all plugins."""

    name: str = "base_plugin" # 插件名称
    description: str = "Base plugin class" # 插件描述
    version: str = "0.1.0" # 插件版本
    manager: "PluginManager"  # 插件管理器
    

    @classmethod
    def id_name(cls) -> str:
        """返回插件的唯一标识符，包括插件目录和插件文件名"""
        return f"{cls.__module__}.{cls.__name__}"

    @classmethod
    def plugin_name(cls) -> str:
        """返回插件的名称，不包括插件目录和插件文件名"""
        return cls.__name__

    def __init__(self, manager: "PluginManager", config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None):
        """Initialize the plugin.

        Args:
            manager: The plugin manager instance
            config: Optional configuration dictionary for the plugin
            config_path: Optional path to the configuration file
        """
        self.config = config or {}
        self.config_path = config_path
        self.manager = manager


    def initialize(self) -> bool:
        """Initialize the plugin.
        
        This method is called after the plugin instance is created but before
        it is registered with the plugin manager. Override this method to
        perform any initialization tasks.
        
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

    def load_config(self, config_path: Optional[str] = None) -> bool:
        """加载插件配置。

        Args:
            config_path: 配置文件路径。如果提供，将覆盖插件的 config_path 属性。

        Returns:
            加载成功返回 True，否则返回 False
        """
        # 如果提供了新的配置路径，则更新 self.config_path
        if config_path:
            self.config_path = config_path
            
        # 如果没有配置路径，则无法加载
        if not self.config_path:
            return False
            
        # 尝试从文件加载配置
        try:
            import json
            import os
            
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                return True
            else:
                # 配置文件不存在，但路径有效，视为成功
                return True
        except Exception as e:
            print(f"Error loading plugin config from {self.config_path}: {e}")
            return False

    def export_config(self, config_path: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """导出插件配置，用于持久化存储。

        默认实现会返回插件的 self.config 属性，并将配置保存到 self.config_path 或提供的 config_path。
        子类可以覆盖此方法，以提供自定义的配置导出逻辑。

        Args:
            config_path: 配置文件保存路径。如果提供，将覆盖插件的 config_path 属性。

        Returns:
            包含插件配置的字典，如果没有配置需要导出则返回 None
        """
        # 如果没有配置，则返回 None
        if not self.config:
            return None
            
        # 更新配置路径（如果提供）
        if config_path:
            self.config_path = config_path
            
        # 通过插件管理器获取插件配置路径
        config_path = self.manager.get_plugin_config_path(self.id_name())
        if config_path:
            self.config_path = config_path
        
        # 如果有配置路径，则保存至文件
        if self.config_path:
            try:
                import json
                import os
                
                # 确保目录存在
                os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
                
                # 保存配置到文件
                with open(self.config_path, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=2, ensure_ascii=False)
            except Exception as e:
                print(f"Error saving plugin config to {self.config_path}: {e}")
                
        return self.config

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
            # 当目录变化时，清空缓存
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
            # 获取插件名称和插件ID
            # plugin_name = plugin_class.plugin_name()
            plugin_id = plugin_class.id_name()
            
            # 获取插件配置路径
            config_path = self.get_plugin_config_path(plugin_id)
            
            # 创建插件实例，传入 manager(self) 作为第一个参数
            plugin = plugin_class(self, config, config_path)
            
            # 如果未提供配置但配置路径存在，尝试加载配置
            if not config and config_path:
                plugin.load_config()
                
            # 调用插件的 initialize 方法，只有成功初始化的插件才会被添加
            if not plugin.initialize():
                print(f"Plugin {plugin_id} initialization failed")
                return False
            
            # 将插件添加到已加载插件字典中
            self.plugins[plugin_id] = plugin

            # Register commands
            for cmd, (handler, desc) in plugin.get_commands().items():
                self.command_handlers[f"/{cmd}"] = (handler, desc, plugin_id)

            return True
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
            discovered_plugins = {p.id_name(): p for p in self.cached_discover_plugins}
            
            for plugin_id in config["plugins"]:
                if plugin_id in discovered_plugins:
                    self.load_plugin(discovered_plugins[plugin_id])

    def get_plugin(self, name: str) -> Optional[Plugin]:
        """Get a plugin by name or full class name.

        Args:
            name: The name or full class name of the plugin

        Returns:
            The plugin instance, or None if not found
        """
        # 直接通过全类名查找 (优先), name 是 plugin_id
        if name in self.plugins:
            return self.plugins[name]
            
        # 如果没找到，尝试通过简单名称查找
        for plugin in self.plugins.values():
            if plugin.plugin_name() == name or plugin.name == name:
                return plugin
                
        return None

    def process_command(
        self, full_command: str
    ) -> Optional[Tuple[str, Optional[Callable], List[str]]]:
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
                    return handler_plugin, handler, [modified_args] if modified_args is not None else [""]
                return plugin_name, None, [modified_command or "", modified_args or ""]

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
            discovered_plugins = self.cached_discover_plugins
            
            # 记录已经添加的显示名称，避免重复
            added_display_names = set()

            # 过滤出与前缀匹配的插件名称
            for plugin_class in discovered_plugins:
                plugin_name = plugin_class.name
                plugin_class_name = plugin_class.plugin_name()
                display_name = f"{plugin_class_name} ({plugin_name})"
                
                # 首先尝试匹配插件短名称
                if plugin_name.startswith(plugin_prefix) and display_name not in added_display_names:
                    completions.append((plugin_name, display_name))
                    added_display_names.add(display_name)
                # 如果类名与短名称不同，也尝试匹配类名
                elif plugin_class_name.startswith(plugin_prefix) and plugin_class_name != plugin_name and display_name not in added_display_names:
                    completions.append((plugin_class_name, display_name))
                    added_display_names.add(display_name)

        elif command == "/plugins unload":
            # 提供已加载插件列表作为补全选项
            plugin_prefix = ""
            if len(parts) > 2:
                plugin_prefix = parts[2]

            # 记录已经添加的显示名称，避免重复
            added_display_names = set()
                
            # 获取所有已加载的插件
            for plugin_id, plugin in self.plugins.items():
                plugin_name = plugin.name
                plugin_class_name = plugin.plugin_name()
                display_name = f"{plugin_class_name} ({plugin_name})"
                
                # 首先尝试匹配插件短名称
                if plugin_name.startswith(plugin_prefix) and display_name not in added_display_names:
                    completions.append((plugin_name, display_name))
                    added_display_names.add(display_name)
                # 如果类名与短名称不同，也尝试匹配类名
                elif plugin_class_name.startswith(plugin_prefix) and plugin_class_name != plugin_name and display_name not in added_display_names:
                    completions.append((plugin_class_name, display_name))
                    added_display_names.add(display_name)

        # 检查是否有插件提供了此命令的动态补全
        for plugin in self.plugins.values():
            # 检查插件是否有 dynamic_completions
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
    
    def project_root(self) -> Optional[str]:
        """检查当前是否在项目根目录。如果是,返回目录,否则返回None"""
        current_dir = os.getcwd()
        _root = os.path.join(current_dir, ".auto-coder")
        if os.path.exists(_root):
            return _root
        return None

    def load_runtime_cfg(self) -> None:
        """从项目根目录加载运行时配置。
        
        只加载插件目录和插件列表信息，具体配置由插件自行加载。
        """
        # 检查是否有项目根目录
        project_root = self.project_root()
        if not project_root:
            return
        # 加载插件列表和目录
        plugins_json_path = os.path.join(project_root, "plugins.json")
        if not os.path.exists(plugins_json_path):
            return

        try:
            config = load_json_file(plugins_json_path)

            # 添加插件目录
            if "plugin_dirs" in config:
                for directory in config["plugin_dirs"]:
                    if os.path.isdir(directory):
                        self.add_plugin_directory(directory)

            # 加载插件 - 在 load_plugin 方法中会自动加载插件的配置
            if "plugins" in config:
                discovered_plugins = {
                    p.id_name(): p for p in self.cached_discover_plugins
                }
                
                for plugin_id in config["plugins"]:
                    if plugin_id in discovered_plugins and plugin_id not in self.plugins:
                        # 加载插件 - 配置会在 load_plugin 方法中处理
                        self.load_plugin(discovered_plugins[plugin_id])
                # print(f"Successfully loaded plugins: {list(self.plugins.keys())}")
        except Exception as e:
            print(f"Error loading plugin configuration: {e}")

    def save_runtime_cfg(self) -> None:
        """将当前插件配置保存到运行时配置文件。
        
        只保存插件目录和插件列表信息，具体配置由插件自行保存。
        """
        # 检查是否有项目根目录
        project_root = self.project_root()
        if not project_root:
            return

        # 保存插件目录和加载的插件列表
        plugins_json_path = os.path.join(project_root, "plugins.json")
        config = {
            "plugin_dirs": self.plugin_dirs,
            "plugins": list(self.plugins.keys())
        }
        
        try:
            save_json_file(plugins_json_path, config)
            # 提示插件保存其配置
            for plugin in self.plugins.values():
                plugin.export_config()
        except Exception as e:
            print(f"Error saving plugins list: {e}")

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
            for plugin_id, plugin in self.plugins.items():
                print(
                    f"  - {plugin.name} (v{plugin.version}): {plugin.description}", file=output
                )

        elif args[0] == "list":
            # 列出所有可用的插件
            discovered_plugins = self.discover_plugins()
            print("\033[1;34mAvailable Plugins:\033[0m", file=output)
            for plugin_class in discovered_plugins:
                # 显示插件的短名称而不是完整ID
                print(f"  - {plugin_class.plugin_name()} ({plugin_class.name}): {plugin_class.description}", file=output)

        elif args[0] == "load" and len(args) > 1:
            # 加载特定的插件
            plugin_name = args[1]
            discovered_plugins = self.cached_discover_plugins
            
            # 使用简短名称查找插件
            found = False
            for plugin_class in discovered_plugins:
                if plugin_class.plugin_name() == plugin_name or plugin_class.name == plugin_name:
                    if self.load_plugin(plugin_class):
                        print(f"Plugin '{plugin_name}' loaded successfully", file=output)
                        # 加载插件后已在 load_plugin 方法中保存配置
                    else:
                        print(f"Failed to load plugin '{plugin_name}'", file=output)
                    found = True
                    break
            
            if not found:
                print(f"Plugin '{plugin_name}' not found", file=output)

        elif args[0] == "unload" and len(args) > 1:
            # 卸载特定的插件
            plugin_name = args[1]
            found = False
            
            # 使用简短名称查找插件
            for plugin_id, plugin in list(self.plugins.items()):
                if plugin.plugin_name() == plugin_name or plugin.name == plugin_name:
                    plugin = self.plugins.pop(plugin_id)
                    plugin.shutdown()
                    print(f"Plugin '{plugin_name}' unloaded", file=output)
                    # 卸载插件后保存配置
                    self.save_runtime_cfg()
                    found = True
                    break
            
            if not found:
                print(f"Plugin '{plugin_name}' not loaded", file=output)

        else:
            # 在找不到命令的情况下显示用法信息
            print("Usage: /plugins [list|load <name>|unload <name>]", file=output)

        return output.getvalue()

    def apply_keybindings(self, kb) -> None:
        """将所有插件的键盘绑定应用到提供的键盘绑定器对象。
        
        此方法迭代所有已加载的插件，获取它们的键盘绑定，并将这些绑定应用到键盘绑定器。
        这样可以将键盘绑定的处理逻辑集中在 PluginManager 中，减少外部代码的耦合。
        
        Args:
            kb: 键盘绑定器对象，必须有一个 add 方法，该方法返回一个可调用对象用于注册处理程序
        """
        # 检查键盘绑定器是否有 add 方法
        if not hasattr(kb, 'add') or not callable(getattr(kb, 'add')):
            raise ValueError("键盘绑定器必须有一个可调用的 add 方法")
        
        # 迭代所有插件
        for plugin_key, plugin in self.plugins.items():
            # 获取插件的键盘绑定
            for key_combination, handler, description in plugin.get_keybindings():
                # 应用键盘绑定
                try:
                    kb.add(key_combination)(handler)
                except Exception as e:
                    print(f"Error applying keybinding '{key_combination}' from plugin '{plugin_key}': {e}")
        
        return

    def get_plugin_config_path(self, plugin_id: str) -> Optional[str]:
        """获取插件配置文件的路径。

        Args:
            plugin_id: 插件的唯一标识符 (plugin.id_name())

        Returns:
            配置文件路径，如果项目根目录不存在则返回 None
        """
        # 检查是否有项目根目录
        project_root = self.project_root()
        if not project_root:
            return None
            
        # 创建配置目录和文件路径
        config_dir = os.path.join(project_root, "plugins", plugin_id)
        os.makedirs(config_dir, exist_ok=True)
        return os.path.join(config_dir, "config.json")
