import os
import json
import shutil
from typing import Dict, Optional
from git import Repo
from pathlib import Path
from loguru import logger

def get_project_root(path: Optional[str] = None) -> str:
    """Get project root directory using git"""
    try:
        repo = Repo(path or os.getcwd(), search_parent_directories=True)
        return repo.working_dir
    except Exception as e:
        logger.warning(f"Failed to get git root: {e}")
        return path or os.getcwd()

def export_index(project_root: str, export_path: str) -> bool:
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
            logger.error(f"Index file not found at {index_path}")
            return False
            
        # Read and convert paths
        with open(index_path, "r") as f:
            index_data = json.load(f)
            
        # Convert absolute paths to relative
        converted_data = {}
        for abs_path, data in index_data.items():
            try:
                rel_path = os.path.relpath(abs_path, project_root)
                converted_data[rel_path] = data
            except ValueError:
                logger.warning(f"Could not convert path {abs_path}")
                converted_data[abs_path] = data
        
        # Write to export location
        export_file = os.path.join(export_path, "index.json")
        os.makedirs(export_path, exist_ok=True)
        with open(export_file, "w") as f:
            json.dump(converted_data, f, indent=2)
            
        return True
        
    except Exception as e:
        logger.error(f"Error exporting index: {e}")
        return False

def import_index(project_root: str, import_path: str) -> bool:
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
            logger.error(f"Import file not found at {import_file}")
            return False
            
        # Read and convert paths
        with open(import_file, "r") as f:
            index_data = json.load(f)
            
        # Convert relative paths to absolute
        converted_data = {}
        for rel_path, data in index_data.items():
            try:
                abs_path = os.path.join(project_root, rel_path)
                converted_data[abs_path] = data
            except Exception:
                logger.warning(f"Could not convert path {rel_path}")
                converted_data[rel_path] = data
        
        # Backup existing index
        index_path = os.path.join(project_root, ".auto-coder", "index.json")
        if os.path.exists(index_path):
            backup_path = index_path + ".bak"
            shutil.copy2(index_path, backup_path)
            logger.info(f"Backed up existing index to {backup_path}")
            
        # Write new index
        with open(index_path, "w") as f:
            json.dump(converted_data, f, indent=2)
            
        return True
        
    except Exception as e:
        logger.error(f"Error importing index: {e}")
        return False