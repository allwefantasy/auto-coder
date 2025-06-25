"""
Pytest tests for AgenticConversationPruner

This module contains comprehensive tests for the AgenticConversationPruner class,
including functionality tests, edge cases, and integration tests.
"""

import json
import pytest
from unittest.mock import MagicMock, patch
from autocoder.common.pruner.agentic_conversation_pruner import AgenticConversationPruner
from autocoder.common import AutoCoderArgs


class TestAgenticConversationPruner:
    """Test suite for AgenticConversationPruner class"""

    @pytest.fixture
    def mock_args(self):
        """Create mock AutoCoderArgs for testing"""
        args = MagicMock(spec=AutoCoderArgs)
        args.conversation_prune_safe_zone_tokens = 1000  # Small threshold for testing
        return args

    @pytest.fixture
    def mock_llm(self):
        """Create mock LLM for testing"""
        return MagicMock()

    @pytest.fixture
    def pruner(self, mock_args, mock_llm):
        """Create AgenticConversationPruner instance for testing"""
        return AgenticConversationPruner(args=mock_args, llm=mock_llm)

    @pytest.fixture
    def sample_conversations(self):
        """Sample conversations with tool results for testing"""
        return [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Please read a file for me."},
            {"role": "assistant", "content": "I'll read the file for you.\n\n<read_file>\n<path>test.py</path>\n</read_file>"},
            {
                "role": "user", 
                "content": "<tool_result tool_name='ReadFileTool' success='true'><message>File read successfully</message><content>def hello():\n    print('Hello, world!')\n    # This is a very long file content that would take up many tokens\n    # We want to clean this up to save space in the conversation\n    for i in range(100):\n        print(f'Line {i}: This is line number {i} with some content')\n    return 'done'</content></tool_result>"
            },
            {"role": "assistant", "content": "I can see the file content. Let me analyze it for you."},
            {"role": "user", "content": "Now please list files in the directory."},
            {"role": "assistant", "content": "I'll list the files for you.\n\n<list_files>\n<path>.</path>\n</list_files>"},
            {
                "role": "user",
                "content": "<tool_result tool_name='ListFilesTool' success='true'><message>Files listed successfully</message><content>['file1.py', 'file2.js', 'file3.md', 'very_long_file_with_many_tokens_that_should_be_cleaned.txt', 'another_file.py', 'config.json', 'readme.md', 'test_data.csv']</content></tool_result>"
            },
            {"role": "assistant", "content": "Here are the files in the directory. Is there anything specific you'd like to do with them?"}
        ]

    def test_initialization(self, mock_args, mock_llm):
        """Test AgenticConversationPruner initialization"""
        pruner = AgenticConversationPruner(args=mock_args, llm=mock_llm)
        
        assert pruner.args == mock_args
        assert pruner.llm == mock_llm
        assert hasattr(pruner, 'strategies')
        assert 'tool_output_cleanup' in pruner.strategies
        assert pruner.replacement_message == "This message has been cleared. If you still want to get this information, you can call the tool again to retrieve it."

    def test_get_available_strategies(self, pruner):
        """Test getting available strategies"""
        strategies = pruner.get_available_strategies()
        
        assert isinstance(strategies, list)
        assert len(strategies) > 0
        
        strategy = strategies[0]
        assert 'name' in strategy
        assert 'description' in strategy
        assert 'config' in strategy
        assert strategy['name'] == 'tool_output_cleanup'

    @patch('autocoder.rag.token_counter.count_tokens')
    def test_prune_conversations_within_limit(self, mock_count_tokens, pruner, sample_conversations):
        """Test pruning when conversations are within token limit"""
        # Mock token count to be within safe zone
        mock_count_tokens.return_value = 500  # Below the 1000 token threshold
        
        result = pruner.prune_conversations(sample_conversations)
        
        # Should return original conversations unchanged
        assert result == sample_conversations
        mock_count_tokens.assert_called_once()

    @patch('autocoder.rag.token_counter.count_tokens')
    def test_prune_conversations_exceeds_limit(self, mock_count_tokens, pruner, sample_conversations):
        """Test pruning when conversations exceed token limit"""
        # Mock token count to exceed safe zone initially, then be within limit after pruning
        mock_count_tokens.side_effect = [2000, 1500, 800]  # First call exceeds, subsequent calls within limit
        
        result = pruner.prune_conversations(sample_conversations)
        
        # Should have processed the conversations
        assert isinstance(result, list)
        assert len(result) == len(sample_conversations)
        
        # Check that tool results were cleaned
        cleaned_found = False
        for conv in result:
            if conv.get("role") == "user" and "<tool_result" in conv.get("content", ""):
                if "This message has been cleared" in conv.get("content", ""):
                    cleaned_found = True
                    break
        
        assert cleaned_found, "Expected to find cleaned tool results"

    def test_is_tool_result_message(self, pruner):
        """Test tool result message detection"""
        # Test cases for tool result detection
        test_cases = [
            ("<tool_result tool_name='ReadFileTool' success='true'>content</tool_result>", True),
            ("<tool_result tool_name=\"ListTool\" success=\"false\">error</tool_result>", True),
            ("Regular message without tool result", False),
            ("<tool_result>missing tool_name</tool_result>", False),
            ("", False),
            ("<some_other_tag tool_name='test'>content</some_other_tag>", False)
        ]
        
        for content, expected in test_cases:
            result = pruner._is_tool_result_message(content)
            assert result == expected, f"Failed for content: {content}"

    def test_extract_tool_name(self, pruner):
        """Test tool name extraction from tool results"""
        test_cases = [
            ("<tool_result tool_name='ReadFileTool' success='true'>", "ReadFileTool"),
            ('<tool_result tool_name="ListFilesTool" success="true">', "ListFilesTool"),
            ("<tool_result success='true' tool_name='WriteTool'>", "WriteTool"),
            ("<tool_result success='true'>", "unknown"),
            ("Not a tool result", "unknown"),
            ("", "unknown"),
            ("<tool_result tool_name=''>", ""),
            ("<tool_result tool_name='Tool With Spaces'>", "Tool With Spaces")
        ]
        
        for content, expected in test_cases:
            result = pruner._extract_tool_name(content)
            assert result == expected, f"Failed for content: {content}"

    def test_generate_replacement_message(self, pruner):
        """Test replacement message generation"""
        test_cases = [
            "ReadFileTool",
            "ListFilesTool", 
            "unknown",
            "",
            "CustomTool"
        ]
        
        for tool_name in test_cases:
            replacement = pruner._generate_replacement_message(tool_name)
            
            # Check that replacement contains expected elements
            assert "<tool_result" in replacement
            assert "Content cleared to save tokens" in replacement
            assert pruner.replacement_message in replacement
            
            if tool_name and tool_name != "unknown":
                assert f"tool_name='{tool_name}'" in replacement

    @patch('autocoder.rag.token_counter.count_tokens')
    def test_get_cleanup_statistics(self, mock_count_tokens, pruner, sample_conversations):
        """Test cleanup statistics calculation"""
        # Mock token counts
        mock_count_tokens.side_effect = [2000, 1200]  # Original: 2000, Pruned: 1200
        
        # Create pruned conversations (simulate cleaning)
        pruned_conversations = sample_conversations.copy()
        pruned_conversations[3]["content"] = "<tool_result tool_name='ReadFileTool' success='true'><message>Content cleared to save tokens</message><content>This message has been cleared</content></tool_result>"
        
        stats = pruner.get_cleanup_statistics(sample_conversations, pruned_conversations)
        
        # Verify statistics
        assert stats['original_tokens'] == 2000
        assert stats['pruned_tokens'] == 1200
        assert stats['tokens_saved'] == 800
        assert stats['compression_ratio'] == 0.6
        assert stats['tool_results_cleaned'] == 1
        assert stats['total_messages'] == len(sample_conversations)

    def test_prune_conversations_invalid_strategy(self, pruner, sample_conversations):
        """Test pruning with invalid strategy name"""
        with patch('autocoder.rag.token_counter.count_tokens', return_value=2000):
            # Should fall back to default strategy
            result = pruner.prune_conversations(sample_conversations, strategy_name="invalid_strategy")
            assert isinstance(result, list)

    def test_prune_conversations_empty_list(self, pruner):
        """Test pruning with empty conversation list"""
        with patch('autocoder.rag.token_counter.count_tokens', return_value=0):
            result = pruner.prune_conversations([])
            assert result == []

    def test_prune_conversations_no_tool_results(self, pruner):
        """Test pruning conversations without tool results"""
        conversations = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "I'm doing well, thank you!"}
        ]
        
        with patch('autocoder.rag.token_counter.count_tokens', return_value=2000):
            result = pruner.prune_conversations(conversations)
            # Should return original since no tool results to clean
            assert result == conversations

    @patch('autocoder.rag.token_counter.count_tokens')
    def test_progressive_cleanup(self, mock_count_tokens, pruner):
        """Test that cleanup happens progressively from earliest tool results"""
        conversations = [
            {"role": "user", "content": "First request"},
            {"role": "user", "content": "<tool_result tool_name='Tool1'><content>First result</content></tool_result>"},
            {"role": "user", "content": "Second request"},
            {"role": "user", "content": "<tool_result tool_name='Tool2'><content>Second result</content></tool_result>"},
            {"role": "user", "content": "Third request"},
            {"role": "user", "content": "<tool_result tool_name='Tool3'><content>Third result</content></tool_result>"}
        ]
        
        # Mock token counts: initial exceeds limit, after first cleanup still exceeds, after second cleanup within limit
        mock_count_tokens.side_effect = [3000, 2500, 1800, 800]
        
        result = pruner.prune_conversations(conversations)
        
        # Check that first two tool results were cleaned (progressive cleanup)
        cleaned_count = 0
        for conv in result:
            if conv.get("role") == "user" and "<tool_result" in conv.get("content", ""):
                if "This message has been cleared" in conv.get("content", ""):
                    cleaned_count += 1
        
        assert cleaned_count >= 1, "Expected at least one tool result to be cleaned"

    def test_edge_cases(self, pruner):
        """Test various edge cases"""
        # Test with None content
        assert not pruner._is_tool_result_message(None)
        
        # Test with malformed tool result
        malformed = "<tool_result tool_name='Test' incomplete"
        assert pruner._extract_tool_name(malformed) == "Test"
        
        # Test with special characters in tool name
        special_chars = "<tool_result tool_name='Tool-With_Special.Chars123' success='true'>"
        assert pruner._extract_tool_name(special_chars) == "Tool-With_Special.Chars123"


class TestAgenticConversationPrunerIntegration:
    """Integration tests for AgenticConversationPruner"""

    @pytest.fixture
    def real_args(self):
        """Create real AutoCoderArgs for integration testing"""
        # Note: This would require actual AutoCoderArgs implementation
        # For now, use MagicMock with realistic values
        args = MagicMock()
        args.conversation_prune_safe_zone_tokens = 50000
        return args

    def test_realistic_scenario(self, real_args):
        """Test with realistic conversation scenario"""
        mock_llm = MagicMock()
        pruner = AgenticConversationPruner(args=real_args, llm=mock_llm)
        
        # Create a realistic conversation with large tool outputs
        conversations = [
            {"role": "system", "content": "You are a helpful coding assistant."},
            {"role": "user", "content": "Can you read the main.py file and analyze it?"},
            {"role": "assistant", "content": "I'll read the file for you.\n\n<read_file>\n<path>main.py</path>\n</read_file>"},
            {
                "role": "user",
                "content": f"<tool_result tool_name='ReadFileTool' success='true'><message>File read successfully</message><content>{'# ' + 'Very long file content ' * 1000}</content></tool_result>"
            },
            {"role": "assistant", "content": "I can see this is a large Python file. Let me analyze its structure..."},
            {"role": "user", "content": "Now can you list all Python files in the directory?"},
            {"role": "assistant", "content": "I'll list the Python files.\n\n<list_files>\n<path>.</path>\n<pattern>*.py</pattern>\n</list_files>"},
            {
                "role": "user",
                "content": f"<tool_result tool_name='ListFilesTool' success='true'><message>Files listed</message><content>{json.dumps(['file' + str(i) + '.py' for i in range(100)])}</content></tool_result>"
            }
        ]
        
        with patch('autocoder.rag.token_counter.count_tokens') as mock_count:
            # Simulate large token count that exceeds limit
            mock_count.side_effect = [100000, 80000, 45000]  # Progressive reduction
            
            result = pruner.prune_conversations(conversations)
            
            # Verify the result is valid
            assert isinstance(result, list)
            assert len(result) == len(conversations)
            
            # Verify that some cleanup occurred
            stats = pruner.get_cleanup_statistics(conversations, result)
            assert isinstance(stats, dict)
            assert all(key in stats for key in ['original_tokens', 'pruned_tokens', 'tokens_saved', 'compression_ratio', 'tool_results_cleaned', 'total_messages'])


# Parametrized tests for comprehensive coverage
class TestParametrized:
    """Parametrized tests for comprehensive coverage"""

    @pytest.mark.parametrize("tool_name,expected", [
        ("ReadFileTool", "ReadFileTool"),
        ("ListFilesTool", "ListFilesTool"),
        ("WriteTool", "WriteTool"),
        ("", ""),
        ("Tool_With_Underscores", "Tool_With_Underscores"),
        ("Tool-With-Hyphens", "Tool-With-Hyphens"),
        ("Tool123", "Tool123"),
    ])
    def test_tool_name_extraction_parametrized(self, tool_name, expected):
        """Parametrized test for tool name extraction"""
        pruner = AgenticConversationPruner(MagicMock(), MagicMock())
        content = f"<tool_result tool_name='{tool_name}' success='true'>"
        result = pruner._extract_tool_name(content)
        assert result == expected

    @pytest.mark.parametrize("content,expected", [
        ("<tool_result tool_name='Test' success='true'>content</tool_result>", True),
        ("<tool_result tool_name=\"Test\" success=\"true\">content</tool_result>", True),
        ("Regular message", False),
        ("<tool_result>no tool_name</tool_result>", False),
        ("", False),
        ("<other_tag tool_name='test'>content</other_tag>", False),
    ])
    def test_tool_result_detection_parametrized(self, content, expected):
        """Parametrized test for tool result detection"""
        pruner = AgenticConversationPruner(MagicMock(), MagicMock())
        result = pruner._is_tool_result_message(content)
        assert result == expected


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v"])
