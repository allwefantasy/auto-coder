"""
Example usage of the unified conversation manager.

This file demonstrates how to use the unified conversation manager
for different conversation types (command, agentic_edit, chat).
"""

from autocoder.common import AutoCoderArgs
from autocoder.common.conversations.conversation_manager import (
    ConversationManager,
    ConversationType,
    get_conversation_manager,
    Message
)
from autocoder.common.conversations.compatibility import (
    load_command_conversation, 
    save_command_conversation,
    save_to_command_memory_file,
    get_agentic_conversation
)


def example_command_conversation(args: AutoCoderArgs):
    """Example of using the manager for command conversations."""
    # Get the conversation manager
    manager = get_conversation_manager(args)
    
    # Create a command conversation (or get existing one)
    conversation = manager.get_conversation(
        conv_id="command_example",
        conv_type=ConversationType.COMMAND,
        create_if_not_exists=True
    )
    
    # Add messages
    manager.add_user_message(conversation.id, "What's the weather like today?")
    manager.add_assistant_message(conversation.id, "I'm sorry, I don't have access to real-time weather data.")
    
    # Get conversation history
    history = manager.get_history_as_dict_list(conversation.id)
    print("Command conversation history:")
    for msg in history:
        print(f"{msg['role']}: {msg['content']}")
    
    # Archive the conversation (useful for command conversations)
    manager.archive_conversation(conversation.id)
    
    # Add new messages
    manager.add_user_message(conversation.id, "What time is it?")
    manager.add_assistant_message(conversation.id, "I don't have access to real-time clock information.")
    
    # Using compatibility functions
    old_format = load_command_conversation(args, conversation.id)
    print(f"\nLoaded in old format: {len(old_format.current_conversation)} current messages, {len(old_format.history)} archived conversations")
    
    # Save in old format
    save_command_conversation(args, old_format, conversation.id)
    
    # Simple save function (common in auto_command.py)
    save_to_command_memory_file(args, "How are you?", "I'm doing well, thank you!", conversation.id)


def example_agentic_edit_conversation(args: AutoCoderArgs):
    """Example of using the manager for agentic edit conversations."""
    # Using the compatibility wrapper
    agentic_conv = get_agentic_conversation(
        args, 
        conversation_name="agentic_example",
        event_id="event_123"
    )
    
    # Add messages
    agentic_conv.add_user_message("Please help me refactor this code.")
    agentic_conv.add_assistant_message("I'll help you refactor your code. Let me analyze it first.")
    
    # Add tool call and result
    tool_calls = [{
        "id": "tool-1",
        "type": "function",
        "function": {
            "name": "read_file",
            "arguments": {"path": "example.py"}
        }
    }]
    
    agentic_conv.add_assistant_tool_call_message(tool_calls, "I need to read the file first.")
    agentic_conv.add_tool_result_message("tool-1", "print('Hello, world!')")
    
    # Get history
    history = agentic_conv.get_history()
    print("\nAgentic edit conversation history:")
    for msg in history:
        role = msg["role"]
        content = msg.get("content", "")
        tool_calls = msg.get("tool_calls", [])
        tool_call_id = msg.get("tool_call_id", "")
        
        if role == "assistant" and tool_calls:
            print(f"{role}: {content} [Tool calls: {len(tool_calls)}]")
        elif role == "tool":
            print(f"{role} ({tool_call_id}): {content}")
        else:
            print(f"{role}: {content}")


def example_chat_conversation(args: AutoCoderArgs, event_id: str):
    """Example of using the manager for chat conversations with event_id."""
    # Get the conversation manager
    manager = get_conversation_manager(args)
    
    # Get or create a conversation by event_id
    conversation = manager.get_conversation(
        event_id=event_id,
        conv_type=ConversationType.CHAT,
        create_if_not_exists=True
    )
    
    # Add messages
    manager.add_user_message(conversation.id, "Tell me about Python's asyncio.")
    manager.add_assistant_message(conversation.id, "Python's asyncio is a library to write concurrent code using the async/await syntax.")
    
    # Add another message
    manager.add_message_by_event_id(event_id, "user", "How does it compare to threading?")
    
    # Get history
    history = manager.get_history_as_dict_list(conversation.id)
    print("\nChat conversation history (event_id: {event_id}):")
    for msg in history:
        print(f"{msg['role']}: {msg['content']}")


def main():
    """Main function to run examples."""
    # Create dummy args
    args = AutoCoderArgs(source_dir=".")
    
    # Run examples
    example_command_conversation(args)
    example_agentic_edit_conversation(args)
    example_chat_conversation(args, "user_session_123")
    
    # Show retrieval by event_id
    manager = get_conversation_manager(args)
    conversation = manager.get_conversation(event_id="user_session_123")
    if conversation:
        print(f"\nSuccessfully retrieved conversation by event_id: {conversation.id}")
    else:
        print("\nFailed to retrieve conversation by event_id")


if __name__ == "__main__":
    main() 