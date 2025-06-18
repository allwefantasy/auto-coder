"""
Cache manager for conversation and message caching.

This module provides a high-level interface for managing caches of
conversations and messages, with support for cache warming, invalidation,
and statistics reporting.
"""

import logging
from typing import Optional, List, Dict, Any, Callable

from .base_cache import BaseCache
from .memory_cache import MemoryCache
from ..models import Conversation, ConversationMessage

logger = logging.getLogger(__name__)


class CacheManager:
    """High-level cache manager for conversations and messages."""
    
    def __init__(
        self,
        conversation_cache: Optional[BaseCache] = None,
        message_cache: Optional[BaseCache] = None
    ):
        """
        Initialize cache manager.
        
        Args:
            conversation_cache: Cache instance for conversations
            message_cache: Cache instance for messages
        """
        self.conversation_cache = conversation_cache or MemoryCache(
            max_size=100, default_ttl=600.0  # 10 minutes default
        )
        self.message_cache = message_cache or MemoryCache(
            max_size=500, default_ttl=300.0  # 5 minutes default  
        )
        
        # Ensure caches implement required interface
        self._validate_cache_interface(self.conversation_cache)
        self._validate_cache_interface(self.message_cache)
    
    def _validate_cache_interface(self, cache: BaseCache) -> None:
        """Validate that cache implements required interface."""
        required_methods = ['get', 'set', 'delete', 'clear', 'exists', 'size', 'keys']
        for method in required_methods:
            if not hasattr(cache, method) or not callable(getattr(cache, method)):
                raise TypeError(f"Cache must implement {method} method")
    
    def _get_conversation_key(self, conversation_id: str) -> str:
        """Generate cache key for conversation."""
        return f"conv:{conversation_id}"
    
    def _get_messages_key(self, conversation_id: str) -> str:
        """Generate cache key for conversation messages."""
        return f"msgs:{conversation_id}"
    
    def cache_conversation(
        self, 
        conversation: Conversation,
        ttl: Optional[float] = None
    ) -> None:
        """
        Cache a conversation.
        
        Args:
            conversation: The conversation to cache
            ttl: Time to live in seconds, None for default
        """
        try:
            key = self._get_conversation_key(conversation.conversation_id)
            self.conversation_cache.set(key, conversation, ttl=ttl)
            logger.debug(f"Cached conversation {conversation.conversation_id}")
        except Exception as e:
            logger.error(f"Failed to cache conversation {conversation.conversation_id}: {e}")
    
    def get_conversation(self, conversation_id: str) -> Optional[Conversation]:
        """
        Get a conversation from cache.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            The cached conversation or None if not found
        """
        try:
            key = self._get_conversation_key(conversation_id)
            conversation = self.conversation_cache.get(key)
            if conversation:
                logger.debug(f"Cache hit for conversation {conversation_id}")
            else:
                logger.debug(f"Cache miss for conversation {conversation_id}")
            return conversation
        except Exception as e:
            logger.error(f"Failed to get conversation {conversation_id} from cache: {e}")
            return None
    
    def cache_messages(
        self,
        conversation_id: str,
        messages: List[ConversationMessage],
        ttl: Optional[float] = None
    ) -> None:
        """
        Cache messages for a conversation.
        
        Args:
            conversation_id: The conversation ID
            messages: List of messages to cache
            ttl: Time to live in seconds, None for default
        """
        try:
            key = self._get_messages_key(conversation_id)
            self.message_cache.set(key, messages, ttl=ttl)
            logger.debug(f"Cached {len(messages)} messages for conversation {conversation_id}")
        except Exception as e:
            logger.error(f"Failed to cache messages for conversation {conversation_id}: {e}")
    
    def get_messages(self, conversation_id: str) -> Optional[List[ConversationMessage]]:
        """
        Get messages from cache.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            List of cached messages or None if not found
        """
        try:
            key = self._get_messages_key(conversation_id) 
            messages = self.message_cache.get(key)
            if messages:
                logger.debug(f"Cache hit for messages of conversation {conversation_id}")
            else:
                logger.debug(f"Cache miss for messages of conversation {conversation_id}")
            return messages
        except Exception as e:
            logger.error(f"Failed to get messages for conversation {conversation_id} from cache: {e}")
            return None
    
    def invalidate_conversation(self, conversation_id: str) -> bool:
        """
        Invalidate cached conversation.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            True if conversation was cached and removed, False otherwise
        """
        try:
            key = self._get_conversation_key(conversation_id)
            result = self.conversation_cache.delete(key)
            if result:
                logger.debug(f"Invalidated conversation {conversation_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to invalidate conversation {conversation_id}: {e}")
            return False
    
    def invalidate_messages(self, conversation_id: str) -> bool:
        """
        Invalidate cached messages.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            True if messages were cached and removed, False otherwise
        """
        try:
            key = self._get_messages_key(conversation_id)
            result = self.message_cache.delete(key)
            if result:
                logger.debug(f"Invalidated messages for conversation {conversation_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to invalidate messages for conversation {conversation_id}: {e}")
            return False
    
    def invalidate_all(self, conversation_id: str) -> Dict[str, bool]:
        """
        Invalidate all cached data for a conversation.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            Dictionary with invalidation results
        """
        return {
            "conversation": self.invalidate_conversation(conversation_id),
            "messages": self.invalidate_messages(conversation_id)
        }
    
    def warm_conversation_cache(
        self, 
        data_loader: Callable[[], List[Conversation]]
    ) -> int:
        """
        Warm conversation cache with data.
        
        Args:
            data_loader: Function that returns conversations to cache
            
        Returns:
            Number of conversations cached
        """
        try:
            conversations = data_loader()
            count = 0
            
            for conversation in conversations:
                self.cache_conversation(conversation)
                count += 1
            
            logger.info(f"Warmed conversation cache with {count} conversations")
            return count
            
        except Exception as e:
            logger.error(f"Failed to warm conversation cache: {e}")
            return 0
    
    def cache_conversations(
        self, 
        conversations: List[Conversation],
        ttl: Optional[float] = None
    ) -> int:
        """
        Cache multiple conversations.
        
        Args:
            conversations: List of conversations to cache
            ttl: Time to live in seconds, None for default
            
        Returns:
            Number of conversations successfully cached
        """
        count = 0
        for conversation in conversations:
            try:
                self.cache_conversation(conversation, ttl=ttl)
                count += 1
            except Exception as e:
                logger.error(f"Failed to cache conversation {conversation.conversation_id}: {e}")
        
        return count
    
    def invalidate_conversations(self, conversation_ids: List[str]) -> Dict[str, bool]:
        """
        Invalidate multiple conversations.
        
        Args:
            conversation_ids: List of conversation IDs to invalidate
            
        Returns:
            Dictionary mapping conversation IDs to invalidation results
        """
        results = {}
        for conversation_id in conversation_ids:
            results[conversation_id] = self.invalidate_conversation(conversation_id)
        
        return results
    
    def clear_all_caches(self) -> None:
        """Clear all caches."""
        try:
            self.conversation_cache.clear()
            self.message_cache.clear()
            logger.info("Cleared all caches")
        except Exception as e:
            logger.error(f"Failed to clear caches: {e}")
    
    def get_cache_statistics(self) -> Dict[str, Any]:
        """
        Get statistics for all caches.
        
        Returns:
            Dictionary with cache statistics
        """
        try:
            stats = {
                "conversation_cache": {
                    "size": self.conversation_cache.size(),
                    "max_size": getattr(self.conversation_cache, 'max_size', 'unknown')
                },
                "message_cache": {
                    "size": self.message_cache.size(),
                    "max_size": getattr(self.message_cache, 'max_size', 'unknown')
                }
            }
            
            # Add detailed stats if available
            if hasattr(self.conversation_cache, 'get_statistics'):
                stats["conversation_cache"].update(
                    self.conversation_cache.get_statistics()
                )
            
            if hasattr(self.message_cache, 'get_statistics'):
                stats["message_cache"].update(
                    self.message_cache.get_statistics()
                )
            
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get cache statistics: {e}")
            return {
                "conversation_cache": {"size": 0, "max_size": "unknown"},
                "message_cache": {"size": 0, "max_size": "unknown"},
                "error": str(e)
            }
    
    def is_conversation_cached(self, conversation_id: str) -> bool:
        """
        Check if a conversation is cached.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            True if conversation is cached, False otherwise
        """
        try:
            key = self._get_conversation_key(conversation_id)
            return self.conversation_cache.exists(key)
        except Exception as e:
            logger.error(f"Failed to check if conversation {conversation_id} is cached: {e}")
            return False
    
    def is_messages_cached(self, conversation_id: str) -> bool:
        """
        Check if messages are cached.
        
        Args:
            conversation_id: The conversation ID
            
        Returns:
            True if messages are cached, False otherwise
        """
        try:
            key = self._get_messages_key(conversation_id)
            return self.message_cache.exists(key)
        except Exception as e:
            logger.error(f"Failed to check if messages for conversation {conversation_id} are cached: {e}")
            return False
    
    def get_cached_conversation_ids(self) -> List[str]:
        """
        Get all cached conversation IDs.
        
        Returns:
            List of conversation IDs currently cached
        """
        try:
            keys = self.conversation_cache.keys()
            # Extract conversation IDs from cache keys
            conversation_ids = []
            for key in keys:
                if key.startswith("conv:"):
                    conversation_ids.append(key[5:])  # Remove "conv:" prefix
            return conversation_ids
        except Exception as e:
            logger.error(f"Failed to get cached conversation IDs: {e}")
            return [] 