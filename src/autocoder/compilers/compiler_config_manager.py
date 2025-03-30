"""
Module providing utilities for managing compiler.yml configuration files.
This module offers functions to read, write, add, update, delete, and query compiler configurations.
"""

import os
import yaml
from typing import Dict, List, Any, Optional, Union
from pathlib import Path


class CompilerConfigManager:
    """
    A utility class for managing compiler configuration files (compiler.yml).
    Provides methods to read, write, add, modify, delete, and query compiler configurations.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the CompilerConfigManager.
        
        Args:
            config_path (Optional[str]): Path to the compiler.yml file. 
                                        If None, will use .auto-coder/projects/compiler.yml.
        """
        self.config_path = config_path or ".auto-coder/projects/compiler.yml"
    
    def exists(self) -> bool:
        """
        Check if the configuration file exists.
        
        Returns:
            bool: True if the configuration file exists, False otherwise.
        """
        return os.path.exists(self.config_path)
    
    def read(self) -> Dict[str, Any]:
        """
        Read the compiler configuration from YAML file.
        
        Returns:
            Dict[str, Any]: The compiler configuration as a dictionary.
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            yaml.YAMLError: If the YAML file is invalid.
        """
        if not self.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        with open(self.config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        # Ensure the config has a compilers section
        if config is None:
            config = {"compilers": []}
        elif "compilers" not in config:
            config["compilers"] = []
            
        return config
    
    def write(self, config: Dict[str, Any]) -> bool:
        """
        Write a compiler configuration to the YAML file.
        
        Args:
            config (Dict[str, Any]): The compiler configuration to write.
            
        Returns:
            bool: True if the write operation was successful, False otherwise.
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.config_path)), exist_ok=True)
            
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
            return True
        except Exception:
            return False
    
    def get_all_compilers(self) -> List[Dict[str, Any]]:
        """
        Get all compiler configurations from the file.
        
        Returns:
            List[Dict[str, Any]]: List of all compiler configurations.
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
        """
        config = self.read()
        return config.get("compilers", [])
    
    def get_compiler_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific compiler configuration by name.
        
        Args:
            name (str): The name of the compiler to find.
            
        Returns:
            Optional[Dict[str, Any]]: The compiler configuration if found, None otherwise.
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
        """
        compilers = self.get_all_compilers()
        for compiler in compilers:
            if compiler.get("name") == name:
                return compiler
        return None
    
    def add_compiler(self, compiler_config: Dict[str, Any]) -> bool:
        """
        Add a new compiler configuration to the file.
        
        Args:
            compiler_config (Dict[str, Any]): The compiler configuration to add.
            
        Returns:
            bool: True if the operation was successful, False otherwise.
            
        Raises:
            ValueError: If a compiler with the same name already exists.
            FileNotFoundError: If the configuration file doesn't exist and couldn't be created.
        """
        name = compiler_config.get("name")
        if not name:
            raise ValueError("Compiler configuration must have a 'name' field")
            
        try:
            # Try to read existing config or create a new one
            try:
                config = self.read()
            except FileNotFoundError:
                config = {"compilers": []}
            
            # Check if a compiler with this name already exists
            for existing in config.get("compilers", []):
                if existing.get("name") == name:
                    raise ValueError(f"A compiler with name '{name}' already exists")
            
            # Add the new compiler config
            config["compilers"].append(compiler_config)
            
            # Write back to file
            return self.write(config)
        except Exception:
            return False
    
    def update_compiler(self, name: str, updated_config: Dict[str, Any]) -> bool:
        """
        Update an existing compiler configuration.
        
        Args:
            name (str): The name of the compiler to update.
            updated_config (Dict[str, Any]): The updated compiler configuration.
            
        Returns:
            bool: True if the operation was successful, False otherwise.
            
        Raises:
            ValueError: If no compiler with the given name exists.
            FileNotFoundError: If the configuration file doesn't exist.
        """
        try:
            config = self.read()
            found = False
            
            # Update the compiler with matching name
            for i, compiler in enumerate(config.get("compilers", [])):
                if compiler.get("name") == name:
                    # Preserve the original name
                    updated_config["name"] = name
                    config["compilers"][i] = updated_config
                    found = True
                    break
            
            if not found:
                raise ValueError(f"No compiler with name '{name}' found")
                
            # Write back to file
            return self.write(config)
        except Exception:
            return False
    
    def delete_compiler(self, name: str) -> bool:
        """
        Delete a compiler configuration from the file.
        
        Args:
            name (str): The name of the compiler to delete.
            
        Returns:
            bool: True if the operation was successful, False otherwise.
            
        Raises:
            ValueError: If no compiler with the given name exists.
            FileNotFoundError: If the configuration file doesn't exist.
        """
        try:
            config = self.read()
            original_length = len(config.get("compilers", []))
            
            # Filter out the compiler with the matching name
            config["compilers"] = [
                compiler for compiler in config.get("compilers", [])
                if compiler.get("name") != name
            ]
            
            if len(config["compilers"]) == original_length:
                raise ValueError(f"No compiler with name '{name}' found")
                
            # Write back to file
            return self.write(config)
        except Exception:
            return False
    
    def create_compiler_config(self, 
                               name: str, 
                               type: str, 
                               working_dir: str, 
                               command: str, 
                               args: List[str], 
                               triggers: List[str],
                               extract_regex: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new compiler configuration dictionary.
        
        Args:
            name (str): Name of the compiler.
            type (str): Type of the compiler (e.g., 'frontend', 'backend').
            working_dir (str): Working directory for the compiler.
            command (str): The command to run.
            args (List[str]): List of arguments for the command.
            extract_regex (Optional[str]): Regular expression to extract error information.
            
        Returns:
            Dict[str, Any]: A new compiler configuration dictionary.
        """
        compiler_config = {
            "name": name,
            "type": type,
            "working_dir": working_dir,
            "command": command,
            "args": args,
            "triggers": triggers
        }
        
        if extract_regex:
            compiler_config["extract_regex"] = extract_regex
            
        return compiler_config
    
    def list_compiler_names(self) -> List[str]:
        """
        Get a list of all compiler names from the configuration.
        
        Returns:
            List[str]: List of compiler names.
            
        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
        """
        compilers = self.get_all_compilers()
        return [compiler.get("name") for compiler in compilers if compiler.get("name")]

    def init_default_config(self) -> bool:
        """
        Initialize a default compiler configuration file if it doesn't exist.
        
        Returns:
            bool: True if initialization was successful, False otherwise.
        """
        if self.exists():
            return True
            
        default_config = {
            "compilers": [
                {
                    "name": "Frontend Build",
                    "type": "frontend",
                    "working_dir": "src/frontend",
                    "command": "npm",
                    "args": ["run", "build"],
                    "extract_regex": "(?P<severity>error|warning)\\s+in\\s+(?P<file>[^:]+):(?P<line>\\d+):(?P<column>\\d+)\\s*-\\s*(?P<message>.+)"
                }
            ]
        }
        
        return self.write(default_config)


def get_compiler_config_manager(config_path: Optional[str] = None) -> CompilerConfigManager:
    """
    Factory function to get a CompilerConfigManager instance.
    
    Args:
        config_path (Optional[str]): Path to the compiler.yml file.
        
    Returns:
        CompilerConfigManager: An instance of the CompilerConfigManager.
    """
    return CompilerConfigManager(config_path=config_path) 