"""
Unified conversation manager for AutoCoder.

This module provides a centralized conversation management system that can be used
by different components of AutoCoder (agentic_edit, auto_command, etc.) instead of
having separate conversation handling implementations.
"""

import os
import json
import time
import uuid
from enum import Enum
from typing import Dict, List, Any, Optional, Union, Callable
from pydantic import BaseModel, Field

from autocoder.common import AutoCoderArgs
from autocoder.common.printer import Printer


class ConversationType(Enum):
    """Types of conversations supported by the manager."""
    COMMAND = "command"
    AGENTIC_EDIT = "agentic_edit"
    CHAT = "chat"


class Message(BaseModel):
    """Base message model with role and content."""
    role: str
    content: Optional[str] = None
    timestamp: Optional[int] = Field(default_factory=lambda: int(time.time()))
    
    # Additional fields for tool calls
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    
    # For any additional metadata
    metadata: Optional[Dict[str, Any]] = None


class Conversation(BaseModel):
    """Model representing a conversation with its messages."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: ConversationType
    messages: List[Message] = []
    
    # For command conversations
    archived_conversations: Optional[Dict[str, List[Message]]] = None


class ConversationManager:
    """
    Unified conversation manager for AutoCoder.
    
    This class handles conversation storage, retrieval, and operations for
    different components of AutoCoder, replacing separate implementations.
    """
    
    def __init__(self, args: AutoCoderArgs):
        """
        Initialize the conversation manager.
        
        Args:
            args: AutoCoderArgs object containing configuration.
        """
        self.args = args
        self.project_dir = args.source_dir
        self.memory_base_dir = os.path.join(self.project_dir, ".auto-coder", "memory", "conversations")
        os.makedirs(self.memory_base_dir, exist_ok=True)
        
        # Cache of loaded conversations by id
        self._conversations: Dict[str, Conversation] = {}
        
        # Map of event_id to conversation_id
        self._event_mapping: Dict[str, str] = self._load_event_mapping()
    
    def _get_conversation_dir(self, conv_type: ConversationType) -> str:
        """Get the directory for a specific conversation type."""
        return os.path.join(self.memory_base_dir, conv_type.value)
    
    def _get_conversation_path(self, conv_id: str, conv_type: ConversationType) -> str:
        """Get the file path for a specific conversation."""
        conv_dir = self._get_conversation_dir(conv_type)
        os.makedirs(conv_dir, exist_ok=True)
        return os.path.join(conv_dir, f"{conv_id}.json")
    
    def _load_event_mapping(self) -> Dict[str, str]:
        """Load the mapping of event_id to conversation_id."""
        mapping_path = os.path.join(self.memory_base_dir, "event_mapping.json")
        if os.path.exists(mapping_path):
            try:
                with open(mapping_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading event mapping: {e}")
        return {}
    
    def _save_event_mapping(self):
        """Save the mapping of event_id to conversation_id."""
        mapping_path = os.path.join(self.memory_base_dir, "event_mapping.json")
        try:
            with open(mapping_path, "w", encoding="utf-8") as f:
                json.dump(self._event_mapping, f, indent=2)
        except Exception as e:
            print(f"Error saving event mapping: {e}")
    
    def create_conversation(
        self, 
        conv_type: ConversationType, 
        event_id: Optional[str] = None,
        conv_id: Optional[str] = None
    ) -> Conversation:
        """
        Create a new conversation.
        
        Args:
            conv_type: Type of the conversation.
            event_id: Optional event ID to associate with this conversation.
            conv_id: Optional conversation ID. If not provided, a UUID will be generated.
            
        Returns:
            The created Conversation object.
        """
        conv_id = conv_id or str(uuid.uuid4())
        
        # Create conversation with appropriate initial structure
        if conv_type == ConversationType.COMMAND:
            conversation = Conversation(
                id=conv_id,
                type=conv_type,
                archived_conversations={}
            )
        else:
            conversation = Conversation(
                id=conv_id,
                type=conv_type
            )
        
        # Save conversation
        self._conversations[conv_id] = conversation
        self._save_conversation(conversation)
        
        # Map event_id to conversation_id if provided
        if event_id:
            self._event_mapping[event_id] = conv_id
            self._save_event_mapping()
        
        return conversation
    
    def get_conversation(
        self, 
        event_id: Optional[str] = None, 
        conv_id: Optional[str] = None,
        conv_type: Optional[ConversationType] = None,
        create_if_not_exists: bool = True
    ) -> Optional[Conversation]:
        """
        Get a conversation by event_id or conv_id.
        
        Args:
            event_id: Event ID associated with the conversation.
            conv_id: Conversation ID.
            conv_type: Type of conversation to create if not exists.
            create_if_not_exists: Whether to create a new conversation if not found.
            
        Returns:
            The Conversation object or None if not found and create_if_not_exists is False.
        """
        # Try to find by event_id first
        if event_id and event_id in self._event_mapping:
            conv_id = self._event_mapping[event_id]
            
        # Return conversation from cache if available
        if conv_id and conv_id in self._conversations:
            return self._conversations[conv_id]
        
        # Try to load from disk if we have conv_id
        if conv_id:
            for type_value in ConversationType:
                conv_path = self._get_conversation_path(conv_id, type_value)
                if os.path.exists(conv_path):
                    conversation = self._load_conversation(conv_path, type_value)
                    if conversation:
                        self._conversations[conv_id] = conversation
                        return conversation
        
        # Create new if requested
        if create_if_not_exists and conv_type:
            return self.create_conversation(conv_type, event_id, conv_id)
            
        return None
    
    def add_message(
        self, 
        conv_id: str, 
        role: str, 
        content: Optional[str] = None,
        **kwargs
    ) -> Message:
        """
        Add a message to a conversation.
        
        Args:
            conv_id: Conversation ID.
            role: Role of the message sender (user, assistant, tool, etc.).
            content: Content of the message.
            **kwargs: Additional message fields.
            
        Returns:
            The created Message object.
        """
        conversation = self._conversations.get(conv_id)
        if not conversation:
            raise ValueError(f"Conversation {conv_id} not found")
            
        message = Message(role=role, content=content, **kwargs)
        conversation.messages.append(message)
        self._save_conversation(conversation)
        return message
    
    def add_message_by_event_id(
        self, 
        event_id: str, 
        role: str, 
        content: Optional[str] = None,
        **kwargs
    ) -> Optional[Message]:
        """
        Add a message to a conversation identified by event_id.
        
        Args:
            event_id: Event ID associated with the conversation.
            role: Role of the message sender.
            content: Content of the message.
            **kwargs: Additional message fields.
            
        Returns:
            The created Message object or None if conversation not found.
        """
        if event_id not in self._event_mapping:
            return None
            
        conv_id = self._event_mapping[event_id]
        return self.add_message(conv_id, role, content, **kwargs)
    
    def add_user_message(self, conv_id: str, content: str) -> Message:
        """Add a user message to a conversation."""
        return self.add_message(conv_id, "user", content)
    
    def add_assistant_message(self, conv_id: str, content: str) -> Message:
        """Add an assistant message to a conversation."""
        return self.add_message(conv_id, "assistant", content)
    
    def add_tool_call_message(self, conv_id: str, tool_calls: List[Dict[str, Any]], content: Optional[str] = None) -> Message:
        """Add a tool call message to a conversation."""
        return self.add_message(conv_id, "assistant", content, tool_calls=tool_calls)
    
    def add_tool_result_message(self, conv_id: str, tool_call_id: str, content: Any) -> Message:
        """Add a tool result message to a conversation."""
        return self.add_message(conv_id, "tool", content, tool_call_id=tool_call_id)
    
    def append_to_last_message(self, conv_id: str, content: str, role: Optional[str] = None) -> bool:
        """
        Append content to the last message in the conversation.
        
        Args:
            conv_id: Conversation ID.
            content: Content to append.
            role: If specified, only append if the last message has this role.
            
        Returns:
            True if appended successfully, False otherwise.
        """
        conversation = self._conversations.get(conv_id)
        if not conversation or not conversation.messages:
            return False
            
        last_message = conversation.messages[-1]
        if role and last_message.role != role:
            return False
            
        # Append to content, creating it if it doesn't exist
        if last_message.content is None:
            last_message.content = content
        else:
            last_message.content += content
            
        self._save_conversation(conversation)
        return True
    
    def get_history(self, conv_id: str, max_pairs: int = -1) -> List[Message]:
        """
        Get the conversation history.

        If max_pairs == -1, return all messages as-is (no pairing/merging).
        If max_pairs != -1, return the latest max_pairs user-assistant pairs,
        with pairing/merging logic for all conversation types.

        Args:
            conv_id: Conversation ID.
            max_pairs: Maximum number of user-assistant pairs to return. 
                       If -1, returns all messages directly.

        Returns:
            List of messages representing the conversation history.
        """
        conversation = self._conversations.get(conv_id)
        if not conversation:
            return []

        if max_pairs == -1:
            # No pairing/merging, return all messages as-is
            return conversation.messages

        # Pairing/merging logic for all conversation types when max_pairs != -1
        paired_history = []
        pair_count = 0
        pending_assistant = None
        pending_user = None

        # Traverse history in reverse to collect latest pairs with merging
        for msg in reversed(conversation.messages):
            role = msg.role
            if role == "assistant":
                if pending_assistant is None:
                    pending_assistant = msg
                else:
                    # Merge with previous assistant
                    prev_content = pending_assistant.content or ""
                    curr_content = msg.content or ""
                    merged_content = (curr_content.strip() + "\n" + prev_content.strip()).strip()
                    pending_assistant.content = merged_content
            elif role == "user":
                if pending_user is None:
                    pending_user = msg
                else:
                    # Merge with previous user
                    prev_content = pending_user.content or ""
                    curr_content = msg.content or ""
                    merged_content = (curr_content.strip() + "\n" + prev_content.strip()).strip()
                    pending_user.content = merged_content

                if pending_assistant is not None:
                    # Have a full pair, insert in order
                    paired_history.insert(0, pending_user)
                    paired_history.insert(1, pending_assistant)
                    pair_count += 1
                    pending_assistant = None
                    pending_user = None
                    if pair_count >= max_pairs:
                        break
                else:
                    # User without assistant yet, continue accumulating
                    continue
            else:
                # Ignore other roles
                continue

        # Ensure last message is assistant, drop trailing user if unpaired
        if paired_history and paired_history[-1].role == "user":
            paired_history.pop()

        return paired_history
    
    def get_history_as_dict_list(self, conv_id: str, max_pairs: int = 20) -> List[Dict[str, Any]]:
        """
        Get conversation history as a list of dictionaries suitable for LLM APIs.
        
        Args:
            conv_id: Conversation ID.
            max_pairs: Maximum number of user-assistant pairs to return.
            
        Returns:
            List of dictionaries with 'role' and 'content' keys.
        """
        history = self.get_history(conv_id, max_pairs)
        return [msg.model_dump(exclude={"timestamp", "metadata"}) for msg in history]
    
    def clear_conversation(self, conv_id: str) -> bool:
        """
        Clear all messages from a conversation.
        
        Args:
            conv_id: Conversation ID.
            
        Returns:
            True if cleared successfully, False otherwise.
        """
        conversation = self._conversations.get(conv_id)
        if not conversation:
            return False
            
        conversation.messages = []
        self._save_conversation(conversation)
        return True
    
    def archive_conversation(self, conv_id: str) -> bool:
        """
        Archive a command conversation.
        
        Args:
            conv_id: Conversation ID.
            
        Returns:
            True if archived successfully, False otherwise.
        """
        conversation = self._conversations.get(conv_id)
        if not conversation or conversation.type != ConversationType.COMMAND:
            return False
            
        # For COMMAND type, archive current messages
        if conversation.messages:
            timestamp = str(int(time.time()))
            conversation.archived_conversations = conversation.archived_conversations or {}
            conversation.archived_conversations[timestamp] = conversation.messages
            conversation.messages = []
            self._save_conversation(conversation)
            
        return True
    
    def _save_conversation(self, conversation: Conversation) -> None:
        """Save a conversation to disk."""
        conv_path = self._get_conversation_path(conversation.id, conversation.type)
        try:
            os.makedirs(os.path.dirname(conv_path), exist_ok=True)
            with open(conv_path, "w", encoding="utf-8") as f:
                f.write(conversation.model_dump_json(indent=2))
        except Exception as e:
            print(f"Error saving conversation {conversation.id}: {e}")
    
    def _load_conversation(self, conv_path: str, conv_type: ConversationType) -> Optional[Conversation]:
        """Load a conversation from disk."""
        try:
            with open(conv_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Ensure type is correct
                data["type"] = conv_type.value
                return Conversation.model_validate(data)
        except Exception as e:
            print(f"Error loading conversation from {conv_path}: {e}")
            return None
    
    def delete_conversation(self, conv_id: str) -> bool:
        """
        Delete a conversation.
        
        Args:
            conv_id: Conversation ID.
            
        Returns:
            True if deleted successfully, False otherwise.
        """
        conversation = self._conversations.get(conv_id)
        if not conversation:
            return False
            
        # Remove from cache
        if conv_id in self._conversations:
            del self._conversations[conv_id]
            
        # Remove from disk
        conv_path = self._get_conversation_path(conv_id, conversation.type)
        if os.path.exists(conv_path):
            try:
                os.remove(conv_path)
            except Exception as e:
                print(f"Error deleting conversation file {conv_path}: {e}")
                return False
        
        # Remove from event mapping
        event_ids_to_remove = []
        for event_id, mapped_conv_id in self._event_mapping.items():
            if mapped_conv_id == conv_id:
                event_ids_to_remove.append(event_id)
        
        for event_id in event_ids_to_remove:
            del self._event_mapping[event_id]
        
        if event_ids_to_remove:
            self._save_event_mapping()
            
        return True


# Factory function to get or create a conversation manager
_manager_instance = None

def get_conversation_manager(args: AutoCoderArgs) -> ConversationManager:
    """
    Get or create a ConversationManager instance.
    
    Args:
        args: AutoCoderArgs object.
        
    Returns:
        A ConversationManager instance.
    """
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = ConversationManager(args)
    return _manager_instance 