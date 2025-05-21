import pytest
from unittest.mock import MagicMock, patch
from autocoder.common.v2.agent.agentic_edit_types import ExecuteCommandTool, ToolResult
from autocoder.common.v2.agent.agentic_edit_tools.execute_command_tool_resolver import ExecuteCommandToolResolver
from autocoder.common import AutoCoderArgs

class TestExecuteCommandToolResolver:
    @pytest.fixture
    def mock_args(self):
        args = AutoCoderArgs()
        args.source_dir = "."
        args.context_prune_safe_zone_tokens = 1000  # 设置裁剪阈值
        args.context_prune_strategy = "smart"  # 设置裁剪策略
        return args

    @pytest.fixture
    def mock_agent(self):
        agent = MagicMock()
        agent.context_prune_llm = MagicMock()
        return agent

    def test_execute_command_with_small_output(self, mock_args, mock_agent):
        """测试小输出不触发裁剪"""
        tool = ExecuteCommandTool(command="echo hello", requires_approval=False)
        resolver = ExecuteCommandToolResolver(mock_agent, tool, mock_args)

        with patch("autocoder.common.run_cmd.run_cmd_subprocess") as mock_run:
            mock_run.return_value = (0, "hello")
            result = resolver.resolve()

        assert result.success is True
        assert result.content == "hello"  # 内容未裁剪

    def test_execute_command_with_large_output(self, mock_args, mock_agent):
        """测试大输出触发裁剪"""
        # 生成超过1000 tokens的大文本
        large_text = "This is a large output. " * 200
        
        tool = ExecuteCommandTool(command="echo large_text", requires_approval=False)
        resolver = ExecuteCommandToolResolver(mock_agent, tool, mock_args)

        with patch("autocoder.common.run_cmd.run_cmd_subprocess") as mock_run:
            mock_run.return_value = (0, large_text)
            result = resolver.resolve()

        assert result.success is True
        assert len(result.content) < len(large_text)  # 内容被裁剪
        assert "This is a large output" in result.content  # 保留部分内容

    def test_execute_command_with_error(self, mock_args, mock_agent):
        """测试命令执行错误"""
        tool = ExecuteCommandTool(command="invalid_command", requires_approval=False)
        resolver = ExecuteCommandToolResolver(mock_agent, tool, mock_args)

        with patch("autocoder.common.run_cmd.run_cmd_subprocess") as mock_run:
            mock_run.side_effect = FileNotFoundError("Command not found")
            result = resolver.resolve()

        assert result.success is False
        assert "Command not found" in result.message

    def test_execute_command_with_unsafe_characters(self, mock_args, mock_agent):
        """测试不安全命令"""
        tool = ExecuteCommandTool(command="rm -rf /", requires_approval=False)
        resolver = ExecuteCommandToolResolver(mock_agent, tool, mock_args)

        result = resolver.resolve()
        assert result.success is False
        assert "unsafe" in result.message.lower()
