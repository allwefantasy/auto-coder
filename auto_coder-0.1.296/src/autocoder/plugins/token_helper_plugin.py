"""
Token Helper Plugin for Chat Auto Coder.
Provides token counting functionality for files and projects.
"""

import os
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

from autocoder.plugins import Plugin, PluginManager
from autocoder.rag.token_counter import count_tokens
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs, SourceCode
from loguru import logger
import json


@dataclass
class TokenCount:
    """Represents token count information for a file."""
    filename: str
    tokens: int
    relative_path: Optional[str] = None
    file_size: Optional[int] = None


class TokenHelperPlugin(Plugin):
    """Token helper plugin for the Chat Auto Coder."""

    name = "token_helper"
    description = "Token helper plugin providing token counting for files and projects"
    version = "0.1.0"

    def __init__(self, manager: PluginManager, config: Optional[Dict[str, Any]] = None, config_path: Optional[str] = None):
        """Initialize the Token helper plugin."""
        super().__init__(manager, config, config_path)
        self.token_counts = {}
        self.project_dir = os.getcwd()        
        self.base_persist_dir = os.path.join(".auto-coder", "plugins", "chat-auto-coder")        
        self.auto_coder_config = {}
        self.exclude_files = []

    def load_auto_coder_config(self):
        memory_path = os.path.join(self.base_persist_dir, "memory.json")
        if os.path.exists(memory_path):
            with open(memory_path, "r", encoding="utf-8") as f:
                _memory = json.load(f)
                self.auto_coder_config = _memory.get("conf",{})   
                self.exclude_files = _memory.get("exclude_files",[])

    def initialize(self) -> bool:
        """Initialize the plugin.

        Returns:
            True if initialization was successful
        """
        self.load_auto_coder_config()
        print(f"[{self.name}] Token Helper plugin initialized")
        return True

    def get_commands(self) -> Dict[str, Tuple[Callable, str]]:
        """Get commands provided by this plugin.

        Returns:
            A dictionary of command name to handler and description
        """
        return {
            "token/count": (self.count_tokens_in_project, "Count tokens in all project files"),
            "token/top": (self.show_top_token_files, "Show top N files by token count"),
            "token/file": (self.count_tokens_in_file, "Count tokens in a specific file"),
            "token/summary": (self.show_token_summary, "Show token count summary for the project"),
        }

    def get_completions(self) -> Dict[str, List[str]]:
        """Get completions provided by this plugin.

        Returns:
            A dictionary mapping command prefixes to completion options
        """
        completions = {
            "/token/count": [],
            "/token/top": ["5", "10", "20", "50", "100"],
            "/token/file": [],
            "/token/summary": [],
        }
        return completions

    def count_tokens_in_project(self, args: str) -> None:
        """Count tokens in all project files.
        
        Args:
            args: Optional arguments including project directory and file types
        """
        args_dict = self._parse_args(args)
        project_dir = args_dict.get("dir", self.auto_coder_config.get("project_dir", os.getcwd()))
        project_type = args_dict.get("type", self.auto_coder_config.get("project_type", ".py"))
        exclude = args_dict.get("exclude_files", [])
        
        self.project_dir = project_dir
        print(f"Counting tokens in project: {project_dir}")
        print(f"File types: {project_type}")
        
        try:
            # Create AutoCoderArgs with necessary parameters
            coder_args = AutoCoderArgs(
                source_dir=project_dir,
                project_type=project_type,
                exclude_files=[f"regex://{exclude}"] + self.exclude_files if exclude else self.exclude_files
            )
            
            # Use SuffixProject to get all source files
            project = SuffixProject(args=coder_args)
            
            total_tokens = 0
            file_count = 0
            self.token_counts = {}
            
            print("Scanning files and counting tokens...")
            
            for source_code in project.get_source_codes():
                file_count += 1
                if file_count % 10 == 0:
                    print(f"Processed {file_count} files...")
                
                tokens = count_tokens(source_code.source_code)
                file_path = source_code.module_name
                relative_path = os.path.relpath(file_path, project_dir)
                file_size = len(source_code.source_code)
                
                self.token_counts[file_path] = TokenCount(
                    filename=file_path,
                    tokens=tokens,
                    relative_path=relative_path,
                    file_size=file_size
                )
                
                total_tokens += tokens
            
            print(f"\nToken count complete!")
            print(f"Total files: {file_count}")
            print(f"Total tokens: {total_tokens:,}")
            print(f"Use /token/top N to see the top N files by token count")
            print(f"Use /token/summary to see a summary by file type")
            
        except Exception as e:
            logger.error(f"Error counting tokens in project: {str(e)}")
            print(f"Error: {str(e)}")

    def _parse_args(self, args: str) -> Dict[str, str]:
        """Parse command arguments.
        
        Args:
            args: Command arguments string. Supports both:
                 - Key=value format: dir=. type=.py,.java
                 - Command line format: --dir . --type .py,.java
            
        Returns:
            Dictionary of parsed arguments
        """
        result = {}
        if not args:
            return result
            
        # Try using argparse first
        try:
            import argparse
            import shlex
            
            # Create parser with arguments expected by the plugin
            parser = argparse.ArgumentParser(description='Token counter options')
            parser.add_argument('--dir', '-d', help='Project directory')
            parser.add_argument('--type', '-t', help='File types (comma separated)')
            parser.add_argument('--exclude', '-e', help='Exclude pattern')
            parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
            
            # Parse with shlex to handle quoted arguments properly
            parsed_args, unknown = parser.parse_known_args(shlex.split(args))
            
            # Convert namespace to dictionary, ignoring None values
            for key, value in vars(parsed_args).items():
                if value is not None:
                    result[key] = value
                    
            # Handle any unknown arguments as key=value pairs
            for arg in unknown:
                if '=' in arg:
                    key, value = arg.split('=', 1)
                    # Strip leading dashes if present
                    if key.startswith('--'):
                        key = key[2:]
                    elif key.startswith('-'):
                        key = key[1:]
                    result[key] = value
            
            return result
            
        except Exception as e:
            # Fallback to original implementation if argparse fails
            logger.debug(f"Argparse failed, using fallback parser: {str(e)}")
            
            parts = args.split()
            i = 0
            while i < len(parts):
                part = parts[i]
                
                # Handle key=value format
                if "=" in part:
                    key, value = part.split("=", 1)
                    # Strip leading dashes if present
                    if key.startswith("--"):
                        key = key[2:]
                    elif key.startswith("-"):
                        key = key[1:]
                    result[key] = value
                    i += 1
                    continue
                    
                # Handle --key value or -key value format
                if part.startswith("--"):
                    key = part[2:]
                    # Check if there's a value following this key
                    if i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                        result[key] = parts[i + 1]
                        i += 2
                    else:
                        # Flag option without value
                        result[key] = "true"
                        i += 1
                elif part.startswith("-"):
                    key = part[1:]
                    # Check if there's a value following this key
                    if i + 1 < len(parts) and not parts[i + 1].startswith("-"):
                        result[key] = parts[i + 1]
                        i += 2
                    else:
                        # Flag option without value
                        result[key] = "true"
                        i += 1
                else:
                    # Standalone argument without a key
                    i += 1
            
            return result

    def show_top_token_files(self, args: str) -> None:
        """Show top N files by token count.
        
        Args:
            args: Number of files to show
        """
        if not self.token_counts:
            print("No token count data available. Run /token/count first.")
            return
            
        try:
            n = int(args.strip()) if args.strip() else 10
        except ValueError:
            print(f"Invalid value: {args}. Using default of 10.")
            n = 10
            
        print(f"\nTop {n} files by token count:")
        print(f"{'Tokens':<10} {'Size (bytes)':<15} {'File'}")
        print(f"{'-'*10} {'-'*15} {'-'*50}")
        
        sorted_files = sorted(
            self.token_counts.values(), 
            key=lambda x: x.tokens, 
            reverse=True
        )
        
        for i, token_count in enumerate(sorted_files[:n], 1):
            relative_path = token_count.relative_path or token_count.filename
            print(f"{token_count.tokens:<10,} {token_count.file_size:<15,} {relative_path}")

    def count_tokens_in_file(self, args: str) -> None:
        """Count tokens in a specific file.
        
        Args:
            args: Path to the file
        """
        if not args:
            print("Please specify a file path.")
            return
            
        file_path = args.strip()
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            tokens = count_tokens(content)
            print(f"\nFile: {file_path}")
            print(f"Tokens: {tokens:,}")
            print(f"File size: {len(content):,} bytes")
            print(f"Avg bytes per token: {len(content)/tokens:.2f}")
            
        except Exception as e:
            print(f"Error counting tokens in file: {str(e)}")

    def show_token_summary(self, args: str) -> None:
        """Show token count summary by file type.
        
        Args:
            args: Optional arguments
        """
        if not self.token_counts:
            print("No token count data available. Run /token/count first.")
            return
            
        by_extension = defaultdict(lambda: {"files": 0, "tokens": 0, "size": 0})
        
        for token_count in self.token_counts.values():
            filename = token_count.filename
            ext = os.path.splitext(filename)[1].lower() or "no_extension"
            
            by_extension[ext]["files"] += 1
            by_extension[ext]["tokens"] += token_count.tokens
            by_extension[ext]["size"] += token_count.file_size or 0
            
        total_tokens = sum(data["tokens"] for data in by_extension.values())
        total_files = sum(data["files"] for data in by_extension.values())
        total_size = sum(data["size"] for data in by_extension.values())
        
        print(f"\nToken count summary by file type:")
        print(f"{'Extension':<12} {'Files':<8} {'Tokens':<12} {'% of Total':<12} {'Size (KB)':<12}")
        print(f"{'-'*12} {'-'*8} {'-'*12} {'-'*12} {'-'*12}")
        
        for ext, data in sorted(by_extension.items(), key=lambda x: x[1]["tokens"], reverse=True):
            percent = (data["tokens"] / total_tokens * 100) if total_tokens > 0 else 0
            size_kb = data["size"] / 1024
            print(f"{ext:<12} {data['files']:<8} {data['tokens']:<12,} {percent:<12.2f} {size_kb:<12.2f}")
            
        print(f"\nTotal Files: {total_files:,}")
        print(f"Total Tokens: {total_tokens:,}")
        print(f"Total Size: {total_size/1024/1024:.2f} MB")
        
        if self.project_dir:
            print(f"Project Directory: {self.project_dir}")

    def shutdown(self) -> None:
        """Shutdown the plugin."""
        print(f"[{self.name}] Token Helper plugin shutdown") 