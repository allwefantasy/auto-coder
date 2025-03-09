"""
Sample plugin demonstrating the plugin system functionality.
"""

from typing import Any, Callable, Dict, List, Optional, Tuple

from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.formatted_text import FormattedText

from autocoder.plugins import Plugin, PluginManager


class SamplePlugin(Plugin):
    """A sample plugin demonstrating the plugin system functionality."""

    name = "sample_plugin"
    description = "A sample plugin demonstrating the plugin system features"
    version = "0.1.0"

    def __init__(self, manager: PluginManager, config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None):
        """Initialize the sample plugin."""
        super().__init__(manager, config, config_path)
        self.counter = 0

    def initialize(self) -> bool:
        """Initialize the plugin.

        Returns:
            True if initialization was successful
        """
        print(f"[{self.name}] Initializing sample plugin")

        # Register interest in intercepting functions
        self.manager.register_function_interception(self.name, "ask")
        self.manager.register_function_interception(self.name, "coding")

        return True

    def get_commands(self) -> Dict[str, Tuple[Callable, str]]:
        """Get commands provided by this plugin.

        Returns:
            A dictionary of command name to handler and description
        """
        return {
            "sample": (self.sample_command, "Sample plugin command"),
            "counter": (self.counter_command, "Show the plugin counter"),
        }

    def get_keybindings(self) -> List[Tuple[str, Callable, str]]:
        """Get keybindings provided by this plugin.

        Returns:
            A list of (key_combination, handler, description) tuples
        """

        def increment_counter(event):
            self.counter += 1
            print(f"[{self.name}] Counter incremented to {self.counter}")

        return [
            ("c-p", increment_counter, "Increment plugin counter"),
        ]

    def get_completions(self) -> Dict[str, List[str]]:
        """Get completions provided by this plugin.

        Returns:
            A dictionary mapping command prefixes to completion options
        """
        return {
            "/sample": ["option1", "option2", "option3"],
            "/counter": ["show", "reset", "increment"],
        }

    def sample_command(self, args: str) -> None:
        """Handle the sample command.

        Args:
            args: Command arguments
        """
        print(f"[{self.name}] Sample command executed with args: {args}")
        self.counter += 1
        print(f"[{self.name}] Counter incremented to {self.counter}")

    def counter_command(self, args: str) -> None:
        """Handle the counter command.

        Args:
            args: Command arguments
        """
        if args == "reset":
            self.counter = 0
            print(f"[{self.name}] Counter reset to {self.counter}")
        elif args == "increment":
            self.counter += 1
            print(f"[{self.name}] Counter incremented to {self.counter}")
        else:
            print(f"[{self.name}] Current counter value: {self.counter}")

    def intercept_command(
        self, command: str, args: str
    ) -> Tuple[bool, Optional[str], Optional[str]]:
        """Intercept commands.

        Args:
            command: The command name (without the /)
            args: The command arguments

        Returns:
            A tuple of (should_continue, modified_command, modified_args)
        """
        # Log all commands
        print(f"[{self.name}] Command intercepted: /{command} {args}")

        # Example: modify the 'ask' command to add a prefix
        if command == "ask" and args:
            return True, command, f"[From Sample Plugin] {args}"

        return True, command, args

    def intercept_function(
        self, func_name: str, args: List[Any], kwargs: Dict[str, Any]
    ) -> Tuple[bool, List[Any], Dict[str, Any]]:
        """Intercept function calls.

        Args:
            func_name: The function name
            args: The positional arguments
            kwargs: The keyword arguments

        Returns:
            A tuple of (should_continue, modified_args, modified_kwargs)
        """
        print(f"[{self.name}] Function intercepted: {func_name}")

        # Example: modify the 'coding' function to add a prefix to the query
        if func_name == "coding" and args:
            args = list(args)  # Convert tuple to list for modification
            if isinstance(args[0], str):
                args[0] = f"[Enhanced by Sample Plugin] {args[0]}"

        return True, args, kwargs

    def post_function(self, func_name: str, result: Any) -> Any:
        """Process function results.

        Args:
            func_name: The function name
            result: The function result

        Returns:
            The possibly modified result
        """
        print(f"[{self.name}] Function completed: {func_name}")
        return result

    def shutdown(self) -> None:
        """Shutdown the plugin."""
        print(f"[{self.name}] Shutting down sample plugin (counter: {self.counter})")
