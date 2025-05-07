
import pytest
import os
import shutil
import json
from unittest.mock import MagicMock, patch

from autocoder.common import AutoCoderArgs
from autocoder.common.v2.agent.agentic_edit_types import WriteToFileTool, ToolResult
from autocoder.common.v2.agent.agentic_edit_tools.write_to_file_tool_resolver import WriteToFileToolResolver
from autocoder.auto_coder_runner import load_tokenizer as load_tokenizer_global
from autocoder.utils.llms import get_single_llm
from autocoder.common.file_monitor.monitor import get_file_monitor, FileMonitor
from autocoder.common.rulefiles.autocoderrules_utils import get_rules, reset_rules_manager
from loguru import logger

# Helper to create a temporary test directory
@pytest.fixture(scope="function")
def temp_test_dir(tmp_path_factory):
    temp_dir = tmp_path_factory.mktemp("test_write_to_file_resolver_")
    logger.info(f"Created temp dir for test: {temp_dir}")
    # Create a dummy .autocoderignore to avoid issues with default ignore patterns loading
    # from unexpected places if the test is run from a different CWD.
    with open(os.path.join(temp_dir, ".autocoderignore"), "w") as f:
        f.write("# Dummy ignore file for tests\n")
    yield temp_dir
    logger.info(f"Cleaning up temp dir: {temp_dir}")
    # shutil.rmtree(temp_dir) # tmp_path_factory handles cleanup

@pytest.fixture(scope="function")
def setup_file_monitor_and_rules(temp_test_dir):
    """Initializes FileMonitor and RulesManager for the test session."""
    # Resetting instances to ensure test isolation
    FileMonitor.reset_instance()
    reset_rules_manager()

    monitor = get_file_monitor(str(temp_test_dir))
    if not monitor.is_running():
        monitor.start()
    logger.info(f"File monitor initialized with root: {monitor.root_dir}")

    rules = get_rules(str(temp_test_dir))
    logger.info(f"Rules loaded for dir: {temp_test_dir}, count: {len(rules)}")
    return str(temp_test_dir)


@pytest.fixture(scope="function")
def load_tokenizer_fixture(setup_file_monitor_and_rules):
    """Loads the tokenizer."""
    try:
        load_tokenizer_global()
        logger.info("Tokenizer loaded successfully.")
    except Exception as e:
        logger.error(f"Failed to load tokenizer: {e}")
        # Depending on test requirements, you might want to raise an error or skip tests
        pytest.skip(f"Skipping tests due to tokenizer loading failure: {e}")


@pytest.fixture(scope="function")
def test_args(temp_test_dir, setup_file_monitor_and_rules, load_tokenizer_fixture):
    """Provides default AutoCoderArgs for tests."""
    args = AutoCoderArgs(
        source_dir=str(temp_test_dir),
        enable_auto_fix_lint=False, # Default to no linting for basic tests
        # Potentially mock other args if needed by resolver or its dependencies
    )
    return args

@pytest.fixture
def mock_agent_no_shadow(test_args):
    """Mocks an AgenticEdit instance that does not provide shadow capabilities."""
    agent = MagicMock()
    agent.shadow_manager = None
    agent.shadow_linter = None
    agent.args = test_args
    agent.record_file_change = MagicMock()
    return agent

@pytest.fixture
def mock_agent_with_shadow(test_args, temp_test_dir):
    """Mocks an AgenticEdit instance with shadow capabilities."""
    from autocoder.shadows.shadow_manager import ShadowManager
    from autocoder.linters.shadow_linter import ShadowLinter

    # Ensure the shadow base directory exists within the temp_test_dir for isolation
    shadow_base_dir = os.path.join(temp_test_dir, ".auto-coder", "shadows")
    os.makedirs(shadow_base_dir, exist_ok=True)
    
    # Patch ShadowManager's default shadow_base to use our temp one
    with patch('autocoder.shadows.shadow_manager.ShadowManager.DEFAULT_SHADOW_BASE_DIR', new=shadow_base_dir):
        shadow_manager = ShadowManager(source_dir=str(temp_test_dir), event_file_id="test_event")
    
    shadow_linter = ShadowLinter(shadow_manager=shadow_manager, verbose=False)
    
    agent = MagicMock()
    agent.shadow_manager = shadow_manager
    agent.shadow_linter = shadow_linter
    agent.args = test_args
    agent.record_file_change = MagicMock()
    return agent


def test_create_new_file(test_args, temp_test_dir, mock_agent_no_shadow):
    logger.info(f"Running test_create_new_file in {temp_test_dir}")
    file_path = "new_file.txt"
    content = "This is a new file."
    tool = WriteToFileTool(path=file_path, content=content)
    
    resolver = WriteToFileToolResolver(agent=mock_agent_no_shadow, tool=tool, args=test_args)
    result = resolver.resolve()

    assert result.success is True
    assert "成功写入文件" in result.message or "Successfully wrote file" in result.message
    
    expected_file_abs_path = os.path.join(temp_test_dir, file_path)
    assert os.path.exists(expected_file_abs_path)
    with open(expected_file_abs_path, "r", encoding="utf-8") as f:
        assert f.read() == content
    mock_agent_no_shadow.record_file_change.assert_called_once_with(file_path, "added", content=content, diffs=None)


def test_overwrite_existing_file(test_args, temp_test_dir, mock_agent_no_shadow):
    logger.info(f"Running test_overwrite_existing_file in {temp_test_dir}")
    file_path = "existing_file.txt"
    initial_content = "Initial content."
    new_content = "This is the new content."

    abs_file_path = os.path.join(temp_test_dir, file_path)
    with open(abs_file_path, "w", encoding="utf-8") as f:
        f.write(initial_content)

    tool = WriteToFileTool(path=file_path, content=new_content)
    resolver = WriteToFileToolResolver(agent=mock_agent_no_shadow, tool=tool, args=test_args)
    result = resolver.resolve()

    assert result.success is True
    assert os.path.exists(abs_file_path)
    with open(abs_file_path, "r", encoding="utf-f8") as f:
        assert f.read() == new_content
    mock_agent_no_shadow.record_file_change.assert_called_once_with(file_path, "modified", content=new_content, diffs=None)


def test_create_file_in_new_directory(test_args, temp_test_dir, mock_agent_no_shadow):
    logger.info(f"Running test_create_file_in_new_directory in {temp_test_dir}")
    file_path = "new_dir/another_new_dir/file.txt"
    content = "Content in a nested directory."
    
    tool = WriteToFileTool(path=file_path, content=content)
    resolver = WriteToFileToolResolver(agent=mock_agent_no_shadow, tool=tool, args=test_args)
    result = resolver.resolve()

    assert result.success is True
    expected_file_abs_path = os.path.join(temp_test_dir, file_path)
    assert os.path.exists(expected_file_abs_path)
    with open(expected_file_abs_path, "r", encoding="utf-8") as f:
        assert f.read() == content
    mock_agent_no_shadow.record_file_change.assert_called_once_with(file_path, "added", content=content, diffs=None)

def test_path_outside_project_root_fails(test_args, temp_test_dir, mock_agent_no_shadow):
    logger.info(f"Running test_path_outside_project_root_fails in {temp_test_dir}")
    # Construct a path that tries to go outside the source_dir
    # Note: The resolver's check is os.path.abspath(target_path).startswith(os.path.abspath(source_dir))
    # So, a direct "../" might be normalized. We need a path that, when absolutized,
    # is still outside an absolutized source_dir. This is tricky if source_dir is already root-like.
    # For this test, we'll assume source_dir is not the filesystem root.
    
    # A more robust way is to try to write to a known safe, but distinct, temporary directory
    another_temp_dir = temp_test_dir.parent / "another_temp_dir_for_outside_test"
    another_temp_dir.mkdir(exist_ok=True)
    
    # This relative path, if source_dir is temp_test_dir, would resolve outside.
    # However, the resolver joins it with source_dir first.
    # file_path = "../outside_file.txt" # This will be joined with source_dir
    
    # Let's try an absolute path that is outside temp_test_dir
    outside_abs_path = os.path.join(another_temp_dir, "outside_file.txt")
    
    # The tool path is relative to source_dir. So, to make it point outside,
    # we need to construct a relative path that goes "up" from source_dir.
    # This requires knowing the relative position of temp_test_dir.
    # A simpler test for the security check:
    # Give an absolute path to the tool that is outside test_args.source_dir.
    # The resolver logic is:
    # abs_file_path = os.path.abspath(os.path.join(source_dir, file_path_from_tool))
    # So, if file_path_from_tool is already absolute, os.path.join might behave unexpectedly on Windows.
    # On POSIX, if file_path_from_tool is absolute, os.path.join returns file_path_from_tool.
    
    if os.name == 'posix':
        file_path_for_tool = outside_abs_path
    else: # Windows, os.path.join with absolute second path is tricky
        # For windows, this test might need adjustment or rely on the fact that
        # the file_path parameter to the tool is *expected* to be relative.
        # Providing an absolute path might be an invalid use case for the tool itself.
        # The resolver's security check should still catch it if os.path.join(source_dir, abs_path)
        # results in abs_path and abs_path is outside source_dir.
        file_path_for_tool = outside_abs_path

    content = "Attempting to write outside."
    tool = WriteToFileTool(path=str(file_path_for_tool), content=content)
    
    resolver = WriteToFileToolResolver(agent=mock_agent_no_shadow, tool=tool, args=test_args)
    result = resolver.resolve()

    assert result.success is False
    assert "访问被拒绝" in result.message or "Access denied" in result.message
    assert not os.path.exists(outside_abs_path)
    
    # shutil.rmtree(another_temp_dir) # Clean up the other temp dir if created by this test

def test_linting_not_called_if_disabled(test_args, temp_test_dir, mock_agent_no_shadow):
    logger.info(f"Running test_linting_not_called_if_disabled in {temp_test_dir}")
    test_args.enable_auto_fix_lint = False # Explicitly disable
    
    file_path = "no_lint_file.py"
    content = "print('hello')"
    tool = WriteToFileTool(path=file_path, content=content)
    
    # Mock the linter parts if they were to be called
    if mock_agent_no_shadow and hasattr(mock_agent_no_shadow, 'shadow_linter') and mock_agent_no_shadow.shadow_linter:
        mock_agent_no_shadow.shadow_linter.lint_shadow_file = MagicMock(return_value=None) # Should not be called

    resolver = WriteToFileToolResolver(agent=mock_agent_no_shadow, tool=tool, args=test_args)
    result = resolver.resolve()

    assert result.success is True
    if mock_agent_no_shadow and hasattr(mock_agent_no_shadow, 'shadow_linter') and mock_agent_no_shadow.shadow_linter:
        mock_agent_no_shadow.shadow_linter.lint_shadow_file.assert_not_called()
    
    # Check if "代码质量检查已禁用" or "Linting is disabled" is in message
    assert "代码质量检查已禁用" in result.message or "Linting is disabled" in result.message or "成功写入文件" in result.message


def test_linting_called_if_enabled(test_args, temp_test_dir, mock_agent_with_shadow):
    logger.info(f"Running test_linting_called_if_enabled in {temp_test_dir}")
    test_args.enable_auto_fix_lint = True # Explicitly enable
    
    file_path = "lint_file.py"
    content = "print('hello world')" # Valid python
    tool = WriteToFileTool(path=file_path, content=content)
    
    # Mock the lint_shadow_file method on the shadow_linter provided by mock_agent_with_shadow
    mock_lint_result = MagicMock()
    mock_lint_result.issues = [] # No issues
    mock_agent_with_shadow.shadow_linter.lint_shadow_file = MagicMock(return_value=mock_lint_result)

    resolver = WriteToFileToolResolver(agent=mock_agent_with_shadow, tool=tool, args=test_args)
    result = resolver.resolve()

    assert result.success is True
    mock_agent_with_shadow.shadow_linter.lint_shadow_file.assert_called_once()
    # The actual path passed to lint_shadow_file will be the shadow path
    shadow_path = mock_agent_with_shadow.shadow_manager.to_shadow_path(os.path.join(temp_test_dir, file_path))
    mock_agent_with_shadow.shadow_linter.lint_shadow_file.assert_called_with(shadow_path)
    assert "代码质量检查通过" in result.message or "Linting passed" in result.message


def test_create_file_with_shadow_manager(test_args, temp_test_dir, mock_agent_with_shadow):
    logger.info(f"Running test_create_file_with_shadow_manager in {temp_test_dir}")
    file_path = "shadowed_file.txt"
    content = "This file should be in the shadow realm."
    tool = WriteToFileTool(path=file_path, content=content)

    resolver = WriteToFileToolResolver(agent=mock_agent_with_shadow, tool=tool, args=test_args)
    result = resolver.resolve()

    assert result.success is True
    
    real_file_abs_path = os.path.join(temp_test_dir, file_path)
    shadow_file_abs_path = mock_agent_with_shadow.shadow_manager.to_shadow_path(real_file_abs_path)

    assert not os.path.exists(real_file_abs_path) # Real file should not be created directly
    assert os.path.exists(shadow_file_abs_path) # Shadow file should exist
    with open(shadow_file_abs_path, "r", encoding="utf-8") as f:
        assert f.read() == content
    
    # Agent's record_file_change should still be called with the original relative path
    mock_agent_with_shadow.record_file_change.assert_called_once_with(file_path, "added", content=content, diffs=None)
    
    # Clean up shadows for this test if needed, though mock_agent_with_shadow might do it
    # mock_agent_with_shadow.shadow_manager.clean_shadows()


def test_linting_error_message_propagation(test_args, temp_test_dir, mock_agent_with_shadow):
    logger.info(f"Running test_linting_error_message_propagation in {temp_test_dir}")
    test_args.enable_auto_fix_lint = True
    
    file_path = "lint_error_file.py"
    content = "print 'hello'" # Python 2 print, will cause lint error in Python 3 env with basic pyflakes
    tool = WriteToFileTool(path=file_path, content=content)

    mock_issue = MagicMock()
    mock_issue.severity = MagicMock() # Simulate IssueSeverity enum if needed by _format_lint_issues
    mock_issue.severity.value = "ERROR" # Assuming _format_lint_issues checks for severity.value
    mock_issue.position.line = 1
    mock_issue.position.column = 0
    mock_issue.message = "SyntaxError: Missing parentheses in call to 'print'"
    mock_issue.code = "E999"

    mock_lint_result = MagicMock()
    mock_lint_result.issues = [mock_issue]
    mock_lint_result.file_results = {
        mock_agent_with_shadow.shadow_manager.to_shadow_path(os.path.join(temp_test_dir, file_path)): mock_lint_result
    }


    mock_agent_with_shadow.shadow_linter.lint_shadow_file = MagicMock(return_value=mock_lint_result)
    # Mock _format_lint_issues if it's complex or to control its output precisely
    # For now, assume it works as expected based on WriteToFileToolResolver's internal call
    
    resolver = WriteToFileToolResolver(agent=mock_agent_with_shadow, tool=tool, args=test_args)
    
    # Temporarily patch _format_lint_issues within the resolver instance for this test
    # to ensure consistent output for assertion.
    formatted_issue_text = f"文件: {mock_agent_with_shadow.shadow_manager.to_shadow_path(os.path.join(temp_test_dir, file_path))}\n  - [错误] 第1行, 第0列: SyntaxError: Missing parentheses in call to 'print' (规则: E999)\n"
    with patch.object(resolver, '_format_lint_issues', return_value=formatted_issue_text) as mock_format:
        result = resolver.resolve()

    assert result.success is True # Write itself is successful
    mock_format.assert_called_once_with(mock_lint_result)
    assert "代码质量检查发现 1 个问题" in result.message or "Linting found 1 issue(s)" in result.message
    assert "SyntaxError: Missing parentheses in call to 'print'" in result.message

