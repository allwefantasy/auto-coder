"""
LLM Friendly Package Manager

This module provides a class-based interface for managing LLM friendly packages,
including operations like get, list, list_all, add, remove, refresh, etc.
"""

import os
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
import git
from filelock import FileLock


@dataclass
class LibraryInfo:
    """Information about a library"""
    domain: str
    username: str
    lib_name: str
    full_path: str
    is_added: bool
    has_md_files: bool = True


@dataclass
class PackageDoc:
    """Package documentation information"""
    file_path: str
    content: Optional[str] = None


class LLMFriendlyPackageManager:
    """Manager for LLM friendly packages"""
    
    def __init__(self, project_root: str = None, base_persist_dir: str = None):
        """
        Initialize the package manager
        
        Args:
            project_root: Project root directory, defaults to current working directory
            base_persist_dir: Base directory for persistence, defaults to .auto-coder/plugins/chat-auto-coder
        """
        self.project_root = project_root or os.getcwd()
        self.base_persist_dir = base_persist_dir or os.path.join(
            self.project_root, ".auto-coder", "plugins", "chat-auto-coder"
        )
        self.lib_dir = os.path.join(self.project_root, ".auto-coder", "libs")
        self.llm_friendly_packages_dir = os.path.join(self.lib_dir, "llm_friendly_packages")
        self.console = Console()
        
        # Ensure directories exist
        os.makedirs(self.lib_dir, exist_ok=True)
        os.makedirs(self.base_persist_dir, exist_ok=True)
    
    def _get_memory_path(self) -> str:
        """Get memory file path"""
        return os.path.join(self.base_persist_dir, "memory.json")
    
    def _load_memory(self) -> Dict[str, Any]:
        """Load memory from file"""
        memory_path = self._get_memory_path()
        lock_path = memory_path + ".lock"
        
        default_memory = {
            "conversation": [],
            "current_files": {"files": [], "groups": {}},
            "conf": {},
            "exclude_dirs": [],
            "mode": "auto_detect",
            "libs": {}
        }
        
        if not os.path.exists(memory_path):
            return default_memory
            
        try:
            with FileLock(lock_path, timeout=30):
                with open(memory_path, "r", encoding="utf-8") as f:
                    memory = json.load(f)
                    # Ensure libs key exists
                    if "libs" not in memory:
                        memory["libs"] = {}
                    return memory
        except Exception:
            return default_memory
    
    def _save_memory(self, memory: Dict[str, Any]) -> None:
        """Save memory to file"""
        memory_path = self._get_memory_path()
        lock_path = memory_path + ".lock"
        
        with FileLock(lock_path, timeout=30):
            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump(memory, f, indent=2, ensure_ascii=False)
    
    def _get_current_proxy(self) -> str:
        """Get current proxy URL"""
        memory = self._load_memory()
        return memory.get("lib-proxy", "https://github.com/allwefantasy/llm_friendly_packages")
    
    def _clone_repository(self) -> bool:
        """Clone the llm_friendly_packages repository"""
        if os.path.exists(self.llm_friendly_packages_dir):
            return True
            
        self.console.print("Cloning llm_friendly_packages repository...")
        try:
            proxy_url = self._get_current_proxy()
            git.Repo.clone_from(proxy_url, self.llm_friendly_packages_dir)
            self.console.print("Successfully cloned llm_friendly_packages repository")
            return True
        except git.exc.GitCommandError as e:
            self.console.print(f"Error cloning repository: {e}")
            return False
    
    def get_docs(self, package_name: Optional[str] = None, return_paths: bool = False) -> List[str]:
        """
        Get documentation for packages
        
        Args:
            package_name: Specific package name to get docs for, None for all packages
            return_paths: If True, return file paths; if False, return file contents
            
        Returns:
            List of documentation content or file paths
        """
        docs = []
        
        if not os.path.exists(self.llm_friendly_packages_dir):
            return docs
        
        memory = self._load_memory()
        libs = list(memory.get("libs", {}).keys())
        
        for domain in os.listdir(self.llm_friendly_packages_dir):
            domain_path = os.path.join(self.llm_friendly_packages_dir, domain)
            if not os.path.isdir(domain_path):
                continue
                
            for username in os.listdir(domain_path):
                username_path = os.path.join(domain_path, username)
                if not os.path.isdir(username_path):
                    continue
                    
                for lib_name in os.listdir(username_path):
                    lib_path = os.path.join(username_path, lib_name)
                    
                    # Check if this is the requested package
                    if not os.path.isdir(lib_path):
                        continue
                        
                    if package_name is not None:
                        if not (lib_name == package_name or 
                               package_name == os.path.join(username, lib_name)):
                            continue
                    
                    # Check if library is added
                    if lib_name not in libs:
                        continue
                    
                    # Collect markdown files
                    for root, _, files in os.walk(lib_path):
                        for file in files:
                            if file.endswith(".md"):
                                file_path = os.path.join(root, file)
                                if return_paths:
                                    docs.append(file_path)
                                else:
                                    try:
                                        with open(file_path, "r", encoding="utf-8") as f:
                                            docs.append(f.read())
                                    except Exception as e:
                                        self.console.print(f"Error reading {file_path}: {e}")
        
        return docs
    
    def list_added_libraries(self) -> List[str]:
        """List all added libraries"""
        memory = self._load_memory()
        return list(memory.get("libs", {}).keys())
    
    def list_all_available_libraries(self) -> List[LibraryInfo]:
        """List all available libraries in the repository"""
        if not os.path.exists(self.llm_friendly_packages_dir):
            return []
        
        available_libs = []
        memory = self._load_memory()
        added_libs = set(memory.get("libs", {}).keys())
        
        for domain in os.listdir(self.llm_friendly_packages_dir):
            domain_path = os.path.join(self.llm_friendly_packages_dir, domain)
            if not os.path.isdir(domain_path):
                continue
                
            for username in os.listdir(domain_path):
                username_path = os.path.join(domain_path, username)
                if not os.path.isdir(username_path):
                    continue
                    
                for lib_name in os.listdir(username_path):
                    lib_path = os.path.join(username_path, lib_name)
                    if not os.path.isdir(lib_path):
                        continue
                    
                    # Check if has markdown files
                    has_md_files = False
                    for root, _, files in os.walk(lib_path):
                        if any(file.endswith('.md') for file in files):
                            has_md_files = True
                            break
                    
                    if has_md_files:
                        available_libs.append(LibraryInfo(
                            domain=domain,
                            username=username,
                            lib_name=lib_name,
                            full_path=f"{username}/{lib_name}",
                            is_added=lib_name in added_libs,
                            has_md_files=has_md_files
                        ))
        
        # Sort by domain, username, lib_name
        available_libs.sort(key=lambda x: (x.domain, x.username, x.lib_name))
        return available_libs
    
    def add_library(self, lib_name: str) -> bool:
        """
        Add a library to the list
        
        Args:
            lib_name: Library name to add
            
        Returns:
            True if successful, False otherwise
        """
        # Clone repository if needed
        if not self._clone_repository():
            return False
        
        memory = self._load_memory()
        
        if lib_name in memory["libs"]:
            self.console.print(f"Library {lib_name} is already added")
            return False
        
        memory["libs"][lib_name] = {}
        self._save_memory(memory)
        self.console.print(f"Added library: {lib_name}")
        return True
    
    def remove_library(self, lib_name: str) -> bool:
        """
        Remove a library from the list
        
        Args:
            lib_name: Library name to remove
            
        Returns:
            True if successful, False otherwise
        """
        memory = self._load_memory()
        
        if lib_name not in memory["libs"]:
            self.console.print(f"Library {lib_name} is not in the list")
            return False
        
        del memory["libs"][lib_name]
        self._save_memory(memory)
        self.console.print(f"Removed library: {lib_name}")
        return True
    
    def set_proxy(self, proxy_url: Optional[str] = None) -> str:
        """
        Set or get proxy URL
        
        Args:
            proxy_url: New proxy URL, None to get current proxy
            
        Returns:
            Current proxy URL
        """
        memory = self._load_memory()
        
        if proxy_url is None:
            current_proxy = memory.get("lib-proxy", "No proxy set")
            self.console.print(f"Current proxy: {current_proxy}")
            return current_proxy
        
        memory["lib-proxy"] = proxy_url
        self._save_memory(memory)
        self.console.print(f"Set proxy to: {proxy_url}")
        return proxy_url
    
    def refresh_repository(self) -> bool:
        """
        Refresh the repository by pulling latest changes
        
        Returns:
            True if successful, False otherwise
        """
        if not os.path.exists(self.llm_friendly_packages_dir):
            self.console.print(
                "llm_friendly_packages repository does not exist. "
                "Please run add_library() first to clone it."
            )
            return False
        
        try:
            repo = git.Repo(self.llm_friendly_packages_dir)
            origin = repo.remotes.origin
            
            # Update remote URL if proxy is set
            memory = self._load_memory()
            proxy_url = memory.get("lib-proxy")
            current_url = origin.url
            
            if proxy_url and proxy_url != current_url:
                origin.set_url(proxy_url)
                self.console.print(f"Updated remote URL to: {proxy_url}")
            
            origin.pull()
            self.console.print("Successfully updated llm_friendly_packages repository")
            return True
            
        except git.exc.GitCommandError as e:
            self.console.print(f"Error updating repository: {e}")
            return False
    
    def get_library_docs_paths(self, package_name: str) -> List[str]:
        """
        Get documentation file paths for a specific package
        
        Args:
            package_name: Package name
            
        Returns:
            List of markdown file paths
        """
        return self.get_docs(package_name, return_paths=True)
    
    def display_added_libraries(self) -> None:
        """Display added libraries in a table"""
        libs = self.list_added_libraries()
        
        if not libs:
            self.console.print("No libraries added yet")
            return
        
        table = Table(title="Added Libraries")
        table.add_column("Library Name", style="cyan")
        
        for lib_name in libs:
            table.add_row(lib_name)
        
        self.console.print(table)
    
    def display_all_libraries(self) -> None:
        """Display all available libraries in a table"""
        if not os.path.exists(self.llm_friendly_packages_dir):
            self.console.print(
                "llm_friendly_packages repository does not exist. "
                "Please call add_library() first to clone it."
            )
            return
        
        available_libs = self.list_all_available_libraries()
        
        if not available_libs:
            self.console.print("No available libraries found in the repository.")
            return
        
        table = Table(title="Available Libraries")
        table.add_column("Domain", style="blue")
        table.add_column("Username", style="green")
        table.add_column("Library Name", style="cyan")
        table.add_column("Full Path", style="magenta")
        table.add_column("Status", style="yellow")
        
        for lib in available_libs:
            status = "[green]Added[/green]" if lib.is_added else "[white]Not Added[/white]"
            table.add_row(
                lib.domain,
                lib.username,
                lib.lib_name,
                lib.full_path,
                status
            )
        
        self.console.print(table)
    
    def display_library_docs(self, package_name: str) -> None:
        """Display documentation paths for a package in a table"""
        docs = self.get_library_docs_paths(package_name)
        
        if not docs:
            self.console.print(f"No markdown files found for package: {package_name}")
            return
        
        table = Table(title=f"Markdown Files for {package_name}")
        table.add_column("File Path", style="cyan")
        
        for doc in docs:
            table.add_row(doc)
        
        self.console.print(table) 