import os
import json
import shutil
from loguru import logger
from autocoder.common.printer import Printer


def export_conf(project_root: str, export_path: str) -> bool:
    printer = Printer()
    """
    Export conf from memory.json to a specified directory

    Args:
        project_root: Project root directory
        export_path: Path to export the conf file

    Returns:
        bool: True if successful, False otherwise
    """
    project_root = os.path.abspath(project_root) or os.getcwd()
    try:
        memory_path = os.path.join(project_root, ".auto-coder", "plugins", "chat-auto-coder", "memory.json")
        if not os.path.exists(memory_path):
            printer.print_in_terminal("conf_not_found", path=memory_path)
            return False

        # Read and extract conf
        with open(memory_path, "r") as f:
            memory_data = json.load(f)

        conf_data = memory_data.get("conf", {})

        # Write to export location
        export_file = os.path.join(export_path, "conf.json")
        os.makedirs(export_path, exist_ok=True)
        with open(export_file, "w") as f:
            json.dump(conf_data, f, indent=2)

        return True

    except Exception as e:
        printer.print_in_terminal("conf_export_error", error=str(e))
        return False


def import_conf(project_root: str, import_path: str) -> bool:
    project_root = os.path.abspath(project_root) or os.getcwd()
    printer = Printer()
    """
    Import conf from a specified directory into memory.json

    Args:
        project_root: Project root directory
        import_path: Path containing the conf file to import

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import_file = os.path.join(import_path, "conf.json")
        if not os.path.exists(import_file):
            printer.print_in_terminal("conf_not_found", path=import_file)
            return False

        # Read conf file
        with open(import_file, "r") as f:
            conf_data = json.load(f)

        # Backup existing memory
        memory_path = os.path.join(project_root, ".auto-coder", "plugins", "chat-auto-coder", "memory.json")
        if os.path.exists(memory_path):
            backup_path = memory_path + ".bak"
            shutil.copy2(memory_path, backup_path)
            printer.print_in_terminal("conf_backup_success", path=backup_path)

        # Update conf in memory
        with open(memory_path, "r") as f:
            memory_data = json.load(f)

        memory_data["conf"] = conf_data

        # Write updated memory
        with open(memory_path, "w") as f:
            json.dump(memory_data, f, indent=2)

        return True

    except Exception as e:
        printer.print_in_terminal("conf_import_error", error=str(e))
        return False
