"""
Compatibility layer for existing conversation implementations.

This module provides adapter functions and classes to help
transition from the existing conversation implementations to 
the new unified conversation manager.
"""

from typing import Dict, List, Any, Optional, Callable, Union
import time
from pydantic import BaseModel

from autocoder.common import AutoCoderArgs
from autocoder.common.conversations.conversation_manager import (
    ConversationManager, 
    ConversationType, 
    get_conversation_manager,
    Message
)


# ======= CommandMessage (auto_command.py) Compatibility =======

class CommandMessage(BaseModel):
    """Compatible with auto_command.py CommandMessage."""
    role: str
    content: str


class ExtendedCommandMessage(BaseModel):
    """Compatible with auto_command.py ExtendedCommandMessage."""
    message: CommandMessage
    timestamp: str


class CommandConversation(BaseModel):
    """Compatible with auto_command.py CommandConversation."""
    history: Dict[str, ExtendedCommandMessage]
    current_conversation: List[ExtendedCommandMessage]


def command_message_to_message(cmd_msg: Union[CommandMessage, ExtendedCommandMessage]) -> Message:
    """Convert a CommandMessage or ExtendedCommandMessage to a Message."""
    if isinstance(cmd_msg, ExtendedCommandMessage):
        return Message(
            role=cmd_msg.message.role,
            content=cmd_msg.message.content,
            timestamp=int(cmd_msg.timestamp)
        )
    else:
        return Message(
            role=cmd_msg.role,
            content=cmd_msg.content
        )


def message_to_command_message(msg: Message) -> ExtendedCommandMessage:
    """Convert a Message to an ExtendedCommandMessage."""
    return ExtendedCommandMessage(
        message=CommandMessage(
            role=msg.role,
            content=msg.content or ""
        ),
        timestamp=str(msg.timestamp or int(time.time()))
    )


def load_command_conversation(args: AutoCoderArgs, conv_id: str = "command") -> CommandConversation:
    """
    Load a command conversation in the old format.
    
    Args:
        args: AutoCoderArgs object
        conv_id: Conversation ID (defaults to "command")
        
    Returns:
        A CommandConversation object compatible with auto_command.py
    """
    manager = get_conversation_manager(args)
    conversation = manager.get_conversation(
        conv_id=conv_id, 
        conv_type=ConversationType.COMMAND,
        create_if_not_exists=True
    )
    
    # Convert to old format
    current_conversation = [
        message_to_command_message(msg) 
        for msg in conversation.messages
    ]
    
    # Convert archived conversations
    history = {}
    if conversation.archived_conversations:
        for timestamp, messages in conversation.archived_conversations.items():
            history[timestamp] = [
                message_to_command_message(msg) 
                for msg in messages
            ]
    
    return CommandConversation(
        history=history,
        current_conversation=current_conversation
    )


def save_command_conversation(
    args: AutoCoderArgs, 
    conv: CommandConversation, 
    conv_id: str = "command"
) -> None:
    """
    Save a command conversation from the old format.
    
    Args:
        args: AutoCoderArgs object
        conv: CommandConversation object
        conv_id: Conversation ID (defaults to "command")
    """
    manager = get_conversation_manager(args)
    conversation = manager.get_conversation(
        conv_id=conv_id, 
        conv_type=ConversationType.COMMAND,
        create_if_not_exists=True
    )
    
    # Convert messages
    conversation.messages = [
        command_message_to_message(msg) 
        for msg in conv.current_conversation
    ]
    
    # Convert archived conversations
    conversation.archived_conversations = {}
    for timestamp, messages in conv.history.items():
        conversation.archived_conversations[timestamp] = [
            command_message_to_message(msg) 
            for msg in messages
        ]
    
    # Save
    manager._save_conversation(conversation)


def save_to_command_memory_file(
    args: AutoCoderArgs, 
    query: str, 
    response: str, 
    conv_id: str = "command"
) -> None:
    """
    Save a command conversation message pair.
    
    Args:
        args: AutoCoderArgs object
        query: User query
        response: Assistant response
        conv_id: Conversation ID
    """
    manager = get_conversation_manager(args)
    conversation = manager.get_conversation(
        conv_id=conv_id, 
        conv_type=ConversationType.COMMAND,
        create_if_not_exists=True
    )
    
    # Add the messages
    manager.add_user_message(conv_id, query)
    manager.add_assistant_message(conv_id, response)


# ======= AgenticConversation (agentic_edit_conversation.py) Compatibility =======

def get_agentic_conversation(
    args: AutoCoderArgs, 
    conversation_name: Optional[str] = None,
    event_id: Optional[str] = None
) -> 'AgenticConversationWrapper':
    """
    Get an AgenticConversation wrapper that mimics the original class.
    
    Args:
        args: AutoCoderArgs object
        conversation_name: Optional conversation name
        event_id: Optional event ID
        
    Returns:
        An AgenticConversationWrapper object compatible with agentic_edit_conversation.py
    """
    return AgenticConversationWrapper(args, conversation_name, event_id)


class AgenticConversationWrapper:
    """Wrapper that mimics the AgenticConversation class from agentic_edit_conversation.py."""
    
    def __init__(
        self, 
        args: AutoCoderArgs, 
        conversation_name: Optional[str] = None,
        event_id: Optional[str] = None,
        initial_history: Optional[List[Dict[str, Any]]] = None
    ):
        """
        Initialize the AgenticConversation wrapper.
        
        Args:
            args: AutoCoderArgs object
            conversation_name: Optional conversation name, used as conv_id
            event_id: Optional event ID to associate with this conversation
            initial_history: Optional initial conversation history
        """
        self.args = args
        self.project_path = args.source_dir
        self.conversation_name = conversation_name or "agentic_edit"
        self.event_id = event_id
        
        # Get the conversation manager
        self.manager = get_conversation_manager(args)
        
        # Get or create the conversation
        self.conversation = self.manager.get_conversation(
            conv_id=self.conversation_name,
            event_id=self.event_id,
            conv_type=ConversationType.AGENTIC_EDIT,
            create_if_not_exists=True
        )
        
        # Add initial history if provided
        if initial_history:
            self._add_initial_history(initial_history)
    
    def _add_initial_history(self, history: List[Dict[str, Any]]) -> None:
        """Add initial history to the conversation."""
        for msg in history:
            role = msg.get("role", "")
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", None)
            tool_call_id = msg.get("tool_call_id", None)
            
            self.manager.add_message(
                self.conversation.id,
                role,
                content,
                tool_calls=tool_calls,
                tool_call_id=tool_call_id
            )
    
    def add_message(self, role: str, content: Any, **kwargs) -> None:
        """Add a message to the conversation."""
        self.manager.add_message(
            self.conversation.id,
            role,
            content,
            **kwargs
        )
    
    def add_user_message(self, content: str) -> None:
        """Add a user message to the conversation."""
        self.manager.add_user_message(self.conversation.id, content)
    
    def add_assistant_message(self, content: str) -> None:
        """Add an assistant message to the conversation."""
        self.manager.add_assistant_message(self.conversation.id, content)
    
    def append_to_last_message(self, content: str, role: str = "assistant") -> None:
        """Append content to the last message."""
        self.manager.append_to_last_message(
            self.conversation.id,
            content,
            role
        )
    
    def add_assistant_tool_call_message(self, tool_calls: List[Dict[str, Any]], content: Optional[str] = None) -> None:
        """Add a tool call message from the assistant."""
        self.manager.add_tool_call_message(
            self.conversation.id,
            tool_calls,
            content
        )
    
    def add_tool_result_message(self, tool_call_id: str, content: Any) -> None:
        """Add a tool result message."""
        self.manager.add_tool_result_message(
            self.conversation.id,
            tool_call_id,
            content
        )
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get the conversation history in the format expected by agentic_edit."""
        return self.manager.get_history_as_dict_list(self.conversation.id)
    
    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.manager.clear_conversation(self.conversation.id)
    
    def __len__(self) -> int:
        """Return the number of messages in the conversation."""
        return len(self.conversation.messages)
    
    def __str__(self) -> str:
        """Return a string representation of the conversation."""
        return str(self.get_history()) 