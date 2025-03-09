# Chat Auto Coder Plugin Development Guide

## Part One: Plugin Development Tutorial - GitHelperPlugin Development Process

We'll use the built-in `git_helper` plugin as an example to illustrate the plugin development process.

### 1. Plugin Basic Structure

First, we create a basic plugin class:

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

### 2. Implementing Initialization Logic

Set up basic plugin configuration and environment detection in the initialization method:

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
        print(f"[{self.name}] Warning: Git is not available, some features will be limited")
        return True

    print(f"[{self.name}] Git helper plugin initialized")
    return True
```

### 3. Registering Command Interface

Define the list of commands provided by the plugin:

```python
def get_commands(self) -> Dict[str, Tuple[Callable, str]]:
    """Get commands provided by this plugin.

    Returns:
        A dictionary of command name to handler and description
    """
    return {
        "git/status": (self.git_status, "Display Git repository status"),
        "git/commit": (self.git_commit, "Commit changes"),
        "git/branch": (self.git_branch, "Display or create branches"),
        "git/checkout": (self.git_checkout, "Switch branches"),
        "git/diff": (self.git_diff, "Show changes"),
        "git/log": (self.git_log, "Show commit history"),
        "git/pull": (self.git_pull, "Pull remote changes"),
        "git/push": (self.git_push, "Push local changes to remote"),
        "git/reset": (self.handle_reset, "Reset current branch to specified state (hard/soft/mixed)"),
    }
```

### 4. Implementing Command Completion

Provide static and dynamic completions for commands:

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

    # Add branch completions
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

### 5. Implementing Common Utility Methods

Create reusable utility methods for handling Git command execution:

```python
def _run_git_command(self, args: List[str]) -> Tuple[int, str, str]:
    """Run a Git command.

    Args:
        args: The command arguments

    Returns:
        A tuple of (return_code, stdout, stderr)
    """
    if not self.git_available:
        return 1, "", "Git not available"

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

### 6. Implementing Command Handling Logic

Here are examples of typical command implementations:

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
        print("Please provide a commit message, e.g.: /git/commit 'Fix bug in login'")
        return

    # First add all changes (git add .)
    self._run_git_command(["add", "."])

    # Execute commit
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
        print("Please provide reset mode (hard/soft/mixed) and optional commit hash")
        return
        
    args_list = args.split()
    mode = args_list[0]
    commit = args_list[1] if len(args_list) > 1 else "HEAD"
    
    if mode not in ["hard", "soft", "mixed"]:
        print(f"Error: Invalid reset mode '{mode}', must be one of hard/soft/mixed")
        return
        
    code, stdout, stderr = self._run_git_command(["reset", f"--{mode}", commit])
    if code == 0:
        print(f"\n{stdout}")
        print(f"Successfully reset repository to {mode} mode at {commit}")
    else:
        print(f"Error: {stderr}")
```

### 7. Implementing Plugin Shutdown

Finally, implement resource cleanup and shutdown logic:

```python
def shutdown(self) -> None:
    """Shutdown the plugin."""
    print(f"[{self.name}] Git helper plugin closed")
```

---

## Part Two: Core API Reference

### Plugin Base Class

Plugins must inherit from the `Plugin` base class and implement these main methods:

| Method/Attribute | Description | Return Value |
|---------|------|-------|
| `name` | Plugin name (lowercase+underscore) | `str` |
| `description` | Plugin description | `str` |
| `version` | Plugin version number | `str` |
| `initialize()` | Plugin initialization method | `bool` |
| `get_commands()` | Return provided commands | `Dict[str, Tuple[Callable, str]]` |
| `get_keybindings()` | Return provided key bindings | `List[Tuple[str, Callable, str]]` |
| `get_completions()` | Return static completion options | `Dict[str, List[str]]` |
| `get_dynamic_completions()` | Return dynamic completion options | `List[str]` |
| `intercept_command()` | Intercept command execution | `Tuple[bool, str, str]` |
| `intercept_function()` | Intercept function calls | `Tuple[bool, Tuple, Dict]` |
| `post_function()` | Process function results | `Any` |
| `export_config()` | Export plugin configuration | `Dict[str, Any]` |
| `shutdown()` | Plugin cleanup | `None` |

### PluginManager Key Methods

The plugin manager provides the following core functionality:

```python
# Plugin directory management
manager.add_plugin_directory(directory)  # Add project-level plugin directory
manager.add_global_plugin_directory(directory)  # Add global plugin directory
manager.clear_plugin_directories()  # Clear project-level plugin directories

# Plugin discovery and loading
manager.discover_plugins()  # Discover plugins in plugin directories
manager.load_plugin(plugin_class, config)  # Load a specific plugin class
manager.get_plugin(name)  # Get a loaded plugin by name

# Interception capabilities
manager.register_function_interception(plugin_name, func_name)  # Register function interception
manager.process_command(full_command)  # Process command, allowing plugin interception

# Completion support
manager.get_all_commands()  # Get all plugin commands
manager.get_plugin_completions()  # Get completions from all plugins
manager.get_dynamic_completions(command, current_input)  # Get dynamic completions

# Configuration management
manager.load_runtime_cfg()  # Load plugin configurations
manager.save_runtime_cfg()  # Save plugin configurations
```

---

## Part Three: Plugin Development Best Practices

### 1. Command Structure Design

Using hierarchical naming makes commands more organized:

```python
def get_commands(self):
    return {
        "namespace/command": (self.handler, "description"),
        "namespace/subnamespace/command": (self.handler, "description"),
    }
```

For example, the Git plugin uses the `git/` prefix to group all commands.

### 2. Error Handling and User Feedback

Always catch exceptions in command handlers and provide friendly error messages:

```python
def git_branch(self, args: str) -> None:
    try:
        # ... code logic ...
    except Exception as e:
        print(f"Branch operation failed: {str(e)}")
        # Provide help information
        print("Usage format: /git/branch [name] or /git/branch --list")
```

### 3. Effective Use of Utility Methods

Abstract common functionality into generic utility methods to avoid code repetition:

```python
# Example utility method in GitHelperPlugin
def _run_git_command(self, args: List[str]) -> Tuple[int, str, str]:
    # Unified handling of Git command execution
    # ... implementation ...
```

### 4. Command Completion Design

Completions can be both static and dynamically generated:

```python
# Static completion
def get_completions(self):
    return {"/git/reset": ["hard", "soft", "mixed"]}

# Dynamic completion (e.g., based on actual branches in the repository)
def _get_git_branches(self):
    # Dynamically get Git branch list
    # ... implementation ...
```

### 5. Graceful Initialization and Shutdown

Ensure plugins handle various environment conditions gracefully:

```python
def initialize(self):
    if not self._check_dependency():
        print("Warning: Dependency not available, some features will be limited")
        return True  # Still allow plugin to load, but with limited functionality
    return True

def shutdown(self):
    # Clean up resources, close connections, etc.
    print(f"[{self.name}] Plugin closed")
```

### 6. Configuration Persistence Management

Use the configuration mechanism to save plugin state:

```python
def export_config(self, config_path=None):
    return {
        "default_branch": self.default_branch,
        "other_setting": self.some_value,
    }
```

### 7. Resource Management and Performance Optimization

Cache results of expensive operations, especially external command calls:

```python
def _get_git_branches(self):
    # Add caching mechanism to avoid frequent external command calls
    if not hasattr(self, "_cached_branches") or time.time() - self._last_branch_update > 60:
        self._cached_branches = self._fetch_branches()
        self._last_branch_update = time.time()
    return self._cached_branches
```

### 8. User Experience Optimization

Add help information and interactive guidance for complex commands:

```python
def git_reset(self, args: str) -> None:
    if not args or args == "help":
        print("Usage: /git/reset [mode] [commit]")
        print("Modes:")
        print("  - hard: Discard working directory and staging area changes")
        print("  - soft: Keep working directory and staging area changes")
        print("  - mixed: Default mode, keep working directory but reset staging area")
        return
    # ... continue implementation ...
```

### 9. Plugin Documentation and Comments

Add detailed documentation and code comments to help users and other developers understand:

```python
"""
Git Helper Plugin for Chat Auto Coder.
Provides Git operation integration, including status queries, commits, branch management, etc.

Usage:
- /git/status: Show current repository status
- /git/commit <message>: Commit all changes
...
"""
```

---

By studying the Git plugin implementation, you can master the core patterns of Chat Auto Coder plugin development. The flexibility of the plugin system allows you to extend and customize Auto Coder to adapt to various development scenarios and workflows. 