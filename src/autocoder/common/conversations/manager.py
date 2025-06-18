"""
Main conversation manager that integrates all subsystems.

This module provides the PersistConversationManager class, which serves as
the primary interface for conversation and message management, integrating
storage, caching, search, and filtering capabilities.
"""

import os
import time
import uuid
import contextlib
from typing import List, Dict, Any, Optional, Union, Generator, Tuple
from pathlib import Path

from .config import ConversationManagerConfig
from .exceptions import (
    ConversationManagerError,
    ConversationNotFoundError,
    MessageNotFoundError,
    ConcurrencyError,
    DataIntegrityError
)
from .models import Conversation, ConversationMessage
from .file_locker import FileLocker
from .storage import FileStorage, IndexManager
from .cache import CacheManager
from .search import TextSearcher, FilterManager


class PersistConversationManager:
    """
    Main conversation manager integrating all subsystems.
    
    This class provides a unified interface for conversation and message management,
    with integrated storage, caching, search, and filtering capabilities.
    """
    
    def __init__(self, config: Optional[ConversationManagerConfig] = None):
        """
        Initialize the conversation manager.
        
        Args:
            config: Configuration object for the manager
        """
        self.config = config or ConversationManagerConfig()
        
        # Initialize components
        self._init_storage()
        self._init_cache()
        self._init_search()
        self._init_locks()
        
        # Statistics tracking
        self._stats = {
            'conversations_created': 0,
            'conversations_loaded': 0,
            'messages_added': 0,
            'cache_hits': 0,
            'cache_misses': 0
        }
    
    def _init_storage(self):
        """Initialize storage components."""
        # Ensure storage directory exists
        storage_path = Path(self.config.storage_path)
        storage_path.mkdir(parents=True, exist_ok=True)
        
        # Initialize storage backend
        self.storage = FileStorage(str(storage_path / "conversations"))
        
        # Initialize index manager
        self.index_manager = IndexManager(str(storage_path / "index"))
    
    def _init_cache(self):
        """Initialize cache system."""
        from .cache import MemoryCache
        
        # Use simple dictionary-based caching for conversations and messages
        self.conversation_cache = MemoryCache(
            max_size=self.config.max_cache_size,
            default_ttl=self.config.cache_ttl
        )
        self.message_cache = MemoryCache(
            max_size=self.config.max_cache_size * 10,  # More messages than conversations
            default_ttl=self.config.cache_ttl
        )
    
    def _init_search(self):
        """Initialize search and filtering systems."""
        self.text_searcher = TextSearcher()
        self.filter_manager = FilterManager()
    
    def _init_locks(self):
        """Initialize locking system."""
        lock_dir = Path(self.config.storage_path) / "locks"
        lock_dir.mkdir(parents=True, exist_ok=True)
        self._lock_dir = str(lock_dir)
    
    def _get_conversation_lock_file(self, conversation_id: str) -> str:
        """Get lock file path for a conversation."""
        return os.path.join(self._lock_dir, f"{conversation_id}.lock")
    
    @contextlib.contextmanager
    def _conversation_lock(self, conversation_id: str, exclusive: bool = True) -> Generator[None, None, None]:
        """
        Acquire lock for conversation operations.
        
        Args:
            conversation_id: ID of the conversation to lock
            exclusive: Whether to acquire exclusive (write) lock
        """
        lock_file = self._get_conversation_lock_file(conversation_id)
        locker = FileLocker(lock_file, timeout=self.config.lock_timeout)
        
        try:
            if exclusive:
                with locker.acquire_write_lock():
                    yield
            else:
                with locker.acquire_read_lock():
                    yield
        except (ConversationNotFoundError, MessageNotFoundError):
            # Re-raise these exceptions as-is (don't wrap in ConcurrencyError)
            raise
        except Exception as e:
            raise ConcurrencyError(f"Failed to acquire lock for conversation {conversation_id}: {e}")
    
    # Conversation Management Methods
    
    def create_conversation(
        self,
        name: str,
        description: Optional[str] = None,
        initial_messages: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a new conversation.
        
        Args:
            name: Name of the conversation
            description: Optional description
            initial_messages: Optional list of initial messages
            metadata: Optional metadata dictionary
            
        Returns:
            ID of the created conversation
            
        Raises:
            ConversationManagerError: If conversation creation fails
        """
        try:
            # Create conversation object
            conversation = Conversation(
                name=name,
                description=description,
                metadata=metadata or {}
            )
            
            # Add initial messages if provided
            if initial_messages:
                for msg_data in initial_messages:
                    message = ConversationMessage(
                        role=msg_data['role'],
                        content=msg_data['content'],
                        metadata=msg_data.get('metadata', {})
                    )
                    conversation.add_message(message)
            
            # Save conversation with locking
            with self._conversation_lock(conversation.conversation_id):
                # Save to storage
                self.storage.save_conversation(conversation.to_dict())
                
                # Update index
                self.index_manager.add_conversation(conversation.to_dict())
                
                # Cache the conversation
                self.conversation_cache.set(conversation.conversation_id, conversation.to_dict())
            
            # Update statistics
            self._stats['conversations_created'] += 1
            
            return conversation.conversation_id
            
        except Exception as e:
            raise ConversationManagerError(f"Failed to create conversation: {e}")
    
    def get_conversation(self, conversation_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a conversation by ID.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Conversation data or None if not found
        """
        try:
            # Try cache first
            cached_conversation = self.conversation_cache.get(conversation_id)
            if cached_conversation:
                self._stats['cache_hits'] += 1
                return cached_conversation
            
            self._stats['cache_misses'] += 1
            
            # Load from storage with read lock
            with self._conversation_lock(conversation_id, exclusive=False):
                conversation_data = self.storage.load_conversation(conversation_id)
                
                if conversation_data:
                    # Cache the loaded conversation
                    self.conversation_cache.set(conversation_id, conversation_data)
                    self._stats['conversations_loaded'] += 1
                    return conversation_data
                
                return None
                
        except Exception as e:
            raise ConversationManagerError(f"Failed to get conversation {conversation_id}: {e}")
    
    def update_conversation(
        self,
        conversation_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update conversation metadata.
        
        Args:
            conversation_id: ID of the conversation to update
            name: New name (optional)
            description: New description (optional)
            metadata: New metadata (optional)
            
        Returns:
            True if update was successful
            
        Raises:
            ConversationNotFoundError: If conversation doesn't exist
        """
        try:
            with self._conversation_lock(conversation_id):
                # Load current conversation
                conversation_data = self.storage.load_conversation(conversation_id)
                if not conversation_data:
                    raise ConversationNotFoundError(conversation_id)
                
                # Create conversation object and update fields
                conversation = Conversation.from_dict(conversation_data)
                
                if name is not None:
                    conversation.name = name
                if description is not None:
                    conversation.description = description
                if metadata is not None:
                    conversation.metadata.update(metadata)
                
                conversation.updated_at = time.time()
                
                # Save updated conversation
                updated_data = conversation.to_dict()
                self.storage.save_conversation(updated_data)
                
                # Update index
                self.index_manager.update_conversation(updated_data)
                
                # Update cache
                self.conversation_cache.set(conversation_id, updated_data)
                
                return True
                
        except ConversationNotFoundError:
            raise
        except Exception as e:
            raise ConversationManagerError(f"Failed to update conversation {conversation_id}: {e}")
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """
        Delete a conversation.
        
        Args:
            conversation_id: ID of the conversation to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            with self._conversation_lock(conversation_id):
                # Check if conversation exists
                if not self.storage.conversation_exists(conversation_id):
                    return False
                
                # Delete from storage
                self.storage.delete_conversation(conversation_id)
                
                # Remove from index
                self.index_manager.remove_conversation(conversation_id)
                
                # Remove from cache
                self.conversation_cache.delete(conversation_id)
                
                return True
                
        except Exception as e:
            raise ConversationManagerError(f"Failed to delete conversation {conversation_id}: {e}")
    
    def list_conversations(
        self,
        limit: Optional[int] = None,
        offset: int = 0,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = 'updated_at',
        sort_desc: bool = True
    ) -> List[Dict[str, Any]]:
        """
        List conversations with optional filtering and sorting.
        
        Args:
            limit: Maximum number of conversations to return
            offset: Number of conversations to skip
            filters: Optional filter criteria
            sort_by: Field to sort by
            sort_desc: Whether to sort in descending order
            
        Returns:
            List of conversation data
        """
        try:
            # Get conversations from index
            conversations = self.index_manager.list_conversations()
            
            # Apply filters if provided
            if filters:
                conversations = self.filter_manager.apply_filters(conversations, filters)
            
            # Sort conversations
            conversations = self.index_manager.sort_conversations(
                conversations, sort_by, sort_desc
            )
            
            # Apply pagination
            end_idx = offset + limit if limit else None
            return conversations[offset:end_idx]
            
        except Exception as e:
            raise ConversationManagerError(f"Failed to list conversations: {e}")
    
    # Message Management Methods
    
    def append_message(
        self,
        conversation_id: str,
        role: str,
        content: Union[str, Dict[str, Any], List[Any]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Append a message to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            role: Role of the message sender
            content: Message content
            metadata: Optional message metadata
            
        Returns:
            ID of the added message
            
        Raises:
            ConversationNotFoundError: If conversation doesn't exist
        """
        try:
            # Create message object
            message = ConversationMessage(
                role=role,
                content=content,
                metadata=metadata or {}
            )
            
            with self._conversation_lock(conversation_id):
                # Load conversation
                conversation_data = self.storage.load_conversation(conversation_id)
                if not conversation_data:
                    raise ConversationNotFoundError(conversation_id)
                
                # Add message to conversation
                conversation = Conversation.from_dict(conversation_data)
                conversation.add_message(message)
                
                # Save updated conversation
                updated_data = conversation.to_dict()
                self.storage.save_conversation(updated_data)
                
                # Update index
                self.index_manager.update_conversation(updated_data)
                
                # Update cache
                self.conversation_cache.set(conversation_id, updated_data)
                self.message_cache.set(f"{conversation_id}:{message.message_id}", message.to_dict())
            
            # Update statistics
            self._stats['messages_added'] += 1
            
            return message.message_id
            
        except ConversationNotFoundError:
            raise
        except Exception as e:
            raise ConversationManagerError(f"Failed to append message to conversation {conversation_id}: {e}")
    
    def append_messages(
        self,
        conversation_id: str,
        messages: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Append multiple messages to a conversation.
        
        Args:
            conversation_id: ID of the conversation
            messages: List of message data dictionaries
            
        Returns:
            List of message IDs
        """
        message_ids = []
        
        for msg_data in messages:
            message_id = self.append_message(
                conversation_id,
                msg_data['role'],
                msg_data['content'],
                msg_data.get('metadata')
            )
            message_ids.append(message_id)
        
        return message_ids
    
    def get_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0,
        message_ids: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Get messages from a conversation.
        
        Args:
            conversation_id: ID of the conversation
            limit: Maximum number of messages to return
            offset: Number of messages to skip
            message_ids: Optional list of specific message IDs
            
        Returns:
            List of message data
        """
        try:
            # Get conversation
            conversation_data = self.get_conversation(conversation_id)
            if not conversation_data:
                raise ConversationNotFoundError(conversation_id)
            
            messages = conversation_data.get('messages', [])
            
            # Filter by message IDs if provided
            if message_ids:
                id_set = set(message_ids)
                messages = [msg for msg in messages if msg.get('message_id') in id_set]
            
            # Apply pagination
            end_idx = offset + limit if limit else None
            return messages[offset:end_idx]
            
        except ConversationNotFoundError:
            raise
        except Exception as e:
            raise ConversationManagerError(f"Failed to get messages from conversation {conversation_id}: {e}")
    
    def get_message(
        self,
        conversation_id: str,
        message_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get a specific message.
        
        Args:
            conversation_id: ID of the conversation
            message_id: ID of the message
            
        Returns:
            Message data or None if not found
        """
        try:
            # Try cache first
            cached_message = self.message_cache.get(f"{conversation_id}:{message_id}")
            if cached_message:
                return cached_message
            
            # Get from conversation
            conversation_data = self.get_conversation(conversation_id)
            if not conversation_data:
                return None
            
            # Find message
            for message in conversation_data.get('messages', []):
                if message.get('message_id') == message_id:
                    # Cache the message
                    self.message_cache.set(f"{conversation_id}:{message_id}", message)
                    return message
            
            return None
            
        except Exception as e:
            raise ConversationManagerError(f"Failed to get message {message_id}: {e}")
    
    def update_message(
        self,
        conversation_id: str,
        message_id: str,
        content: Optional[Union[str, Dict[str, Any], List[Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Update a message.
        
        Args:
            conversation_id: ID of the conversation
            message_id: ID of the message to update
            content: New content (optional)
            metadata: New metadata (optional)
            
        Returns:
            True if update was successful
        """
        try:
            with self._conversation_lock(conversation_id):
                # Load conversation
                conversation_data = self.storage.load_conversation(conversation_id)
                if not conversation_data:
                    raise ConversationNotFoundError(conversation_id)
                
                conversation = Conversation.from_dict(conversation_data)
                
                # Find and update message
                for i, message_data in enumerate(conversation.messages):
                    msg = ConversationMessage.from_dict(message_data)
                    if msg.message_id == message_id:
                        # Update message fields
                        if content is not None:
                            msg.content = content
                        if metadata is not None:
                            msg.metadata.update(metadata)
                        
                        # Update timestamp
                        msg.timestamp = time.time()
                        
                        # Replace in conversation
                        conversation.messages[i] = msg.to_dict()
                        conversation.updated_at = time.time()
                        
                        # Save updated conversation
                        updated_data = conversation.to_dict()
                        self.storage.save_conversation(updated_data)
                        
                        # Update index
                        self.index_manager.update_conversation(updated_data)
                        
                        # Update caches
                        self.conversation_cache.set(conversation_id, updated_data)
                        self.message_cache.set(f"{conversation_id}:{message_id}", msg.to_dict())
                        
                        return True
                
                raise MessageNotFoundError(message_id)
                
        except (ConversationNotFoundError, MessageNotFoundError):
            raise
        except Exception as e:
            raise ConversationManagerError(f"Failed to update message {message_id}: {e}")
    
    def delete_message(
        self,
        conversation_id: str,
        message_id: str
    ) -> bool:
        """
        Delete a message from a conversation.
        
        Args:
            conversation_id: ID of the conversation
            message_id: ID of the message to delete
            
        Returns:
            True if deletion was successful
        """
        try:
            with self._conversation_lock(conversation_id):
                # Load conversation
                conversation_data = self.storage.load_conversation(conversation_id)
                if not conversation_data:
                    raise ConversationNotFoundError(conversation_id)
                
                conversation = Conversation.from_dict(conversation_data)
                
                # Find and remove message
                original_count = len(conversation.messages)
                conversation.messages = [
                    msg for msg in conversation.messages
                    if msg.get('message_id') != message_id
                ]
                
                if len(conversation.messages) == original_count:
                    raise MessageNotFoundError(message_id)
                
                conversation.updated_at = time.time()
                
                # Save updated conversation
                updated_data = conversation.to_dict()
                self.storage.save_conversation(updated_data)
                
                # Update index
                self.index_manager.update_conversation(updated_data)
                
                # Update caches
                self.conversation_cache.set(conversation_id, updated_data)
                self.message_cache.delete(f"{conversation_id}:{message_id}")
                
                return True
                
        except (ConversationNotFoundError, MessageNotFoundError):
            raise
        except Exception as e:
            raise ConversationManagerError(f"Failed to delete message {message_id}: {e}")
    
    def delete_message_pair(
        self,
        conversation_id: str,
        user_message_id: str
    ) -> bool:
        """
        Delete a user message and its corresponding assistant reply.
        
        Args:
            conversation_id: ID of the conversation
            user_message_id: ID of the user message
            
        Returns:
            True if deletion was successful
        """
        try:
            with self._conversation_lock(conversation_id):
                # Load conversation
                conversation_data = self.storage.load_conversation(conversation_id)
                if not conversation_data:
                    raise ConversationNotFoundError(conversation_id)
                
                conversation = Conversation.from_dict(conversation_data)
                
                # Find user message and next assistant message
                messages_to_remove = []
                for i, message in enumerate(conversation.messages):
                    if message.get('message_id') == user_message_id:
                        messages_to_remove.append(i)
                        # Check if next message is assistant reply
                        if (i + 1 < len(conversation.messages) and
                            conversation.messages[i + 1].get('role') == 'assistant'):
                            messages_to_remove.append(i + 1)
                        break
                
                if not messages_to_remove:
                    raise MessageNotFoundError(user_message_id)
                
                # Remove messages (in reverse order to maintain indices)
                assistant_message_id = None
                for idx in reversed(messages_to_remove):
                    if idx == messages_to_remove[-1] and len(messages_to_remove) > 1:
                        assistant_message_id = conversation.messages[idx].get('message_id')
                    del conversation.messages[idx]
                
                conversation.updated_at = time.time()
                
                # Save updated conversation
                updated_data = conversation.to_dict()
                self.storage.save_conversation(updated_data)
                
                # Update index
                self.index_manager.update_conversation(updated_data)
                
                # Update caches
                self.conversation_cache.set(conversation_id, updated_data)
                self.message_cache.delete(f"{conversation_id}:{user_message_id}")
                if assistant_message_id:
                    self.message_cache.delete(f"{conversation_id}:{assistant_message_id}")
                
                return True
                
        except (ConversationNotFoundError, MessageNotFoundError):
            raise
        except Exception as e:
            raise ConversationManagerError(f"Failed to delete message pair {user_message_id}: {e}")
    
    # Search and Filter Methods
    
    def search_conversations(
        self,
        query: str,
        search_in_messages: bool = True,
        filters: Optional[Dict[str, Any]] = None,
        max_results: Optional[int] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search conversations.
        
        Args:
            query: Search query
            search_in_messages: Whether to search in message content
            filters: Optional filter criteria
            max_results: Maximum number of results
            min_score: Minimum relevance score
            
        Returns:
            List of matching conversations with scores
        """
        try:
            # Get all conversations
            conversations = self.index_manager.list_conversations()
            
            # Apply filters first if provided
            if filters:
                conversations = self.filter_manager.apply_filters(conversations, filters)
            
            # If search_in_messages is True, load full conversation data
            if search_in_messages:
                full_conversations = []
                for conv in conversations:
                    conv_id = conv.get('conversation_id')
                    if conv_id:
                        full_conv = self.get_conversation(conv_id)
                        if full_conv:
                            full_conversations.append(full_conv)
                conversations = full_conversations
            
            # Perform text search
            results = self.text_searcher.search_conversations(
                query, conversations, max_results, min_score
            )
            
            return [{'conversation': conv, 'score': score} for conv, score in results]
            
        except Exception as e:
            raise ConversationManagerError(f"Failed to search conversations: {e}")
    
    def search_messages(
        self,
        conversation_id: str,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
        max_results: Optional[int] = None,
        min_score: float = 0.0
    ) -> List[Dict[str, Any]]:
        """
        Search messages in a conversation.
        
        Args:
            conversation_id: ID of the conversation
            query: Search query
            filters: Optional filter criteria
            max_results: Maximum number of results
            min_score: Minimum relevance score
            
        Returns:
            List of matching messages with scores
        """
        try:
            # Get conversation messages
            messages = self.get_messages(conversation_id)
            
            # Apply filters if provided
            if filters:
                messages = self.filter_manager.apply_filters(messages, filters)
            
            # Perform text search
            results = self.text_searcher.search_messages(
                query, messages, max_results, min_score
            )
            
            return [{'message': msg, 'score': score} for msg, score in results]
            
        except Exception as e:
            raise ConversationManagerError(f"Failed to search messages: {e}")
    
    # Utility and Management Methods
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get manager statistics.
        
        Returns:
            Dictionary with statistics
        """
        cache_stats = {
            'conversation_cache_size': self.conversation_cache.size(),
            'message_cache_size': self.message_cache.size()
        }
        
        return {
            **self._stats,
            'cache_stats': cache_stats,
            'total_conversations': len(self.index_manager.list_conversations()),
            'storage_path': self.config.storage_path
        }
    
    def health_check(self) -> Dict[str, Any]:
        """
        Perform health check of all components.
        
        Returns:
            Health status dictionary
        """
        health_status = {
            'status': 'healthy',
            'storage': True,
            'cache': True,
            'index': True,
            'search': True,
            'issues': []
        }
        
        try:
            # Check storage
            if not os.path.exists(self.config.storage_path):
                health_status['storage'] = False
                health_status['issues'].append('Storage directory not accessible')
            
            # Check cache
            conv_cache_size = self.conversation_cache.size()
            if conv_cache_size > self.config.max_cache_size:
                health_status['issues'].append('Conversation cache size exceeds limit')
            
            # Check index consistency
            try:
                conversations = self.index_manager.list_conversations()
                health_status['total_conversations'] = len(conversations)
            except Exception as e:
                health_status['index'] = False
                health_status['issues'].append(f'Index error: {e}')
            
            # Determine overall status
            if not all([health_status['storage'], health_status['cache'], 
                       health_status['index'], health_status['search']]):
                health_status['status'] = 'degraded'
            
            if health_status['issues']:
                health_status['status'] = 'warning' if health_status['status'] == 'healthy' else health_status['status']
                
        except Exception as e:
            health_status['status'] = 'unhealthy'
            health_status['issues'].append(f'Health check failed: {e}')
        
        return health_status
    
    @contextlib.contextmanager
    def transaction(self, conversation_id: str) -> Generator[None, None, None]:
        """
        Transaction context manager for atomic operations.
        
        Args:
            conversation_id: ID of the conversation for the transaction
        """
        with self._conversation_lock(conversation_id):
            try:
                yield
            except Exception:
                # In a full implementation, we would rollback changes here
                # For now, we just re-raise the exception
                raise
    
    def clear_cache(self):
        """Clear all caches."""
        self.conversation_cache.clear()
        self.message_cache.clear()
    
    def rebuild_index(self):
        """Rebuild the conversation index from storage."""
        try:
            # Clear existing index
            self.index_manager._index.clear()
            
            # Load all conversations from storage and rebuild index
            conversation_ids = self.storage.list_conversations()
            
            for conv_id in conversation_ids:
                conversation_data = self.storage.load_conversation(conv_id)
                if conversation_data:
                    self.index_manager.add_conversation(conversation_data)
            
        except Exception as e:
            raise ConversationManagerError(f"Failed to rebuild index: {e}")
    
    def close(self):
        """Clean up resources."""
        # Clear caches
        self.clear_cache()
        
        # Save any pending index changes
        try:
            self.index_manager._save_index()
        except Exception:
            pass  # Ignore errors during cleanup 