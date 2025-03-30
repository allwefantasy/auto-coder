"""
Module providing a high-level API for managing compiler.yml configurations.
This module offers functions to create, retrieve, update, and delete compiler configurations
through a simple API interface that can be used in web services or other applications.
"""

import os
import yaml
from typing import Dict, List, Any, Optional, Tuple, Union
from pathlib import Path

from autocoder.compilers.compiler_config_manager import CompilerConfigManager, get_compiler_config_manager


class CompilerConfigAPI:
    """
    A high-level API for managing compiler configurations through a service interface.
    This class simplifies interacting with compiler.yml files and provides standardized
    response formats suitable for API endpoints.
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the CompilerConfigAPI.
        
        Args:
            config_path (Optional[str]): Path to the compiler.yml file.
                                        If None, will use .auto-coder/projects/compiler.yml.
        """
        self.config_manager = get_compiler_config_manager(config_path)
    
    def create_compiler(self, 
                       name: str, 
                       compiler_type: str, 
                       triggers: List[str],
                       working_dir: str, 
                       command: str, 
                       args: List[str], 
                       extract_regex: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a new compiler configuration.
        
        Args:
            name (str): Name of the compiler.
            compiler_type (str): Type of the compiler (e.g., 'frontend', 'backend').
            working_dir (str): Working directory for the compiler.
            command (str): The command to run.
            args (List[str]): List of arguments for the command.
            extract_regex (Optional[str]): Regular expression to extract error information.
            
        Returns:
            Dict[str, Any]: API response with status and result information.
        """
        try:
            # Validate inputs
            if not name or not name.strip():
                return self._error_response("Compiler name cannot be empty")
            
            if not command or not command.strip():
                return self._error_response("Command cannot be empty")
            
            # Create compiler config
            compiler_config = self.config_manager.create_compiler_config(
                name=name,
                type=compiler_type,
                working_dir=working_dir,
                command=command,
                args=args,
                triggers=triggers,
                extract_regex=extract_regex
            )
            
            # Add it to the configuration
            success = self.config_manager.add_compiler(compiler_config)
            
            if success:
                return {
                    "status": "success",
                    "message": f"Compiler '{name}' created successfully",
                    "data": compiler_config
                }
            else:
                return self._error_response(f"Failed to create compiler '{name}'")
        
        except ValueError as e:
            return self._error_response(str(e))
        except Exception as e:
            return self._error_response(f"Unexpected error: {str(e)}")
    
    def get_compiler(self, name: str) -> Dict[str, Any]:
        """
        Get a specific compiler configuration.
        
        Args:
            name (str): Name of the compiler to retrieve.
            
        Returns:
            Dict[str, Any]: API response with status and compiler configuration.
        """
        try:
            compiler_config = self.config_manager.get_compiler_by_name(name)
            
            if compiler_config:
                return {
                    "status": "success",
                    "data": compiler_config
                }
            else:
                return self._error_response(f"Compiler '{name}' not found", status_code=404)
        
        except FileNotFoundError:
            return self._error_response("Configuration file not found", status_code=404)
        except Exception as e:
            return self._error_response(f"Unexpected error: {str(e)}")
    
    def list_compilers(self) -> Dict[str, Any]:
        """
        List all compiler configurations.
        
        Returns:
            Dict[str, Any]: API response with status and list of compilers.
        """
        try:
            compilers = self.config_manager.get_all_compilers()
            
            return {
                "status": "success",
                "data": compilers,
                "count": len(compilers)
            }
        
        except FileNotFoundError:
            # Return empty list if file doesn't exist
            return {
                "status": "success",
                "data": [],
                "count": 0
            }
        except Exception as e:
            return self._error_response(f"Unexpected error: {str(e)}")
    
    def update_compiler(self, 
                       name: str, 
                       compiler_type: Optional[str] = None,
                       working_dir: Optional[str] = None,
                       command: Optional[str] = None,
                       args: Optional[List[str]] = None,
                       triggers: Optional[List[str]] = None,
                       extract_regex: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing compiler configuration.
        
        Args:
            name (str): Name of the compiler to update.
            compiler_type (Optional[str]): Type of the compiler.
            working_dir (Optional[str]): Working directory for the compiler.
            command (Optional[str]): The command to run.
            args (Optional[List[str]]): List of arguments for the command.
            extract_regex (Optional[str]): Regular expression to extract error information.
            
        Returns:
            Dict[str, Any]: API response with status and result information.
        """
        try:
            # Get existing compiler
            existing_config = self.config_manager.get_compiler_by_name(name)
            if not existing_config:
                return self._error_response(f"Compiler '{name}' not found", status_code=404)
            
            # Create updated config by merging with existing values
            updated_config = existing_config.copy()
            
            if compiler_type is not None:
                updated_config["type"] = compiler_type
            
            if working_dir is not None:
                updated_config["working_dir"] = working_dir
            
            if command is not None:
                updated_config["command"] = command
            
            if args is not None:
                updated_config["args"] = args
            
            if extract_regex is not None:
                updated_config["extract_regex"] = extract_regex

            if triggers is not None:
                updated_config["triggers"] = triggers
                
            # Update the configuration
            success = self.config_manager.update_compiler(name, updated_config)
            
            if success:
                return {
                    "status": "success",
                    "message": f"Compiler '{name}' updated successfully",
                    "data": updated_config
                }
            else:
                return self._error_response(f"Failed to update compiler '{name}'")
        
        except ValueError as e:
            return self._error_response(str(e))
        except FileNotFoundError:
            return self._error_response("Configuration file not found", status_code=404)
        except Exception as e:
            return self._error_response(f"Unexpected error: {str(e)}")
    
    def delete_compiler(self, name: str) -> Dict[str, Any]:
        """
        Delete a compiler configuration.
        
        Args:
            name (str): Name of the compiler to delete.
            
        Returns:
            Dict[str, Any]: API response with status and result information.
        """
        try:
            success = self.config_manager.delete_compiler(name)
            
            if success:
                return {
                    "status": "success",
                    "message": f"Compiler '{name}' deleted successfully"
                }
            else:
                return self._error_response(f"Failed to delete compiler '{name}'")
        
        except ValueError as e:
            return self._error_response(str(e))
        except FileNotFoundError:
            return self._error_response("Configuration file not found", status_code=404)
        except Exception as e:
            return self._error_response(f"Unexpected error: {str(e)}")
    
    def initialize_config(self) -> Dict[str, Any]:
        """
        Initialize a default compiler configuration file if it doesn't exist.
        
        Returns:
            Dict[str, Any]: API response with status and result information.
        """
        try:
            if self.config_manager.exists():
                return {
                    "status": "success",
                    "message": "Configuration file already exists",
                    "data": self.config_manager.get_all_compilers()
                }
            
            success = self.config_manager.init_default_config()
            
            if success:
                return {
                    "status": "success",
                    "message": "Configuration file initialized with default settings",
                    "data": self.config_manager.get_all_compilers()
                }
            else:
                return self._error_response("Failed to initialize configuration file")
        
        except Exception as e:
            return self._error_response(f"Unexpected error: {str(e)}")
    
    def validate_config(self) -> Dict[str, Any]:
        """
        Validate the structure of the compiler.yml file.
        
        Returns:
            Dict[str, Any]: API response with validation results.
        """
        try:
            if not self.config_manager.exists():
                return self._error_response("Configuration file does not exist", status_code=404)
            
            config = self.config_manager.read()
            
            # Check if compilers section exists
            if "compilers" not in config:
                return self._error_response("Invalid configuration: missing 'compilers' section")
            
            if not isinstance(config["compilers"], list):
                return self._error_response("Invalid configuration: 'compilers' must be a list")
            
            # Validate each compiler
            validation_errors = []
            for i, compiler in enumerate(config["compilers"]):
                errors = self._validate_compiler_config(compiler, i)
                validation_errors.extend(errors)
            
            if validation_errors:
                return {
                    "status": "error",
                    "message": "Configuration validation failed",
                    "errors": validation_errors
                }
            
            return {
                "status": "success",
                "message": "Configuration validation passed",
                "data": config
            }
        
        except yaml.YAMLError:
            return self._error_response("Invalid YAML format in configuration file")
        except Exception as e:
            return self._error_response(f"Unexpected error: {str(e)}")
    
    def _validate_compiler_config(self, compiler: Dict[str, Any], index: int) -> List[str]:
        """
        Validate an individual compiler configuration.
        
        Args:
            compiler (Dict[str, Any]): The compiler configuration to validate.
            index (int): Index of the compiler in the list (for error reporting).
            
        Returns:
            List[str]: List of validation error messages.
        """
        errors = []
        
        # Check required fields
        if "name" not in compiler or not compiler["name"]:
            errors.append(f"Compiler at index {index}: missing or empty 'name' field")
        
        if "command" not in compiler or not compiler["command"]:
            errors.append(f"Compiler '{compiler.get('name', f'at index {index}')}': missing or empty 'command' field")
        
        # Check args is a list
        if "args" in compiler and not isinstance(compiler["args"], list):
            errors.append(f"Compiler '{compiler.get('name', f'at index {index}')}': 'args' must be a list")
        
        return errors
    
    def _error_response(self, message: str, status_code: int = 400) -> Dict[str, Any]:
        """
        Create a standardized error response.
        
        Args:
            message (str): Error message.
            status_code (int): HTTP-like status code.
            
        Returns:
            Dict[str, Any]: Standardized error response.
        """
        return {
            "status": "error",
            "message": message,
            "code": status_code
        }


def get_compiler_config_api(config_path: Optional[str] = None) -> CompilerConfigAPI:
    """
    Factory function to get a CompilerConfigAPI instance.
    
    Args:
        config_path (Optional[str]): Path to the compiler.yml file.
        
    Returns:
        CompilerConfigAPI: An instance of the CompilerConfigAPI.
    """
    return CompilerConfigAPI(config_path=config_path) 