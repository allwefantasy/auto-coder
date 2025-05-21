import unittest
from unittest.mock import MagicMock, patch
from autocoder.common.v2.agent.agentic_edit_types import ExecuteCommandTool
from autocoder.common import AutoCoderArgs
from autocoder.common.v2.agent.agentic_edit_tools.\
    execute_command_tool_resolver import ExecuteCommandToolResolver


class TestExecuteCommandToolResolver(unittest.TestCase):
    def setUp(self):
        self.args = AutoCoderArgs()
        # 设置token限制
        self.args.context_prune_safe_zone_tokens = 1000
        self.tool = ExecuteCommandTool(
            command="echo test", 
            requires_approval=False
        )
        self.agent = MagicMock()
        
    def test_execute_command_with_small_output(self):
        """测试小输出(不超过token限制)的情况"""
        resolver = cmd_resolver.ExecuteCommandToolResolver(
            self.agent, self.tool, self.args)
        
        with patch('autocoder.common.run_cmd_subprocess') as mock_run_cmd:
            mock_run_cmd.return_value = (0, "small output")
            result = resolver.resolve()
            
        self.assertTrue(result.success)
        self.assertEqual(result.content, "small output")
        
    def test_execute_command_with_large_output(self):
        """测试大输出(超过token限制)的情况"""
        # 生成一个大输出(超过1000 tokens)
        large_output = "large output " * 500
        
        resolver = ExecuteCommandToolResolver(self.agent, self.tool, self.args)
        
        with patch('autocoder.common.run_cmd_subprocess') as mock_run_cmd:
            mock_run_cmd.return_value = (0, large_output)
            result = resolver.resolve()
            
        self.assertTrue(result.success)
        # 验证输出被裁剪(长度小于原始输出)
        self.assertLess(len(result.content), len(large_output))
        
    def test_execute_command_token_counting(self):
        """测试token统计功能"""
        resolver = ExecuteCommandToolResolver(self.agent, self.tool, self.args)
        
        with patch('autocoder.common.run_cmd_subprocess') as mock_run_cmd:
            mock_run_cmd.return_value = (0, "test output")
            with patch('autocoder.rag.token_counter.count_tokens') as mock_count:
                mock_count.return_value = 42
                resolver.resolve()
                
        # 验证token统计被调用
        mock_count.assert_called_once_with("test output")
        
    def test_execute_command_with_error(self):
        """测试命令执行失败的情况"""
        resolver = ExecuteCommandToolResolver(self.agent, self.tool, self.args)
        
        with patch('autocoder.common.run_cmd_subprocess') as mock_run_cmd:
            mock_run_cmd.return_value = (1, "error output")
            result = resolver.resolve()
            
        self.assertFalse(result.success)
        self.assertIn("Command failed", result.message)

if __name__ == '__main__':
    unittest.main()
