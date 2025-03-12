import os
import json
import shutil
from loguru import logger
from autocoder.common.printer import Printer
from autocoder.common.result_manager import ResultManager

result_manager = ResultManager()


def export_index(project_root: str, export_path: str) -> bool:
    printer = Printer()
    """
    Export index.json with absolute paths converted to relative paths
    
    Args:
        project_root: Project root directory
        export_path: Path to export the index file
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        index_path = os.path.join(project_root, ".auto-coder", "index.json")
        if not os.path.exists(index_path):
            printer.print_in_terminal("index_not_found", path=index_path)
            return False

        # Read and convert paths
        with open(index_path, "r",encoding="utf-8") as f:
            index_data = json.load(f)

        # Convert absolute paths to relative
        converted_data = {}
        for abs_path, data in index_data.items():
            try:
                rel_path = os.path.relpath(abs_path, project_root)
                data["module_name"] = rel_path
                converted_data[rel_path] = data
            except ValueError:
                printer.print_in_terminal(
                    "index_convert_path_fail", path=abs_path)
                converted_data[abs_path] = data

        # Write to export location
        export_file = os.path.join(export_path, "index.json")
        os.makedirs(export_path, exist_ok=True)
        with open(export_file, "w",encoding="utf-8") as f:
            json.dump(converted_data, f, indent=2)
        printer.print_in_terminal("index_export_success", path=export_file)
        result_manager.add_result(content=printer.get_message_from_key_with_format("index_export_success", path=export_file), meta={"action": "index_export", "input": {
            "path": export_file
        }})
        return True

    except Exception as e:
        printer.print_in_terminal("index_error", error=str(e))
        result_manager.add_result(content=printer.get_message_from_key_with_format("index_error", error=str(e)), meta={"action": "index_export", "input": {
            "path": export_file
        }})
        return False


def import_index(project_root: str, import_path: str) -> bool:
    printer = Printer()
    """
    Import index.json with relative paths converted to absolute paths
    
    Args:
        project_root: Project root directory
        import_path: Path containing the index file to import
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        import_file = os.path.join(import_path, "index.json")
        if not os.path.exists(import_file):
            printer.print_in_terminal("index_not_found", path=import_file)
            return False

        # Read and convert paths
        with open(import_file, "r",encoding="utf-8") as f:
            index_data = json.load(f)

        # Convert relative paths to absolute
        converted_data = {}
        for rel_path, data in index_data.items():
            try:
                abs_path = os.path.join(project_root, rel_path)
                data["module_name"] = abs_path
                converted_data[abs_path] = data
            except Exception:
                printer.print_in_terminal(
                    "index_convert_path_fail", path=rel_path)
                converted_data[rel_path] = data

        # Backup existing index
        index_path = os.path.join(project_root, ".auto-coder", "index.json")
        if os.path.exists(index_path):
            backup_path = index_path + ".bak"
            shutil.copy2(index_path, backup_path)
            printer.print_in_terminal("index_backup_success", path=backup_path)

        # Write new index
        with open(index_path, "w",encoding="utf-8") as f:
            json.dump(converted_data, f, indent=2)
        
        printer.print_in_terminal("index_import_success", path=index_path)
        result_manager.add_result(content=printer.get_message_from_key_with_format("index_import_success", path=index_path), meta={"action": "index_import", "input": {
            "path": index_path
        }})

        return True

    except Exception as e:
        printer.print_in_terminal("index_error", error=str(e))
        result_manager.add_result(content=printer.get_message_from_key_with_format("index_error", error=str(e)), meta={"action": "index_import", "input": {
            "path": index_path
        }})
        return False
