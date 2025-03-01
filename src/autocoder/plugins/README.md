# Chat Auto Coder Plugin System

This directory contains the plugin system for Chat Auto Coder, which allows extending the functionality of the application at runtime.

## Plugin System Features

- Add new commands to the Chat Auto Coder
- Intercept and modify existing commands
- Intercept and modify function calls
- Add custom keybindings
- Provide command completions
- No-invasive architecture (doesn't require modifying existing code)

## Using Plugins

You can load plugins in several ways:

1. Command line arguments:
   ```
   python -m autocoder.chat_auto_coder --plugin_dirs /path/to/plugins --plugins PluginClass1,PluginClass2
   ```

2. Configuration file:
   ```
   python -m autocoder.chat_auto_coder --plugin_config /path/to/config.json
   ```

3. At runtime using the `/plugins` command:
   ```
   /plugins list              # List available plugins
   /plugins load PluginClass  # Load a specific plugin
   /plugins unload PluginName # Unload a plugin
   /plugins                   # Show loaded plugins
   ```

## Creating Plugins

To create a plugin, subclass the `Plugin` class from `autocoder.plugins`:

```python
from autocoder.plugins import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    description = "My custom plugin"
    version = "0.1.0"
    
    def __init__(self, config=None):
        super().__init__(config)
        # Initialize your plugin
    
    def initialize(self, manager):
        # Register function interceptions
        manager.register_function_interception(self.name, "ask")
        return True
    
    def get_commands(self):
        return {
            "my_command": (self.my_command_handler, "My custom command"),
        }
    
    def my_command_handler(self, args):
        print(f"My command executed with: {args}")
    
    def get_keybindings(self):
        return [
            ("c-m", self.my_keybinding_handler, "My custom keybinding"),
        ]
    
    def my_keybinding_handler(self, event):
        print("My keybinding pressed!")
    
    def intercept_command(self, command, args):
        # Return True, command, args to allow normal processing
        # Return False, new_command, new_args to take over processing
        return True, command, args
    
    def intercept_function(self, func_name, args, kwargs):
        # Modify args or kwargs if needed
        return True, args, kwargs
    
    def post_function(self, func_name, result):
        # Modify result if needed
        return result
    
    def shutdown(self):
        # Clean up resources
        pass
```

## Plugin Configuration

Plugins can be configured using a JSON file. Example:

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

The configuration will be passed to the plugin's constructor.

## Built-in Plugins

The following plugins are included with Chat Auto Coder:

- `SamplePlugin`: A demonstration plugin showing basic functionality
- `GitHelperPlugin`: A git command plugin

## Plugin API Reference

### Plugin Class

Base class for all plugins:

- `name`: Plugin name (string)
- `description`: Plugin description (string)
- `version`: Plugin version (string)
- `initialize(manager)`: Called when the plugin is loaded
- `get_commands()`: Returns a dictionary of commands provided by the plugin
- `get_keybindings()`: Returns a list of keybindings provided by the plugin
- `get_completions()`: Returns a dictionary of command completions
- `intercept_command(command, args)`: Intercept and potentially modify commands
- `intercept_function(func_name, args, kwargs)`: Intercept and potentially modify function calls
- `post_function(func_name, result)`: Process function results
- `shutdown()`: Called when the plugin is unloaded or the application is exiting

### PluginManager Class

Manages plugins for the Chat Auto Coder:

- `add_plugin_directory(directory)`: Add a directory to search for plugins
- `discover_plugins()`: Discover available plugins in plugin directories
- `load_plugin(plugin_class, config)`: Load and initialize a plugin
- `load_plugins_from_config(config)`: Load plugins based on configuration
- `get_plugin(name)`: Get a plugin by name
- `process_command(full_command)`: Process a command, allowing plugins to intercept it
- `wrap_function(original_func, func_name)`: Wrap a function to allow plugin interception
- `register_function_interception(plugin_name, func_name)`: Register a plugin's interest in intercepting a function
- `get_all_commands()`: Get all commands from all plugins
- `get_plugin_completions()`: Get command completions from all plugins
- `shutdown_all()`: Shutdown all plugins 