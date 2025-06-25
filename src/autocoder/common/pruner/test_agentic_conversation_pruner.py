import json
from unittest.mock import MagicMock
from autocoder.common.pruner.agentic_conversation_pruner import AgenticConversationPruner
from autocoder.common import AutoCoderArgs

def test_agentic_conversation_pruner():
    """Test the agentic conversation pruner functionality"""
    
    # Mock args and llm
    args = MagicMock()
    args.conversation_prune_safe_zone_tokens = 1000  # Small threshold for testing
    llm = MagicMock()
    
    # Create pruner instance
    pruner = AgenticConversationPruner(args=args, llm=llm)
    
    # Create test conversations with tool results
    test_conversations = [
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
    
    print("=== Original Conversations ===")
    for i, conv in enumerate(test_conversations):
        print(f"{i}: {conv['role']} - {conv['content'][:100]}...")
    
    # Test pruning
    pruned_conversations = pruner.prune_conversations(test_conversations)
    
    print("\n=== Pruned Conversations ===")
    for i, conv in enumerate(pruned_conversations):
        print(f"{i}: {conv['role']} - {conv['content'][:100]}...")
    
    # Get statistics
    stats = pruner.get_cleanup_statistics(test_conversations, pruned_conversations)
    print(f"\n=== Cleanup Statistics ===")
    for key, value in stats.items():
        print(f"{key}: {value}")
    
    # Verify that tool results were cleaned
    tool_result_found = False
    cleaned_tool_result_found = False
    
    for conv in pruned_conversations:
        if conv.get("role") == "user" and "<tool_result" in conv.get("content", ""):
            if "This message has been cleared" in conv.get("content", ""):
                cleaned_tool_result_found = True
            else:
                tool_result_found = True
    
    print(f"\nTool results cleaned: {cleaned_tool_result_found}")
    print(f"Original tool results remaining: {tool_result_found}")
    
    return pruned_conversations, stats

def test_tool_name_extraction():
    """Test tool name extraction functionality"""
    pruner = AgenticConversationPruner(MagicMock(), MagicMock())
    
    test_cases = [
        ("<tool_result tool_name='ReadFileTool' success='true'>", "ReadFileTool"),
        ('<tool_result tool_name="ListFilesTool" success="true">', "ListFilesTool"),
        ("<tool_result success='true' tool_name='WriteTool'>", "WriteTool"),
        ("<tool_result success='true'>", "unknown"),
        ("Not a tool result", "unknown")
    ]
    
    print("\n=== Tool Name Extraction Tests ===")
    for content, expected in test_cases:
        result = pruner._extract_tool_name(content)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{content[:50]}...' -> '{result}' (expected: '{expected}')")

def test_replacement_message_generation():
    """Test replacement message generation"""
    pruner = AgenticConversationPruner(MagicMock(), MagicMock())
    
    test_cases = [
        "ReadFileTool",
        "ListFilesTool", 
        "unknown",
        ""
    ]
    
    print("\n=== Replacement Message Generation Tests ===")
    for tool_name in test_cases:
        replacement = pruner._generate_replacement_message(tool_name)
        print(f"Tool: '{tool_name}' -> {replacement[:100]}...")

if __name__ == "__main__":
    # Run basic functionality test
    test_agentic_conversation_pruner()
    
    # Run extraction tests
    test_tool_name_extraction()
    
    # Run replacement message tests  
    test_replacement_message_generation()
    
    print("\n✓ All tests completed!") 