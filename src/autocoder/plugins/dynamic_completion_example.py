"""
Dynamic Completion Example Plugin for Chat Auto Coder.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from autocoder.plugins import Plugin, PluginManager


class DynamicCompletionExamplePlugin(Plugin):
    """A sample plugin demonstrating dynamic completion functionality."""

    name = "dynamic_completion_example"
    description = "Demonstrates the dynamic completion feature"
    version = "0.1.0"

    def __init__(self, manager: PluginManager, config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None):
        """Initialize the plugin.

        Args:
            manager: The plugin manager instance
            config: Optional configuration dictionary for the plugin
            config_path: Optional path to the configuration file
        """
        super().__init__(manager, config, config_path)
        self.items = ["item1", "item2", "item3", "custom_item"]

    def initialize(self) -> bool:
        """Initialize the plugin.

        Returns:
            True if initialization was successful, False otherwise
        """
        # Register for function interception if needed
        # self.manager.register_function_interception(self.name, "ask")

        # Register as a dynamic completion provider
        self.manager.register_dynamic_completion_provider(self.name, ["/example"])

        return True

    def get_commands(self) -> Dict[str, Tuple[Callable, str]]:
        """Get commands provided by this plugin.

        Returns:
            A dictionary of command name to handler and description
        """
        return {
            "example": (
                self.example_command,
                "Example command with dynamic completion",
            ),
            "example/add": (self.add_item, "Add a new item to the example list"),
            "example/list": (self.list_items, "List all available items"),
        }

    def get_completions(self) -> Dict[str, List[str]]:
        """Get completions provided by this plugin.

        Returns:
            A dictionary mapping command prefixes to completion options
        """
        # 基本的静态补全选项
        return {
            "/example": ["add", "list", "select"],
        }

    def get_dynamic_completions(
        self, command: str, current_input: str
    ) -> List[Tuple[str, str]]:
        """Get dynamic completions based on the current command context.

        Args:
            command: The base command (e.g., "/example select")
            current_input: The full current input including the command

        Returns:
            A list of tuples containing (completion_text, display_text)
        """
        # 如果是 /example select 命令，提供动态项目列表
        if current_input.startswith("/example select"):
            # 提取已输入的部分项目名
            parts = current_input.split(maxsplit=2)
            item_prefix = ""
            if len(parts) > 2:
                item_prefix = parts[2]

            # 返回匹配的项目
            return [
                (item, f"{item} (example item)")
                for item in self.items
                if item.startswith(item_prefix)
            ]

        return []

    def example_command(self, args: str) -> None:
        """Handle the example command.

        Args:
            args: Command arguments
        """
        if not args:
            print("Usage: /example [add|list|select]")
            return

        parts = args.split(maxsplit=1)
        subcommand = parts[0]

        if subcommand == "select" and len(parts) > 1:
            item = parts[1]
            if item in self.items:
                print(f"Selected item: {item}")
            else:
                print(
                    f"Item '{item}' not found. Use /example list to see available items."
                )
        else:
            print(f"Unknown subcommand: {subcommand}. Use add, list, or select.")

    def add_item(self, args: str) -> None:
        """Add a new item to the list.

        Args:
            args: The item name to add
        """
        if not args:
            print("Please specify an item name to add.")
            return

        if args in self.items:
            print(f"Item '{args}' already exists.")
        else:
            self.items.append(args)
            print(f"Added item: {args}")

    def list_items(self, args: str) -> None:
        """List all available items.

        Args:
            args: Ignored
        """
        print("Available items:")
        for item in self.items:
            print(f"  - {item}")

    def shutdown(self) -> None:
        """Shutdown the plugin."""
        pass
