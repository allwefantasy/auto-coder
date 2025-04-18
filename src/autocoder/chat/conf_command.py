
from autocoder.auto_coder_runner import configure, print_conf
from typing import Dict, Any
import os

def handle_conf_command(command_args: str, memory: Dict[str, Any]):
    """
    Handles the /conf command and its subcommands like /export, /import.

    Args:
        command_args: The arguments string following the /conf command.
                      Example: "key:value", "/drop key", "/export path", "/import path", or ""
        memory: The current session memory dictionary, used here to pass
                configuration to print_conf.
    """
    conf_str = command_args.strip()

    if conf_str.startswith("/export"):
        from autocoder.common.conf_import_export import export_conf
        export_path = conf_str[len("/export"):].strip()
        if not export_path:
            print("Error: Please specify a path for export. Usage: /conf /export <path>")
            return
        export_conf(os.getcwd(), export_path)
    elif conf_str.startswith("/import"):
        from autocoder.common.conf_import_export import import_conf
        import_path = conf_str[len("/import"):].strip()
        if not import_path:
            print("Error: Please specify a path for import. Usage: /conf /import <path>")
            return
        import_conf(os.getcwd(), import_path)
    elif not conf_str:
        # If no arguments (and not /export or /import), print the current configuration
        print_conf(memory.get("conf", {}))
    else:
        # Handle setting, updating, or dropping keys
        # The configure function (imported from auto_coder_runner) handles
        # setting, updating, or dropping keys. It implicitly uses and saves
        # the global memory state defined within auto_coder_runner.
        # This includes handling "/drop key" internally.
        configure(conf_str)

# Future Enhancements:
# To make this more extensible and less reliant on the global state in
# auto_coder_runner, consider modifying the configure function to accept
# the memory dictionary and a save function as parameters.