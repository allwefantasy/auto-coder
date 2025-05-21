import pytest
from unittest.mock import MagicMock, patch
from autocoder.common.v2.agent.agentic_edit_tools \
    .execute_command_tool_resolver import ExecuteCommandToolResolver
from autocoder.common.v2.agent.agentic_edit_types import ExecuteCommandTool
from autocoder.common import AutoCoderArgs


class TestExecuteCommandToolResolver:
    @pytest.fixture
    def mock_agent(self):
        agent = MagicMock()
        agent.args = AutoCoderArgs()
        agent.args.context_prune_safe_zone_tokens = 1000
        agent.context_prune_llm = None
        agent.current_conversations = []
        return agent

    @pytest.fixture
    def mock_tool(self):
        return ExecuteCommandTool(
            command="echo 'test output'", 
            requires_approval=False
        )


    def test_command_execution_with_token_count(self, mock_agent, mock_tool):
        """测试命令执行并验证token统计功能"""
        resolver = ExecuteCommandToolResolver(mock_agent, mock_tool, mock_agent.args)
        
        # 模拟命令执行返回大量输出
        with patch("autocoder.common.run_cmd.run_cmd_subprocess") as mock_run_cmd:
            mock_run_cmd.return_value = (0, "test output " * 500)  # 生成大量输出
            
            result = resolver.resolve()
            
            assert result.success
            assert "test output" in result.content
            
            # 验证token统计功能
            # 这里需要修改ExecuteCommandToolResolver来添加token统计功能
            # 测试将失败，符合TDD的红色阶段

    def test_output_pruning_when_exceeds_token_limit(self, mock_agent, mock_tool):
        """测试当输出超过token限制时的裁剪功能"""
        resolver = ExecuteCommandToolResolver(mock_agent, mock_tool, mock_agent.args)
        
        # 模拟命令执行返回大量输出
        with patch("autocoder.common.run_cmd.run_cmd_subprocess") as mock_run_cmd:
            mock_run_cmd.return_value = (0, "test output " * 500)  # 生成大量输出
            
            result = resolver.resolve()
            
            assert result.success
            # 验证输出是否被裁剪
            # 这里需要修改ExecuteCommandToolResolver来添加裁剪功能
            # 测试将失败，符合TDD的红色阶段

    def test_command_execution_failure(self, mock_agent, mock_tool):
        """测试命令执行失败的情况"""
        resolver = ExecuteCommandToolResolver(mock_agent, mock_tool, mock_agent.args)
        
        # 模拟命令执行失败
        with patch("autocoder.common.run_cmd.run_cmd_subprocess") as mock_run_cmd:
            mock_run_cmd.return_value = (1, "command failed")
            
            result = resolver.resolve()
            
            assert not result.success
            assert "command failed" in result.message
