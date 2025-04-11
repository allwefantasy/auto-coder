
import pytest
import subprocess
from unittest.mock import patch, MagicMock
import os
import tempfile
import shutil

from autocoder.common.v2.agent.agentic_edit_tools.search_files_tool_resolver import SearchFilesToolResolver, SearchFilesToolInput
from autocoder.common.v2.agent.tool_response import ToolResponse

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
def search_tool_resolver():
    """Fixture to provide an instance of SearchFilesToolResolver."""
    return SearchFilesToolResolver(None) # Pass None for agent_id or a mock if needed

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
    tool_input = SearchFilesToolInput(
        path=temp_search_dir,
        regex="world",
        file_pattern="*.txt"
    )

    # We mock subprocess.run to avoid dependency on external 'rg' and control output
    mock_process = MagicMock()
    mock_process.returncode = 0
    # Simulate rg output format: path:lineno:content
    mock_process.stdout = f"{os.path.join(temp_search_dir, 'file1.txt')}:1:Hello world\n{os.path.join(temp_search_dir, 'subdir/another.txt')}:1:Another text file with world.\n".encode('utf-8')
    mock_process.stderr = b""

    with patch('subprocess.run', return_value=mock_process) as mock_run:
        response = search_tool_resolver.resolve(tool_input=tool_input)

        # Check if subprocess.run was called with expected arguments (adjust rg path if needed)
        expected_cmd_part = ["rg", "--json", "--context=3", "--glob='*.txt'", "world", temp_search_dir]
        # Allow for variations in rg path
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[1:] == expected_cmd_part[1:] # Compare args after rg command itself
        assert called_cmd[4] == tool_input.regex # Check regex
        assert called_cmd[5] == tool_input.path # Check path

        assert isinstance(response, ToolResponse)
        assert response.is_success()
        assert "Found 2 matches" in response.response
        assert "file1.txt:1:Hello world" in response.response
        assert "subdir/another.txt:1:Another text file with world." in response.response

def test_resolve_no_matches(search_tool_resolver, temp_search_dir):
    """Test that resolve handles no matches correctly."""
    tool_input = SearchFilesToolInput(
        path=temp_search_dir,
        regex="nonexistent_pattern",
        file_pattern="*"
    )

    mock_process = MagicMock()
    mock_process.returncode = 0 # rg returns 0 even if no matches, but stdout is empty
    mock_process.stdout = b""
    mock_process.stderr = b""

    with patch('subprocess.run', return_value=mock_process) as mock_run:
        response = search_tool_resolver.resolve(tool_input=tool_input)

        expected_cmd_part = ["rg", "--json", "--context=3", "--glob='*'", "nonexistent_pattern", temp_search_dir]
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[1:] == expected_cmd_part[1:]

        assert isinstance(response, ToolResponse)
        assert response.is_success() # Still success, just no results
        assert "No matches found" in response.response

def test_resolve_rg_error(search_tool_resolver, temp_search_dir):
    """Test that resolve handles errors from the rg command."""
    tool_input = SearchFilesToolInput(
        path=temp_search_dir,
        regex="world",
        file_pattern="*.txt"
    )

    mock_process = MagicMock()
    mock_process.returncode = 1 # Simulate an error
    mock_process.stdout = b""
    mock_process.stderr = b"Simulated rg error message"

    with patch('subprocess.run', return_value=mock_process) as mock_run:
        response = search_tool_resolver.resolve(tool_input=tool_input)

        expected_cmd_part = ["rg", "--json", "--context=3", "--glob='*.txt'", "world", temp_search_dir]
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[1:] == expected_cmd_part[1:]

        assert isinstance(response, ToolResponse)
        assert not response.is_success()
        assert "Error executing search command" in response.response
        assert "Simulated rg error message" in response.response

def test_resolve_file_pattern(search_tool_resolver, temp_search_dir):
    """Test that the file_pattern is correctly applied."""
    tool_input_txt = SearchFilesToolInput(
        path=temp_search_dir,
        regex="world",
        file_pattern="*.txt" # Only search .txt files
    )
    tool_input_py = SearchFilesToolInput(
        path=temp_search_dir,
        regex="print",
        file_pattern="*.py" # Only search .py files
    )

    # Mock for .txt search
    mock_process_txt = MagicMock()
    mock_process_txt.returncode = 0
    mock_process_txt.stdout = f"{os.path.join(temp_search_dir, 'file1.txt')}:1:Hello world\n{os.path.join(temp_search_dir, 'subdir/another.txt')}:1:Another text file with world.\n".encode('utf-8')
    mock_process_txt.stderr = b""

    # Mock for .py search
    mock_process_py = MagicMock()
    mock_process_py.returncode = 0
    mock_process_py.stdout = f"{os.path.join(temp_search_dir, 'subdir/file2.py')}:4:    print('Python script')\n".encode('utf-8')
    mock_process_py.stderr = b""

    with patch('subprocess.run') as mock_run:
        # Test .txt pattern
        mock_run.return_value = mock_process_txt
        response_txt = search_tool_resolver.resolve(tool_input=tool_input_txt)
        called_cmd_txt = mock_run.call_args[0][0]
        assert "--glob='*.txt'" in called_cmd_txt
        assert isinstance(response_txt, ToolResponse)
        assert response_txt.is_success()
        assert "Found 2 matches" in response_txt.response
        assert "file1.txt" in response_txt.response
        assert "another.txt" in response_txt.response
        assert "file2.py" not in response_txt.response # Should not be found

        # Test .py pattern
        mock_run.return_value = mock_process_py
        response_py = search_tool_resolver.resolve(tool_input=tool_input_py)
        called_cmd_py = mock_run.call_args[0][0]
        assert "--glob='*.py'" in called_cmd_py
        assert isinstance(response_py, ToolResponse)
        assert response_py.is_success()
        assert "Found 1 matches" in response_py.response # Corrected expectation
        assert "file2.py" in response_py.response
        assert "file1.txt" not in response_py.response # Should not be found

# Add more tests as needed, e.g., for invalid regex, path not found etc.
# Note: Testing invalid regex might depend on how `rg` handles it.
# If `rg` errors out, test_resolve_rg_error covers it. If it just finds no matches,
# test_resolve_no_matches covers it.

