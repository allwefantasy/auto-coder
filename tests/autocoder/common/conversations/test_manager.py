"""
Tests for the main conversation manager.

This module provides comprehensive tests for the PersistConversationManager class,
testing all conversation and message management functionality.
"""

import pytest
import tempfile
import shutil
import time
from pathlib import Path
from typing import Dict, Any, List

from src.autocoder.common.conversations.manager import PersistConversationManager
from src.autocoder.common.conversations.config import ConversationManagerConfig
from src.autocoder.common.conversations.exceptions import (
    ConversationNotFoundError,
    MessageNotFoundError,
    ConversationManagerError
)


class TestPersistConversationManager:
    """Test cases for PersistConversationManager."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create a temporary directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)
    
    @pytest.fixture
    def config(self, temp_dir):
        """Create test configuration."""
        return ConversationManagerConfig(
            storage_path=temp_dir,
            max_cache_size=10,
            cache_ttl=300.0,
            lock_timeout=5.0
        )
    
    @pytest.fixture
    def manager(self, config):
        """Create manager instance for testing."""
        manager = PersistConversationManager(config)
        yield manager
        manager.close()
    
    def test_manager_initialization(self, config):
        """Test manager initialization."""
        manager = PersistConversationManager(config)
        
        # Check that all components are initialized
        assert manager.config == config
        assert manager.storage is not None
        assert manager.index_manager is not None
        assert manager.conversation_cache is not None
        assert manager.message_cache is not None
        assert manager.text_searcher is not None
        assert manager.filter_manager is not None
        
        # Check storage directories are created
        storage_path = Path(config.storage_path)
        assert storage_path.exists()
        assert (storage_path / "conversations").exists()
        assert (storage_path / "index").exists()
        assert (storage_path / "locks").exists()
        
        manager.close()
    
    def test_create_conversation(self, manager):
        """Test conversation creation."""
        # Test basic conversation creation
        conv_id = manager.create_conversation(
            name="Test Conversation",
            description="A test conversation"
        )
        
        assert conv_id is not None
        assert len(conv_id) > 0
        
        # Verify conversation was created
        conversation = manager.get_conversation(conv_id)
        assert conversation is not None
        assert conversation['name'] == "Test Conversation"
        assert conversation['description'] == "A test conversation"
        assert 'conversation_id' in conversation
        assert 'created_at' in conversation
        assert 'updated_at' in conversation
        assert conversation['messages'] == []
    
    def test_create_conversation_with_initial_messages(self, manager):
        """Test conversation creation with initial messages."""
        initial_messages = [
            {
                'role': 'user',
                'content': 'Hello, world!',
                'metadata': {'source': 'test'}
            },
            {
                'role': 'assistant',
                'content': 'Hello! How can I help you?'
            }
        ]
        
        conv_id = manager.create_conversation(
            name="Test with Messages",
            initial_messages=initial_messages
        )
        
        conversation = manager.get_conversation(conv_id)
        assert len(conversation['messages']) == 2
        assert conversation['messages'][0]['role'] == 'user'
        assert conversation['messages'][0]['content'] == 'Hello, world!'
        assert conversation['messages'][1]['role'] == 'assistant'
    
    def test_create_conversation_with_metadata(self, manager):
        """Test conversation creation with metadata."""
        metadata = {
            'project': 'test-project',
            'tags': ['important', 'test'],
            'priority': 'high'
        }
        
        conv_id = manager.create_conversation(
            name="Test with Metadata",
            metadata=metadata
        )
        
        conversation = manager.get_conversation(conv_id)
        assert conversation['metadata'] == metadata
    
    def test_get_conversation_not_found(self, manager):
        """Test getting non-existent conversation."""
        result = manager.get_conversation("non-existent-id")
        assert result is None
    
    def test_update_conversation(self, manager):
        """Test conversation update."""
        # Create conversation
        conv_id = manager.create_conversation(name="Original Name")
        
        # Update conversation
        success = manager.update_conversation(
            conv_id,
            name="Updated Name",
            description="Updated description",
            metadata={'updated': True}
        )
        
        assert success is True
        
        # Verify updates
        conversation = manager.get_conversation(conv_id)
        assert conversation['name'] == "Updated Name"
        assert conversation['description'] == "Updated description"
        assert conversation['metadata']['updated'] is True
    
    def test_update_conversation_not_found(self, manager):
        """Test updating non-existent conversation."""
        with pytest.raises(ConversationNotFoundError):
            manager.update_conversation("non-existent-id", name="New Name")
    
    def test_delete_conversation(self, manager):
        """Test conversation deletion."""
        # Create conversation
        conv_id = manager.create_conversation(name="To Delete")
        
        # Verify it exists
        assert manager.get_conversation(conv_id) is not None
        
        # Delete conversation
        success = manager.delete_conversation(conv_id)
        assert success is True
        
        # Verify it's gone
        assert manager.get_conversation(conv_id) is None
    
    def test_delete_conversation_not_found(self, manager):
        """Test deleting non-existent conversation."""
        success = manager.delete_conversation("non-existent-id")
        assert success is False
    
    def test_append_message(self, manager):
        """Test appending messages to conversations."""
        # Create conversation
        conv_id = manager.create_conversation(name="Test Messages")
        
        # Append message
        msg_id = manager.append_message(
            conv_id,
            role="user",
            content="Test message",
            metadata={'source': 'test'}
        )
        
        assert msg_id is not None
        
        # Verify message was added
        messages = manager.get_messages(conv_id)
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert messages[0]['content'] == 'Test message'
        assert messages[0]['message_id'] == msg_id
        assert messages[0]['metadata']['source'] == 'test'
    
    def test_append_message_to_nonexistent_conversation(self, manager):
        """Test appending message to non-existent conversation."""
        with pytest.raises(ConversationNotFoundError):
            manager.append_message("non-existent-id", "user", "Test message")
    
    def test_search_conversations(self, manager):
        """Test searching conversations."""
        # Create conversations with searchable content
        conv_id1 = manager.create_conversation(
            name="Python Programming Discussion",
            description="Discussion about Python programming"
        )
        manager.append_message(conv_id1, "user", "How to use decorators in Python?")
        
        conv_id2 = manager.create_conversation(
            name="JavaScript Tutorial",
            description="Learning JavaScript basics"
        )
        manager.append_message(conv_id2, "user", "What are JavaScript closures?")
        
        # Search for Python-related conversations
        results = manager.search_conversations("Python", search_in_messages=True)
        
        # Should find the Python conversation
        assert len(results) >= 1
        found_python = any(
            result['conversation']['conversation_id'] == conv_id1
            for result in results
        )
        assert found_python
    
    def test_health_check(self, manager):
        """Test health check functionality."""
        health = manager.health_check()
        
        assert 'status' in health
        assert health['status'] in ['healthy', 'warning', 'degraded', 'unhealthy']
        assert 'storage' in health
        assert 'cache' in health
        assert 'index' in health
        assert 'search' in health
    
    def test_statistics(self, manager):
        """Test statistics collection."""
        initial_stats = manager.get_statistics()
        
        # Create some conversations and messages
        conv_id = manager.create_conversation(name="Stats Test")
        manager.append_message(conv_id, "user", "Test message")
        
        final_stats = manager.get_statistics()
        
        # Verify statistics updated
        assert final_stats['conversations_created'] > initial_stats['conversations_created']
        assert final_stats['messages_added'] > initial_stats['messages_added']
    
    def test_caching_behavior(self, manager):
        """Test caching functionality."""
        # Create conversation
        conv_id = manager.create_conversation(name="Cache Test")
        
        # Clear cache to start fresh
        manager.clear_cache()
        
        # First access should miss cache
        initial_stats = manager.get_statistics()
        initial_misses = initial_stats['cache_misses']
        
        conversation1 = manager.get_conversation(conv_id)
        stats_after_first = manager.get_statistics()
        assert stats_after_first['cache_misses'] > initial_misses
        
        # Second access should hit cache
        initial_hits = stats_after_first['cache_hits']
        conversation2 = manager.get_conversation(conv_id)
        stats_after_second = manager.get_statistics()
        assert stats_after_second['cache_hits'] > initial_hits
        
        # Both results should be identical
        assert conversation1 == conversation2
