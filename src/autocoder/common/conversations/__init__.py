"""
Conversation management package for AutoCoder.

This package provides a unified conversation management system that serves
different components of AutoCoder, replacing separate implementations in:
- agentic_edit.py
- auto_command.py
- agentic_edit_conversation.py
"""

from autocoder.common.conversations.conversation_manager import (
    ConversationManager,
    ConversationType,
    get_conversation_manager,
    Message,
    Conversation
)

from autocoder.common.conversations.compatibility import (
    # Command conversation compatibility
    CommandMessage,
    ExtendedCommandMessage,
    CommandConversation,
    load_command_conversation,
    save_command_conversation,
    save_to_command_memory_file,
    
    # Agentic edit conversation compatibility
    get_agentic_conversation,
    AgenticConversationWrapper
)

__all__ = [
    # Main conversation manager
    'ConversationManager',
    'ConversationType',
    'get_conversation_manager',
    'Message',
    'Conversation',
    
    # Command conversation compatibility
    'CommandMessage',
    'ExtendedCommandMessage',
    'CommandConversation',
    'load_command_conversation',
    'save_command_conversation',
    'save_to_command_memory_file',
    
    # Agentic edit conversation compatibility
    'get_agentic_conversation',
    'AgenticConversationWrapper'
] 