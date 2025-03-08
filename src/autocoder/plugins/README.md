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

At runtime using the `/plugins` command:
   ```
   /plugins list              # List available plugins
   /plugins load PluginClass  # Load a specific plugin
   /plugins unload PluginName # Unload a plugin
   /plugins                   # Show loaded plugins
   ```

## Plugin Directories

Chat Auto Coder supports two types of plugin directories:

1. **Project-specific plugin directories**: Only available in the current project.
2. **Global plugin directories**: Available across all projects for the current user.

### Managing Plugin Directories

You can manage plugin directories using the `/plugins/dirs` command:

```
/plugins/dirs                # List all plugin directories (both global and project-specific)
/plugins/dirs /add <path>    # Add a project-specific plugin directory
/plugins/dirs /remove <path> # Remove a project-specific plugin directory
/plugins/dirs /clear         # Clear all project-specific plugin directories
```

Global plugin directories are stored in `~/.auto-coder/plugins/global_plugin_dirs` and are automatically loaded when Chat Auto Coder starts. They remain available across all your projects.

To add a global plugin directory, you'll need to edit the global plugin directories file directly, or use the API from code.

## Creating Plugins

To create a plugin, subclass the `Plugin` class from `autocoder.plugins`:

```python
from autocoder.plugins import Plugin

class MyPlugin(Plugin):
    name = "my_plugin"
    description = "My custom plugin"
    version = "0.1.0"
    
    def __init__(self, manager, config=None, config_path=None):
        super().__init__(manager, config, config_path)
        # Initialize your plugin
    
    def initialize(self):
        # This method is for plugin self-initialization
        # You can set up resources, register event handlers, or perform any startup tasks
        # The register_function_interception below is just an example of what you might do here
        self.manager.register_function_interception(self.name, "ask")
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
    
    def export_config(self, config_path=None):
        # Export plugin configuration for persistence
        # Return None if no configuration is needed
        return self.config
    
    def shutdown(self):
        # Clean up resources
        pass
```

## Plugin Configuration

The configuration for each plugin is stored separately in the project's `.auto-coder/plugins/{plugin_id}/config.json` directory. The plugin manager takes care of loading and saving these configurations.

Global plugin directories are stored in `~/.auto-coder/plugins/global_plugin_dirs` and are automatically loaded for all projects.

## Built-in Plugins

The following plugins are included with Chat Auto Coder:

- `SamplePlugin`: A demonstration plugin showing basic functionality
- `DynamicCompletionExamplePlugin`: A plugin demonstrating dynamic command completion functionality
- `GitHelperPlugin`: A git command plugin


## Plugin Identification

Each plugin is uniquely identified by its full module and class name through the `id_name()` class method:

```python
@classmethod
def id_name(cls) -> str:
    """Return the unique identifier for the plugin including module path"""
    return f"{cls.__module__}.{cls.__name__}"
```

This identifier is used for plugin registration, loading, and configuration management.

## Plugin API Reference

### Plugin Class

Base class for all plugins:

- `name`: Plugin name (string)
- `description`: Plugin description (string)
- `version`: Plugin version (string)
- `dynamic_cmds`: List of commands that require dynamic completion (list of strings). This list specifies which commands should use dynamic completion based on the current context. For example, a plugin might set this to `["/my_command"]` to indicate that `/my_command` should have dynamic completions.
- `initialize()`: Called when the plugin is loaded. Used for plugin self-initialization such as setting up resources, connecting to services, or any other startup tasks. Return `True` if initialization is successful, `False` otherwise.
- `get_commands()`: Returns a dictionary of commands provided by the plugin
- `get_keybindings()`: Returns a list of keybindings provided by the plugin
- `get_completions()`: Returns a dictionary of command completions
- `get_dynamic_completions(command, current_input)`: Returns dynamic completions based on input context
- `intercept_command(command, args)`: Intercept and potentially modify commands
- `intercept_function(func_name, args, kwargs)`: Intercept and potentially modify function calls
- `post_function(func_name, result)`: Process function results
- `export_config(config_path)`: Export plugin configuration
- `shutdown()`: Called when the plugin is unloaded or the application is exiting

### PluginManager Class

Manages plugins for the Chat Auto Coder:

- `add_plugin_directory(directory)`: Add a directory to search for plugins (project-specific)
- `add_global_plugin_directory(directory)`: Add a global directory to search for plugins (available in all projects)
- `remove_plugin_directory(directory)`: Remove a project-specific plugin directory
- `clear_plugin_directories()`: Clear all project-specific plugin directories
- `load_global_plugin_dirs()`: Load global plugin directories from ~/.auto-coder/plugins/global_plugin_dirs
- `save_global_plugin_dirs()`: Save global plugin directories to ~/.auto-coder/plugins/global_plugin_dirs
- `discover_plugins()`: Discover available plugins in plugin directories
- `load_plugin(plugin_class, config)`: Load and initialize a plugin
- `load_plugins_from_config(config)`: Load plugins based on configuration
- `get_plugin(name)`: Get a plugin by name
- `process_command(full_command)`: Process a command, allowing plugins to intercept it
- `wrap_function(original_func, func_name)`: Wrap a function to allow plugin interception
- `register_function_interception(plugin_name, func_name)`: Register a plugin's interest in intercepting a function
- `get_all_commands()`: Get all commands from all plugins
- `get_plugin_completions()`: Get command completions from all plugins
- `get_dynamic_completions(command, current_input)`: Get dynamic completions based on current input
- `load_runtime_cfg()`: Load runtime configuration for plugins
- `save_runtime_cfg()`: Save runtime configuration for plugins
- `shutdown_all()`: Shutdown all plugins

### Module-Level Functions

The `autocoder.plugins` module also provides the following functions:

- `register_global_plugin_dir(directory)`: Register a directory as a global plugin directory during plugin installation. This is a convenience function for plugin installation scripts.

## Plugin Installation and Registration

When creating installation scripts for plugins, you can use the `register_global_plugin_dir` module-level function to automatically register your plugin's directory as a global plugin directory. This makes the plugin available to all projects on the user's machine.

### Example: Plugin Installation Script

```python
#!/usr/bin/env python3
import os
import sys
from pathlib import Path

def install_plugin():
    """Install the plugin and register it globally."""
    # Get the current directory (where your plugin code is located)
    plugin_dir = os.path.dirname(os.path.abspath(__file__))
    
    try:
        # Import the plugin manager module
        sys.path.insert(0, str(Path(plugin_dir).parent))
        from autocoder.plugins import register_global_plugin_dir
        
        # Register the plugin directory globally using the module function
        register_global_plugin_dir(plugin_dir)
        print(f"✅ Successfully registered plugin directory: {plugin_dir}")
        print(f"The plugin is now available in all Chat Auto Coder projects.")
            
        return True
    except Exception as e:
        print(f"❌ Error during plugin installation: {str(e)}")
        return False

if __name__ == "__main__":
    if install_plugin():
        print("Installation completed successfully!")
    else:
        print("Installation failed. Please check the error messages above.") 