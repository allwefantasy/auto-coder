"""
Tests for cache manager implementation.
"""
import pytest
import time
import tempfile
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from autocoder.common.conversations.cache.cache_manager import CacheManager
from autocoder.common.conversations.cache.memory_cache import MemoryCache
from autocoder.common.conversations.models import Conversation, ConversationMessage


class TestCacheManager:
    """Test cache manager implementation."""
    
    def test_cache_manager_creation(self):
        """Test cache manager creation with different configurations."""
        # Default creation
        manager = CacheManager()
        assert manager.conversation_cache is not None
        assert manager.message_cache is not None
        assert isinstance(manager.conversation_cache, MemoryCache)
        assert isinstance(manager.message_cache, MemoryCache)
        
        # Custom cache instances
        conv_cache = MemoryCache(max_size=50)
        msg_cache = MemoryCache(max_size=200)
        
        manager = CacheManager(
            conversation_cache=conv_cache,
            message_cache=msg_cache
        )
        assert manager.conversation_cache is conv_cache
        assert manager.message_cache is msg_cache
    
    def test_conversation_caching(self):
        """Test conversation caching operations."""
        manager = CacheManager()
        
        # Create test conversation
        conversation = Conversation(
            conversation_id="test_conv_1",
            name="Test Conversation",
            description="A test conversation",
            messages=[]
        )
        
        # Cache conversation
        manager.cache_conversation(conversation)
        
        # Retrieve from cache
        cached = manager.get_conversation("test_conv_1")
        assert cached is not None
        assert cached.conversation_id == "test_conv_1"
        assert cached.name == "Test Conversation"
        
        # Non-existent conversation
        assert manager.get_conversation("non_existent") is None
    
    def test_message_caching(self):
        """Test message caching operations."""
        manager = CacheManager()
        
        # Create test messages
        messages = [
            ConversationMessage(
                message_id="msg_1",
                role="user",
                content="Hello"
            ),
            ConversationMessage(
                message_id="msg_2", 
                role="assistant",
                content="Hi there!"
            )
        ]
        
        # Cache messages
        manager.cache_messages("test_conv_1", messages)
        
        # Retrieve from cache
        cached = manager.get_messages("test_conv_1")
        assert cached is not None
        assert len(cached) == 2
        assert cached[0].message_id == "msg_1"
        assert cached[1].message_id == "msg_2"
        
        # Non-existent conversation messages
        assert manager.get_messages("non_existent") is None
    
    def test_cache_invalidation(self):
        """Test cache invalidation operations."""
        manager = CacheManager()
        
        # Create and cache test data
        conversation = Conversation(
            conversation_id="test_conv_1",
            name="Test Conversation",
            messages=[]
        )
        messages = [
            ConversationMessage(
                message_id="msg_1",
                role="user", 
                content="Hello"
            )
        ]
        
        manager.cache_conversation(conversation)
        manager.cache_messages("test_conv_1", messages)
        
        # Verify cached
        assert manager.get_conversation("test_conv_1") is not None
        assert manager.get_messages("test_conv_1") is not None
        
        # Invalidate conversation
        manager.invalidate_conversation("test_conv_1")
        assert manager.get_conversation("test_conv_1") is None
        
        # Messages should still be cached
        assert manager.get_messages("test_conv_1") is not None
        
        # Invalidate messages
        manager.invalidate_messages("test_conv_1") 
        assert manager.get_messages("test_conv_1") is None
    
    def test_cache_warming(self):
        """Test cache warming functionality."""
        manager = CacheManager()
        
        # Mock data loader
        def mock_data_loader():
            return [
                Conversation(
                    conversation_id="warm_conv_1",
                    name="Warm Conversation 1", 
                    messages=[]
                ),
                Conversation(
                    conversation_id="warm_conv_2",
                    name="Warm Conversation 2",
                    messages=[]
                )
            ]
        
        # Warm cache
        result = manager.warm_conversation_cache(mock_data_loader)
        assert result == 2
        
        # Verify data is cached
        assert manager.get_conversation("warm_conv_1") is not None
        assert manager.get_conversation("warm_conv_2") is not None
        assert manager.get_conversation("warm_conv_1").name == "Warm Conversation 1"
    
    def test_cache_statistics(self):
        """Test cache statistics reporting."""
        manager = CacheManager()
        
        # Get initial stats
        stats = manager.get_cache_statistics()
        assert isinstance(stats, dict)
        assert "conversation_cache" in stats
        assert "message_cache" in stats
        
        # Each cache stats should have size info
        conv_stats = stats["conversation_cache"]
        msg_stats = stats["message_cache"]
        
        assert "size" in conv_stats
        assert "max_size" in conv_stats
        assert "size" in msg_stats
        assert "max_size" in msg_stats
        
        # Add some data and check stats update
        conversation = Conversation(
            conversation_id="stats_test",
            name="Stats Test",
            messages=[]
        )
        manager.cache_conversation(conversation)
        
        new_stats = manager.get_cache_statistics()
        assert new_stats["conversation_cache"]["size"] == 1
    
    def test_cache_clear(self):
        """Test clearing all caches."""
        manager = CacheManager()
        
        # Add data to caches
        conversation = Conversation(
            conversation_id="clear_test",
            name="Clear Test",
            messages=[]
        )
        messages = [
            ConversationMessage(
                message_id="clear_msg_1",
                role="user",
                content="Test message"
            )
        ]
        
        manager.cache_conversation(conversation)
        manager.cache_messages("clear_test", messages)
        
        # Verify data is cached
        assert manager.get_conversation("clear_test") is not None
        assert manager.get_messages("clear_test") is not None
        
        # Clear all caches
        manager.clear_all_caches()
        
        # Verify caches are empty
        assert manager.get_conversation("clear_test") is None
        assert manager.get_messages("clear_test") is None
        
        stats = manager.get_cache_statistics()
        assert stats["conversation_cache"]["size"] == 0
        assert stats["message_cache"]["size"] == 0
    
    def test_cache_key_generation(self):
        """Test cache key generation strategies."""
        manager = CacheManager()
        
        # Test conversation key generation
        conv_key = manager._get_conversation_key("test_conv_123")
        assert isinstance(conv_key, str)
        assert "test_conv_123" in conv_key
        
        # Test message key generation
        msg_key = manager._get_messages_key("test_conv_123")
        assert isinstance(msg_key, str)
        assert "test_conv_123" in msg_key
        
        # Keys should be different
        assert conv_key != msg_key
        
        # Same input should generate same key
        assert manager._get_conversation_key("test_conv_123") == conv_key
        assert manager._get_messages_key("test_conv_123") == msg_key
    
    def test_cache_error_handling(self):
        """Test error handling in cache operations."""
        # Create manager with mock cache that raises errors
        mock_cache = Mock()
        mock_cache.get.side_effect = Exception("Cache error")
        mock_cache.set.side_effect = Exception("Cache error")
        mock_cache.delete.side_effect = Exception("Cache error")
        mock_cache.size.return_value = 0
        mock_cache.max_size = 100
        
        manager = CacheManager(
            conversation_cache=mock_cache,
            message_cache=mock_cache
        )
        
        conversation = Conversation(
            conversation_id="error_test",
            name="Error Test",
            messages=[]
        )
        
        # Cache operations should handle errors gracefully
        manager.cache_conversation(conversation)  # Should not raise
        assert manager.get_conversation("error_test") is None  # Should not raise
        manager.invalidate_conversation("error_test")  # Should not raise
    
    def test_bulk_operations(self):
        """Test bulk cache operations."""
        manager = CacheManager()
        
        # Create multiple conversations
        conversations = []
        for i in range(10):
            conv = Conversation(
                conversation_id=f"bulk_conv_{i}",
                name=f"Bulk Conversation {i}",
                messages=[]
            )
            conversations.append(conv)
        
        # Bulk cache
        result = manager.cache_conversations(conversations)
        assert result == 10
        
        # Verify all are cached
        for conv in conversations:
            cached = manager.get_conversation(conv.conversation_id)
            assert cached is not None
            assert cached.name == conv.name
        
        # Bulk invalidation
        conv_ids = [conv.conversation_id for conv in conversations[:5]]
        results = manager.invalidate_conversations(conv_ids)
        
        # Check results
        for conv_id in conv_ids:
            assert results[conv_id] is True
        
        # First 5 should be invalidated
        for i in range(5):
            assert manager.get_conversation(f"bulk_conv_{i}") is None
        
        # Rest should still be cached
        for i in range(5, 10):
            assert manager.get_conversation(f"bulk_conv_{i}") is not None
    
    def test_is_cached_methods(self):
        """Test methods to check if items are cached."""
        manager = CacheManager()
        
        # Initially nothing is cached
        assert manager.is_conversation_cached("test_conv") is False
        assert manager.is_messages_cached("test_conv") is False
        
        # Cache conversation
        conversation = Conversation(
            conversation_id="test_conv",
            name="Test",
            messages=[]
        )
        manager.cache_conversation(conversation)
        
        assert manager.is_conversation_cached("test_conv") is True
        assert manager.is_messages_cached("test_conv") is False
        
        # Cache messages
        messages = [
            ConversationMessage(
                message_id="msg_1",
                role="user",
                content="Hello"
            )
        ]
        manager.cache_messages("test_conv", messages)
        
        assert manager.is_conversation_cached("test_conv") is True
        assert manager.is_messages_cached("test_conv") is True
    
    def test_get_cached_conversation_ids(self):
        """Test getting list of cached conversation IDs."""
        manager = CacheManager()
        
        # Initially empty
        assert manager.get_cached_conversation_ids() == []
        
        # Cache some conversations
        for i in range(3):
            conv = Conversation(
                conversation_id=f"conv_{i}",
                name=f"Conversation {i}",
                messages=[]
            )
            manager.cache_conversation(conv)
        
        # Should return all conversation IDs
        cached_ids = manager.get_cached_conversation_ids()
        assert len(cached_ids) == 3
        assert "conv_0" in cached_ids
        assert "conv_1" in cached_ids
        assert "conv_2" in cached_ids
    
    def test_invalidate_all(self):
        """Test invalidating all data for a conversation."""
        manager = CacheManager()
        
        # Cache both conversation and messages
        conversation = Conversation(
            conversation_id="test_conv",
            name="Test",
            messages=[]
        )
        messages = [
            ConversationMessage(
                message_id="msg_1",
                role="user",
                content="Hello"
            )
        ]
        
        manager.cache_conversation(conversation)
        manager.cache_messages("test_conv", messages)
        
        # Verify both are cached
        assert manager.get_conversation("test_conv") is not None
        assert manager.get_messages("test_conv") is not None
        
        # Invalidate all
        results = manager.invalidate_all("test_conv")
        
        # Check results
        assert results["conversation"] is True
        assert results["messages"] is True
        
        # Verify both are invalidated
        assert manager.get_conversation("test_conv") is None
        assert manager.get_messages("test_conv") is None
    
    def test_cache_configuration_validation(self):
        """Test validation of cache configuration."""
        # Valid configuration should work
        manager = CacheManager()
        assert manager is not None
        
        # Invalid cache types should raise errors
        with pytest.raises((TypeError, AttributeError)):
            CacheManager(conversation_cache="invalid")
        
        with pytest.raises((TypeError, AttributeError)):
            CacheManager(message_cache="invalid") 