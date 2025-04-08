
import os
import json
from loguru import logger

def load_failed_files(failed_files_path: str) -> set:
    """
    Load the set of failed file paths from a JSON file.
    
    Args:
        failed_files_path: Path to the JSON file storing failed files.
    
    Returns:
        A set of failed file paths.
    """
    directory = os.path.dirname(failed_files_path)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    if os.path.exists(failed_files_path):
        try:
            with open(failed_files_path, "r", encoding="utf-8") as f:
                return set(json.load(f))
        except Exception:
            return set()
    return set()

def save_failed_files(failed_files_path: str, failed_files: set) -> None:
    """
    Save the set of failed file paths to a JSON file.
    
    Args:
        failed_files_path: Path to the JSON file.
        failed_files: A set of failed file paths.
    """
    try:
        with open(failed_files_path, "w", encoding="utf-8") as f:
            json.dump(list(failed_files), f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving failed files list: {e}")
