
import os
import io
import contextlib
import fnmatch
import json
from typing import Dict, Any, List, Callable, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from autocoder.auto_coder_runner import save_memory  # Import save_memory
from autocoder.common.conf_validator import ConfigValidator
from autocoder.common.auto_coder_lang import get_message, get_message_with_format

# Helper function to print the configuration table (internal implementation)
def _print_conf_table(content: Dict[str, Any], title: str = "Configuration Settings"):
    """Display configuration dictionary in a Rich table format."""
    console = Console(file=io.StringIO(), force_terminal=True, color_system="truecolor") # Capture output

    # Create a styled table with rounded borders
    table = Table(
        show_header=True,
        header_style="bold magenta",
        title=title,
        title_style="bold blue",
        border_style="blue",
        show_lines=True
    )

    # Add columns with explicit width and alignment
    table.add_column(get_message("conf_key"), style="cyan", justify="right", width=30, no_wrap=False)
    table.add_column(get_message("conf_value"), style="green", justify="left", width=50, no_wrap=False)

    # Sort keys for consistent display
    for key in sorted(content.keys()):
        value = content[key]
        # Format value based on type
        if isinstance(value, (dict, list)):
            formatted_value = Text(json.dumps(value, indent=2), style="yellow")
        elif isinstance(value, bool):
            formatted_value = Text(str(value), style="bright_green" if value else "red")
        elif isinstance(value, (int, float)):
            formatted_value = Text(str(value), style="bright_cyan")
        else:
            formatted_value = Text(str(value), style="green")

        table.add_row(str(key), formatted_value)

    # Add padding and print with a panel
    console.print(Panel(
        table,
        padding=(1, 2),
        subtitle=f"[italic]{get_message('conf_subtitle')}[/italic]",
        border_style="blue"
    ))
    return console.file.getvalue() # Return captured string

# --- Command Handlers ---

def _handle_list_conf(memory: Dict[str, Any], args: List[str]) -> str:
    """Handles listing configuration settings, supports wildcard filtering."""
    conf = memory.get("conf", {})
    pattern = args[0] if args else "*" # Default to all if no pattern

    if pattern == "*":
        title = get_message("conf_title")
        filtered_conf = conf
    else:
        title = f"Filtered Configuration (Pattern: {pattern})"
        filtered_conf = {k: v for k, v in conf.items() if fnmatch.fnmatch(k, pattern)}
        if not filtered_conf:
            return f"No configuration keys found matching pattern: {pattern}"

    if not filtered_conf and pattern == "*":
        return "No configurations set."

    return _print_conf_table(filtered_conf, title)


def _handle_get_conf(memory: Dict[str, Any], args: List[str]) -> str:
    """Handles getting a specific configuration setting."""
    if len(args) != 1:
        return "Error: 'get' command requires exactly one argument (the key). Usage: /conf get <key>"
    key = args[0]
    conf = memory.get("conf", {})
    value = conf.get(key)
    if value is None:
        return f"Error: Configuration key '{key}' not found."
    else:
        # Format value for better readability
        if isinstance(value, (list, dict)):
             formatted_value = json.dumps(value, indent=2)
        else:
             formatted_value = repr(value)
        return f"{key}: {formatted_value}"

def _parse_value(value_str: str) -> Any:
    """Attempts to parse the value string into common types."""
    value_str = value_str.strip()
    if value_str.lower() == 'true':
        return True
    if value_str.lower() == 'false':
        return False
    if value_str.lower() == 'none' or value_str.lower() == 'null':
        return None
    # Keep quoted strings as strings without quotes
    if (value_str.startswith('"') and value_str.endswith('"')) or \
       (value_str.startswith("'") and value_str.endswith("'")):
         return value_str[1:-1]

    try:
        # Try int first
        return int(value_str)
    except ValueError:
        pass
    try:
        # Then try float
        return float(value_str)
    except ValueError:
        pass
    # If none of the above, return as string
    return value_str

def _handle_set_conf(memory: Dict[str, Any], args: List[str]) -> str:
    """Handles setting or updating a configuration setting."""
    if len(args) < 2:
        return "Error: 'set' command requires at least two arguments (key and value). Usage: /conf set <key> <value>"
    key = args[0]
    # Join the rest of the arguments to form the value string
    value_str = " ".join(args[1:])
    try:
        parsed_value = _parse_value(value_str)

        # Validate before setting
        product_mode = memory.get("conf", {}).get("product_mode", "lite")
        ConfigValidator.validate(key, str(parsed_value), product_mode) # Validate the parsed value as string initially if needed, or adjust validation

        if "conf" not in memory:
            memory["conf"] = {}
        memory["conf"][key] = parsed_value
        save_memory() # Save after modification
        # Use repr for confirmation message for clarity
        return f"Configuration updated: {key} = {repr(parsed_value)}"
    except Exception as e:
        return f"Error setting configuration for key '{key}': {e}"

def _handle_delete_conf(memory: Dict[str, Any], args: List[str]) -> str:
    """Handles deleting a configuration setting."""
    if len(args) != 1:
        return "Error: 'delete' command requires exactly one argument (the key). Usage: /conf delete <key>"
    key = args[0]
    conf = memory.get("conf", {})
    if key in conf:
        try:
            del memory["conf"][key]
            save_memory() # Save after modification
            return f"Configuration deleted: {key}"
        except Exception as e:
            return f"Error deleting key '{key}': {e}"
    else:
        return f"Error: Configuration key '{key}' not found."


def _handle_help(memory: Dict[str, Any], args: List[str]) -> str:
    """Provides help text for the /conf command."""
    if args:
        return f"Error: 'help' command takes no arguments. Usage: /conf help"

    help_text = """
/conf command usage:
  /conf [pattern]    - Show configurations. Optional wildcard pattern (e.g., *_model, api*).  
  /conf get <key>    - Get the value of a specific configuration key.
  /conf set <key>:<value> - Set or update a configuration key.
                       Value parsed (bool, int, float, None) or treated as string.
                       Use quotes ("value with spaces") for explicit strings.
  /conf /drop <key> - Delete a configuration key.
  /conf /export <path> - Export current configuration to a file.
  /conf /import <path> - Import configuration from a file.
  /conf help         - Show this help message.
    """
    return help_text.strip()

# Command dispatch table
COMMAND_HANDLERS: Dict[str, Callable[[Dict[str, Any], List[str]], str]] = {
    "/list": _handle_list_conf,
    "/show": _handle_list_conf, # Alias
    "/get": _handle_get_conf,
    "/set": _handle_set_conf,
    "/delete": _handle_delete_conf,
    "/del": _handle_delete_conf,    # Alias
    "/rm": _handle_delete_conf,     # Alias
    "/drop": _handle_delete_conf,  # Add this line for /drop command
    "/help": _handle_help,
}

def handle_conf_command(command_args: str, memory: Dict[str, Any]) -> str:
    """
    Handles the /conf command, its subcommands, and wildcard listing.

    Args:
        command_args: The arguments string following the /conf command.
                      Example: "key:value", "get key", "set key value", "*_model", "/export path"
        memory: The current session memory dictionary.

    Returns:
        A string response to be displayed to the user.
    """
    conf_str = command_args.strip()        

    # Handle special subcommands first
    if conf_str.startswith("/export"):
        from autocoder.common.conf_import_export import export_conf
        export_path = conf_str[len("/export"):].strip()
        if not export_path:
            return "Error: Please specify a path for export. Usage: /conf /export <path>"
        try:
            export_conf(os.getcwd(), export_path)
            return f"Configuration exported successfully to {export_path}"
        except Exception as e:
            return f"Error exporting configuration: {e}"
    elif conf_str.startswith("/import"):
        from autocoder.common.conf_import_export import import_conf
        import_path = conf_str[len("/import"):].strip()
        if not import_path:
            return "Error: Please specify a path for import. Usage: /conf /import <path>"
        try:
            import_conf(os.getcwd(), import_path)
            # Reload memory after import might be needed depending on import_conf implementation
            # load_memory() # Consider if import_conf modifies the passed memory or global state
            return f"Configuration imported successfully from {import_path}. Use '/conf' to see changes."
        except Exception as e:
            return f"Error importing configuration: {e}"

    # Handle regular commands and listing/filtering
    args = conf_str.split()

    if not args:
        # Default action: list all configurations
        return _handle_list_conf(memory, [])
    else:
        command = args[0].lower()
        command_args_list = args[1:]        

        # Check if the first argument is a known command or potentially a pattern
        handler = COMMAND_HANDLERS.get(command)

        if handler:
            # It's a known command (list, get, set, delete, help)
            try:
                return handler(memory, command_args_list)
            except Exception as e:
                return f"An unexpected error occurred while executing '/conf {command}': {e}"
        elif "*" in command or "?" in command:
             # Treat as a list/filter pattern if it contains wildcards and is not a known command
             return _handle_list_conf(memory, [command]) # Pass the pattern as the argument to list
        else:
            # Handle legacy key:value format for setting (optional, can be removed if only set command is preferred)
            if ":" in conf_str and len(args) == 1: # Check if it looks like key:value and is a single "word"
                 parts = conf_str.split(":", 1)
                 if len(parts) == 2:
                     key, value_str = parts[0].strip(), parts[1].strip()
                     if key and value_str:
                         return _handle_set_conf(memory, [key, value_str])
                     else:
                         return f"Error: Invalid key:value format in '{conf_str}'. Use '/conf set {key} {value_str}' or '/conf help'."
                 else:
                      return f"Error: Unknown command or invalid format '{conf_str}'. Type '/conf help' for available commands."
            else:
                # If it's not a known command, not a wildcard, and not key:value format
                return f"Error: Unknown command '/conf {command}'. Type '/conf help' for available commands."