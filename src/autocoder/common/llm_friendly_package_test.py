"""
Test script for LLMFriendlyPackageManager

This script demonstrates the usage of the new LLMFriendlyPackageManager class.
"""

import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from autocoder.common.llm_friendly_package import LLMFriendlyPackageManager

def test_llm_friendly_package_manager():
    """Test the LLMFriendlyPackageManager functionality"""
    
    # Initialize the manager
    manager = LLMFriendlyPackageManager()
    
    print("=== Testing LLMFriendlyPackageManager ===\n")
    
    # Test 1: Display added libraries (should be empty initially)
    print("1. Testing display_added_libraries():")
    manager.display_added_libraries()
    print()
    
    # Test 2: List added libraries programmatically
    print("2. Testing list_added_libraries():")
    added_libs = manager.list_added_libraries()
    print(f"Added libraries: {added_libs}")
    print()
    
    # Test 3: Show current proxy
    print("3. Testing set_proxy() to get current proxy:")
    current_proxy = manager.set_proxy()
    print(f"Current proxy: {current_proxy}")
    print()
    
    # Test 4: Try to get docs (should be empty if no libraries added)
    print("4. Testing get_docs():")
    docs = manager.get_docs(return_paths=True)
    print(f"Number of documentation files found: {len(docs)}")
    if docs:
        print("First few docs:")
        for i, doc in enumerate(docs[:3]):
            print(f"  - {doc}")
    print()
    
    # Test 5: Display all available libraries (may require repository)
    print("5. Testing display_all_libraries():")
    try:
        manager.display_all_libraries()
    except Exception as e:
        print(f"Could not display all libraries: {e}")
    print()
    
    print("=== Test completed ===")

if __name__ == "__main__":
    test_llm_friendly_package_manager() 