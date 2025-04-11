import pytest
import os
import tempfile
import shutil
from unittest.mock import patch, MagicMock

from autocoder.common.v2.agent.agentic_edit_tools.search_files_tool_resolver import SearchFilesToolResolver
from autocoder.common.v2.agent.agentic_edit_types import SearchFilesTool, ToolResult
from autocoder.common import AutoCoderArgs

# Helper function to create a directory structure with files for testing
def create_test_files(base_dir, structure):
    """
    Creates a directory structure with files based on the provided dictionary.
    Keys are filenames (relative to base_dir), values are file contents.
    Directories are created automatically.
    """
    for path, content in structure.items():
        full_path = os.path.join(base_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content)

@pytest.fixture
def search_tool_resolver(temp_search_dir):
    """Fixture to provide an instance of SearchFilesToolResolver."""
    # Create AutoCoderArgs with the temp directory as source_dir to allow the security check to pass
    args = AutoCoderArgs()
    args.source_dir = temp_search_dir  # Set the source_dir to our temp directory
    return SearchFilesToolResolver(None, SearchFilesTool(path="", regex=""), args)

@pytest.fixture(scope="function")
def temp_search_dir():
    """Fixture to create a temporary directory with test files for searching."""
    temp_dir = tempfile.mkdtemp()
    test_structure = {
        "file1.txt": "Hello world\nThis is a test file.",
        "subdir/file2.py": "import sys\n\ndef main():\n    print('Python script')\n",
        "subdir/another.txt": "Another text file with world.",
        ".hiddenfile": "This should be ignored by default",
        "no_match.md": "Markdown file."
    }
    create_test_files(temp_dir, test_structure)
    yield temp_dir # Provide the path to the test function
    shutil.rmtree(temp_dir) # Cleanup after test

# --- Test Cases ---

def test_resolve_finds_matches(search_tool_resolver, temp_search_dir):
    """Test that resolve finds matches correctly."""
    # Set up the tool with the pattern we want to search for
    tool = SearchFilesTool(
        path="",  # Use empty path to search in the source_dir itself
        regex="world",
        file_pattern="*.txt"
    )
    search_tool_resolver.tool = tool

    # Call the resolve method directly
    response = search_tool_resolver.resolve()

    # Check the response
    assert isinstance(response, ToolResult)
    assert response.success
    assert "Search completed. Found 2 matches" in response.message
    
    # Check that the correct files were found
    assert len(response.content) == 2
    paths = [result["path"] for result in response.content]
    assert any("file1.txt" in path for path in paths)
    assert any("another.txt" in path for path in paths)
    
    # Check that the match lines contain our search pattern
    for result in response.content:
        assert "world" in result["match_line"]

def test_resolve_no_matches(search_tool_resolver, temp_search_dir):
    """Test that resolve handles no matches correctly."""
    tool = SearchFilesTool(
        path="",  # Use empty path to search in the source_dir itself
        regex="nonexistent_pattern",
        file_pattern="*"
    )
    search_tool_resolver.tool = tool

    response = search_tool_resolver.resolve()

    assert isinstance(response, ToolResult)
    assert response.success  # Still success, just no results
    assert "Search completed. Found 0 matches" in response.message
    assert len(response.content) == 0

def test_resolve_file_pattern(search_tool_resolver, temp_search_dir):
    """Test that the file_pattern is correctly applied."""
    # Test .txt pattern
    tool_txt = SearchFilesTool(
        path="",  # Use empty path to search in the source_dir itself
        regex="world",
        file_pattern="*.txt"  # Only search .txt files
    )
    search_tool_resolver.tool = tool_txt
    
    response_txt = search_tool_resolver.resolve()
    
    assert isinstance(response_txt, ToolResult)
    assert response_txt.success
    assert "Search completed. Found 2 matches" in response_txt.message
    # Ensure only .txt files were matched
    for result in response_txt.content:
        assert result["path"].endswith(".txt")
    
    # Test .py pattern
    tool_py = SearchFilesTool(
        path="",  # Use empty path to search in the source_dir itself
        regex="print",
        file_pattern="*.py"  # Only search .py files
    )
    search_tool_resolver.tool = tool_py
    
    response_py = search_tool_resolver.resolve()
    
    assert isinstance(response_py, ToolResult)
    assert response_py.success
    assert "Search completed. Found 1 matches" in response_py.message
    # Ensure only .py files were matched
    for result in response_py.content:
        assert result["path"].endswith(".py")

def test_invalid_regex(search_tool_resolver, temp_search_dir):
    """Test that an invalid regex pattern is properly handled."""
    tool = SearchFilesTool(
        path="",  # Use empty path to search in the source_dir itself
        regex="[invalid regex",  # Invalid regex pattern
        file_pattern="*"
    )
    search_tool_resolver.tool = tool

    response = search_tool_resolver.resolve()

    assert isinstance(response, ToolResult)
    assert not response.success
    assert "Invalid regex pattern" in response.message

def test_nonexistent_path(search_tool_resolver, temp_search_dir):
    """Test that a nonexistent path is properly handled."""
    # Create a path that we know doesn't exist under temp_search_dir
    nonexistent_path = "nonexistent_subdirectory"
    
    tool = SearchFilesTool(
        path=nonexistent_path,  # This path doesn't exist in our temp directory
        regex="pattern",
        file_pattern="*"
    )
    search_tool_resolver.tool = tool

    response = search_tool_resolver.resolve()

    assert isinstance(response, ToolResult)
    assert not response.success
    assert "Error: Search path not found" in response.message

# Add more tests as needed

