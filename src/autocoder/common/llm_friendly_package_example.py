"""
LLMFriendlyPackageManager Usage Examples

This file demonstrates various ways to use the LLMFriendlyPackageManager class
for managing LLM friendly packages.
"""

from autocoder.common.llm_friendly_package import LLMFriendlyPackageManager

def example_basic_usage():
    """Basic usage example"""
    print("=== Basic Usage Example ===")
    
    # Initialize the manager
    manager = LLMFriendlyPackageManager()
    
    # List current added libraries
    added_libs = manager.list_added_libraries()
    print(f"Currently added libraries: {added_libs}")
    
    # Display added libraries in a nice table
    manager.display_added_libraries()

def example_library_management():
    """Library management example"""
    print("\n=== Library Management Example ===")
    
    manager = LLMFriendlyPackageManager()
    
    # Add a library (this will clone the repository if needed)
    print("Adding a library...")
    success = manager.add_library("example-lib")
    if success:
        print("Library added successfully!")
    
    # List all available libraries
    print("\nAll available libraries:")
    manager.display_all_libraries()
    
    # Remove a library
    print("\nRemoving the library...")
    removed = manager.remove_library("example-lib")
    if removed:
        print("Library removed successfully!")

def example_documentation_access():
    """Documentation access example"""
    print("\n=== Documentation Access Example ===")
    
    manager = LLMFriendlyPackageManager()
    
    # Get documentation content for all packages
    docs_content = manager.get_docs()
    print(f"Total documentation content items: {len(docs_content)}")
    
    # Get documentation file paths for all packages
    docs_paths = manager.get_docs(return_paths=True)
    print(f"Total documentation files: {len(docs_paths)}")
    
    # Get documentation for a specific package
    specific_docs = manager.get_docs(package_name="some-package", return_paths=True)
    print(f"Documentation files for 'some-package': {len(specific_docs)}")
    
    # Display documentation paths for a specific package
    manager.display_library_docs("some-package")

def example_repository_management():
    """Repository management example"""
    print("\n=== Repository Management Example ===")
    
    manager = LLMFriendlyPackageManager()
    
    # Get current proxy setting
    current_proxy = manager.set_proxy()
    print(f"Current proxy: {current_proxy}")
    
    # Set a new proxy (optional)
    # manager.set_proxy("https://gitee.com/your-mirror/llm_friendly_packages")
    
    # Refresh the repository to get latest changes
    print("Refreshing repository...")
    success = manager.refresh_repository()
    if success:
        print("Repository refreshed successfully!")

def example_data_access():
    """Data access example"""
    print("\n=== Data Access Example ===")
    
    manager = LLMFriendlyPackageManager()
    
    # Get all available libraries as structured data
    available_libs = manager.list_all_available_libraries()
    print(f"Total available libraries: {len(available_libs)}")
    
    # Process the library information
    for lib in available_libs[:3]:  # Show first 3
        print(f"Domain: {lib.domain}, "
              f"Username: {lib.username}, "
              f"Library: {lib.lib_name}, "
              f"Added: {lib.is_added}")

def example_custom_configuration():
    """Custom configuration example"""
    print("\n=== Custom Configuration Example ===")
    
    # Initialize with custom directories (using existing project directory)
    import tempfile
    import os
    
    # Create a temporary directory for demonstration
    with tempfile.TemporaryDirectory() as temp_dir:
        custom_project_root = temp_dir
        custom_persist_dir = os.path.join(temp_dir, "custom_persist")
        
        manager = LLMFriendlyPackageManager(
            project_root=custom_project_root,
            base_persist_dir=custom_persist_dir
        )
        
        print("Manager initialized with custom configuration")
        print(f"Project root: {custom_project_root}")
        print(f"Persistence directory: {custom_persist_dir}")
        
        # Use the manager with custom configuration
        added_libs = manager.list_added_libraries()
        print(f"Added libraries with custom config: {added_libs}")

if __name__ == "__main__":
    # Run all examples
    example_basic_usage()
    example_library_management()
    example_documentation_access()
    example_repository_management()
    example_data_access()
    example_custom_configuration()
    
    print("\n=== All examples completed ===") 