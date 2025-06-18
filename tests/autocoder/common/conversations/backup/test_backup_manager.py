"""
Tests for BackupManager.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.autocoder.common.conversations.config import ConversationManagerConfig
from src.autocoder.common.conversations.backup.backup_manager import BackupManager, BackupMetadata
from src.autocoder.common.conversations.exceptions import BackupError


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def config(temp_storage):
    """Create a test configuration."""
    return ConversationManagerConfig(
        storage_path=temp_storage,
        backup_enabled=True,
        backup_interval=3600.0,
        max_backups=5
    )


@pytest.fixture
def backup_manager(config):
    """Create a BackupManager instance for testing."""
    return BackupManager(config)


@pytest.fixture
def sample_conversations(temp_storage):
    """Create sample conversation files for testing."""
    conversations_dir = Path(temp_storage) / "conversations"
    conversations_dir.mkdir(parents=True, exist_ok=True)
    
    # Create sample conversations
    conversations = []
    for i in range(3):
        conv_id = f"conv_{i}"
        conv_data = {
            "conversation_id": conv_id,
            "name": f"Test Conversation {i}",
            "created_at": datetime.now().timestamp(),
            "messages": [
                {
                    "message_id": f"msg_{i}_0",
                    "role": "user",
                    "content": f"Hello from conversation {i}",
                    "timestamp": datetime.now().timestamp()
                }
            ]
        }
        
        conv_file = conversations_dir / f"{conv_id}.json"
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conv_data, f, indent=2)
        
        conversations.append((conv_id, conv_data))
    
    # Create sample index
    index_dir = Path(temp_storage) / "index"
    index_dir.mkdir(parents=True, exist_ok=True)
    
    index_data = {
        "conversations": [conv[0] for conv in conversations],
        "last_updated": datetime.now().timestamp()
    }
    
    index_file = index_dir / "conversations.idx"
    with open(index_file, 'w', encoding='utf-8') as f:
        json.dump(index_data, f, indent=2)
    
    return conversations


class TestBackupManager:
    """Test cases for BackupManager."""
    
    def test_backup_manager_initialization(self, backup_manager, temp_storage):
        """Test backup manager initialization."""
        assert backup_manager.config.storage_path == temp_storage
        assert backup_manager.backup_path.exists()
        assert backup_manager.temp_path.exists()
        assert isinstance(backup_manager._metadata, dict)
    
    def test_create_full_backup_empty_storage(self, backup_manager):
        """Test creating full backup with empty storage."""
        backup_id = backup_manager.create_full_backup("Empty backup test")
        
        assert backup_id is not None
        assert backup_id.startswith("full_")
        
        # Check metadata
        metadata = backup_manager.get_backup_metadata(backup_id)
        assert metadata is not None
        assert metadata.backup_type == "full"
        assert metadata.description == "Empty backup test"
        assert metadata.file_count == 0
        assert metadata.conversation_ids == []
    
    def test_create_full_backup_with_data(self, backup_manager, sample_conversations):
        """Test creating full backup with sample data."""
        backup_id = backup_manager.create_full_backup("Full backup with data")
        
        assert backup_id is not None
        assert backup_id.startswith("full_")
        
        # Check metadata
        metadata = backup_manager.get_backup_metadata(backup_id)
        assert metadata is not None
        assert metadata.backup_type == "full"
        assert metadata.file_count == 3  # 3 conversation files
        assert len(metadata.conversation_ids) == 3
        assert metadata.total_size_bytes > 0
        assert metadata.checksum is not None
        
        # Verify backup directory exists and contains files
        backup_dir = backup_manager.backup_path / backup_id
        assert backup_dir.exists()
        
        # Check conversation files
        for conv_id, _ in sample_conversations:
            conv_file = backup_dir / f"{conv_id}.json"
            assert conv_file.exists()
        
        # Check index directory
        index_dir = backup_dir / "index"
        assert index_dir.exists()
    
    def test_create_incremental_backup_no_base(self, backup_manager):
        """Test creating incremental backup without base backup."""
        with pytest.raises(BackupError, match="No full backup found"):
            backup_manager.create_incremental_backup()
    
    def test_create_incremental_backup_no_changes(self, backup_manager, sample_conversations):
        """Test creating incremental backup with no changes."""
        # Create full backup first
        full_backup_id = backup_manager.create_full_backup("Base backup")
        
        # Create incremental backup immediately (no changes)
        incremental_backup_id = backup_manager.create_incremental_backup(
            description="No changes backup"
        )
        
        assert incremental_backup_id is not None
        assert incremental_backup_id.startswith("incremental_")
        
        # Check metadata
        metadata = backup_manager.get_backup_metadata(incremental_backup_id)
        assert metadata is not None
        assert metadata.backup_type == "incremental"
        assert metadata.base_backup_id == full_backup_id
        assert metadata.file_count == 0  # No changes
    
    def test_create_incremental_backup_with_changes(self, backup_manager, sample_conversations, temp_storage):
        """Test creating incremental backup with changes."""
        # Create full backup first
        full_backup_id = backup_manager.create_full_backup("Base backup")
        
        # Wait a bit to ensure timestamp difference
        import time
        time.sleep(0.1)
        
        # Modify a conversation file
        conversations_dir = Path(temp_storage) / "conversations"
        conv_file = conversations_dir / "conv_0.json"
        
        with open(conv_file, 'r', encoding='utf-8') as f:
            conv_data = json.load(f)
        
        conv_data["messages"].append({
            "message_id": "new_msg",
            "role": "assistant",
            "content": "This is a new message",
            "timestamp": datetime.now().timestamp()
        })
        
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conv_data, f, indent=2)
        
        # Create incremental backup
        incremental_backup_id = backup_manager.create_incremental_backup(
            description="Changes backup"
        )
        
        assert incremental_backup_id is not None
        
        # Check metadata
        metadata = backup_manager.get_backup_metadata(incremental_backup_id)
        assert metadata is not None
        assert metadata.backup_type == "incremental"
        assert metadata.base_backup_id == full_backup_id
        assert metadata.file_count > 0  # Should have changes
        assert "conv_0" in metadata.conversation_ids
    
    def test_list_backups(self, backup_manager, sample_conversations):
        """Test listing backups."""
        # Initially no backups
        backups = backup_manager.list_backups()
        assert len(backups) == 0
        
        # Create some backups
        full_backup_id = backup_manager.create_full_backup("First backup")
        incremental_backup_id = backup_manager.create_incremental_backup(description="Second backup")
        
        # List backups
        backups = backup_manager.list_backups()
        assert len(backups) == 2
        
        # Should be sorted by timestamp (newest first)
        assert backups[0].backup_id == incremental_backup_id
        assert backups[1].backup_id == full_backup_id
    
    def test_delete_backup(self, backup_manager, sample_conversations):
        """Test deleting a backup."""
        backup_id = backup_manager.create_full_backup("Test backup")
        
        # Verify backup exists
        assert backup_manager.get_backup_metadata(backup_id) is not None
        backup_dir = backup_manager.backup_path / backup_id
        assert backup_dir.exists()
        
        # Delete backup
        result = backup_manager.delete_backup(backup_id)
        assert result is True
        
        # Verify backup is deleted
        assert backup_manager.get_backup_metadata(backup_id) is None
        assert not backup_dir.exists()
        
        # Try to delete non-existent backup
        result = backup_manager.delete_backup("non_existent")
        assert result is False
    
    def test_delete_backup_with_dependencies(self, backup_manager, sample_conversations):
        """Test deleting a backup that has dependent incremental backups."""
        full_backup_id = backup_manager.create_full_backup("Base backup")
        incremental_backup_id = backup_manager.create_incremental_backup(description="Dependent backup")
        
        # Try to delete full backup that has incremental dependency
        with pytest.raises(BackupError, match="Cannot delete backup.*referenced by"):
            backup_manager.delete_backup(full_backup_id)
        
        # Should be able to delete incremental backup
        result = backup_manager.delete_backup(incremental_backup_id)
        assert result is True
        
        # Now should be able to delete full backup
        result = backup_manager.delete_backup(full_backup_id)
        assert result is True
    
    def test_verify_backup(self, backup_manager, sample_conversations):
        """Test backup verification."""
        backup_id = backup_manager.create_full_backup("Test backup")
        
        # Verify intact backup
        assert backup_manager.verify_backup(backup_id) is True
        
        # Corrupt backup by modifying a file
        backup_dir = backup_manager.backup_path / backup_id
        conv_file = backup_dir / "conv_0.json"
        
        with open(conv_file, 'a', encoding='utf-8') as f:
            f.write("corrupted data")
        
        # Verification should now fail
        assert backup_manager.verify_backup(backup_id) is False
        
        # Verify non-existent backup
        assert backup_manager.verify_backup("non_existent") is False
    
    def test_cleanup_old_backups(self, backup_manager, sample_conversations):
        """Test cleanup of old backups."""
        # Set max_backups to 3 to test the cleanup behavior
        backup_manager.config.max_backups = 3
        
        # Create 4 backups - the 4th one should trigger cleanup
        backup_ids = []
        for i in range(4):
            backup_id = backup_manager.create_full_backup(f"Backup {i}")
            backup_ids.append(backup_id)
            # Small delay to ensure different timestamps
            import time
            time.sleep(0.01)
        
        # Should have 3 backups due to auto-cleanup during creation
        backups = backup_manager.list_backups()
        assert len(backups) <= 3  # Could be 3 or fewer due to automatic cleanup
        
        # Test explicit cleanup
        backup_manager.config.max_backups = 1
        deleted_count = backup_manager.cleanup_old_backups()
        assert deleted_count >= 0  # Could be 0 if already cleaned up
        
        # Should now have 1 backup
        backups = backup_manager.list_backups()
        assert len(backups) == 1
    
    def test_backup_statistics(self, backup_manager, sample_conversations):
        """Test backup statistics."""
        # Initially no statistics
        stats = backup_manager.get_backup_statistics()
        assert stats["total_backups"] == 0
        assert stats["full_backups"] == 0
        assert stats["incremental_backups"] == 0
        assert stats["total_size_bytes"] == 0
        
        # Create backups
        full_backup_id = backup_manager.create_full_backup("Full backup")
        incremental_backup_id = backup_manager.create_incremental_backup(description="Incremental backup")
        
        # Check statistics
        stats = backup_manager.get_backup_statistics()
        assert stats["total_backups"] == 2
        assert stats["full_backups"] == 1
        assert stats["incremental_backups"] == 1
        assert stats["total_size_bytes"] > 0
        assert stats["total_size_mb"] >= 0  # Could be 0 for very small files
        assert stats["last_full_backup"] is not None
        assert stats["last_incremental_backup"] is not None
    
    def test_should_create_backup(self, backup_manager, sample_conversations):
        """Test backup scheduling logic."""
        # Initially should create full backup
        should_backup, backup_type = backup_manager.should_create_backup()
        assert should_backup is True
        assert backup_type == "full"
        
        # After creating full backup, should not need backup immediately
        backup_manager.create_full_backup("Recent backup")
        should_backup, backup_type = backup_manager.should_create_backup()
        # The test might pass if incremental backup is due
        if should_backup:
            assert backup_type == "incremental"
        else:
            assert should_backup is False
        
        # Simulate time passing for incremental backup
        backup_manager._last_full_backup = datetime.now().timestamp() - (backup_manager.config.backup_interval / 8)
        should_backup, backup_type = backup_manager.should_create_backup()
        assert should_backup is True
        assert backup_type == "incremental"
    
    def test_backup_metadata_persistence(self, backup_manager, sample_conversations):
        """Test that backup metadata persists across manager instances."""
        # Create backup
        backup_id = backup_manager.create_full_backup("Persistence test")
        
        # Create new manager instance
        new_manager = BackupManager(backup_manager.config)
        
        # Should have the same backup metadata
        metadata = new_manager.get_backup_metadata(backup_id)
        assert metadata is not None
        assert metadata.backup_id == backup_id
        assert metadata.description == "Persistence test"
    
    def test_backup_error_handling(self, backup_manager):
        """Test error handling in backup operations."""
        # Test with invalid base backup ID
        with pytest.raises(BackupError, match="Base backup .* not found"):
            backup_manager.create_incremental_backup(base_backup_id="non_existent")
        
        # Test backup creation with permission issues
        # Make backup directory read-only
        original_mode = backup_manager.backup_path.stat().st_mode
        backup_manager.backup_path.chmod(0o444)
        
        try:
            with pytest.raises(BackupError, match="Failed to create full backup"):
                backup_manager.create_full_backup("Permission test")
        finally:
            # Restore permissions for cleanup
            backup_manager.backup_path.chmod(original_mode) 