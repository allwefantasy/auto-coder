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

    def add_plugin_directory(self, directory: str) -> None:
        """Add a directory to search for plugins.

        Args:
            directory: The directory path
        """
        if os.path.isdir(directory) and directory not in self.plugin_dirs:
            self.plugin_dirs.append(directory)
            if directory not in sys.path:
                sys.path.append(directory)

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

        # Add built-in completions for /plugins command
        completions["/plugins"] = ["list", "load", "unload"]

        # Get completions from plugins
        for plugin in self.plugins.values():
            plugin_completions = plugin.get_completions()
            for prefix, options in plugin_completions.items():
                if prefix not in completions:
                    completions[prefix] = []
                completions[prefix].extend(options)
        return completions

    def shutdown_all(self) -> None:
        """Shutdown all plugins."""
        for plugin in self.plugins.values():
            try:
                plugin.shutdown()
            except Exception as e:
                print(f"Error shutting down plugin {plugin.name}: {e}")
