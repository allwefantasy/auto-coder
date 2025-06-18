"""
Tests for RestoreManager.
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime, timedelta

from src.autocoder.common.conversations.config import ConversationManagerConfig
from src.autocoder.common.conversations.backup.backup_manager import BackupManager
from src.autocoder.common.conversations.backup.restore_manager import RestoreManager
from src.autocoder.common.conversations.exceptions import RestoreError


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
def restore_manager(config, backup_manager):
    """Create a RestoreManager instance for testing."""
    return RestoreManager(config, backup_manager)


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


@pytest.fixture
def backup_with_data(backup_manager, sample_conversations):
    """Create a backup with sample data."""
    return backup_manager.create_full_backup("Test backup")


class TestRestoreManager:
    """Test cases for RestoreManager."""
    
    def test_restore_manager_initialization(self, restore_manager, temp_storage):
        """Test restore manager initialization."""
        assert restore_manager.config.storage_path == temp_storage
        assert restore_manager.backup_path.exists()
        assert restore_manager.temp_path.exists()
        assert restore_manager.backup_manager is not None
    
    def test_restore_conversation_success(self, restore_manager, backup_with_data, temp_storage):
        """Test successful conversation restoration."""
        # Clear the original conversation to simulate loss
        conversations_dir = Path(temp_storage) / "conversations"
        conv_file = conversations_dir / "conv_0.json"
        
        if conv_file.exists():
            conv_file.unlink()  # Delete the file
        
        # Restore the conversation
        result = restore_manager.restore_conversation("conv_0", backup_with_data)
        assert result is True
        
        # Verify the conversation was restored
        assert conv_file.exists()
        with open(conv_file, 'r', encoding='utf-8') as f:
            restored_data = json.load(f)
        
        assert restored_data["conversation_id"] == "conv_0"
        assert len(restored_data["messages"]) > 0
    
    def test_restore_conversation_not_found(self, restore_manager, backup_with_data):
        """Test restoring non-existent conversation."""
        with pytest.raises(RestoreError, match="Conversation .* not found in backup"):
            restore_manager.restore_conversation("non_existent", backup_with_data)
    
    def test_restore_conversation_invalid_backup(self, restore_manager):
        """Test restoring from invalid backup."""
        with pytest.raises(RestoreError, match="Backup .* not found"):
            restore_manager.restore_conversation("conv_0", "invalid_backup")
    
    def test_restore_full_backup_success(self, restore_manager, backup_with_data, temp_storage):
        """Test successful full backup restoration."""
        # Clear all data to simulate complete loss
        conversations_dir = Path(temp_storage) / "conversations"
        index_dir = Path(temp_storage) / "index"
        
        if conversations_dir.exists():
            shutil.rmtree(conversations_dir)
        if index_dir.exists():
            shutil.rmtree(index_dir)
        
        # Restore full backup
        result = restore_manager.restore_full_backup(backup_with_data)
        
        assert "backup_id" in result
        assert result["backup_id"] == backup_with_data
        assert len(result["restored_conversations"]) > 0
        
        # Verify directories were recreated
        assert conversations_dir.exists()
        
        # Verify conversation files were restored
        for conv_id in result["restored_conversations"]:
            conv_file = conversations_dir / f"{conv_id}.json"
            assert conv_file.exists()
    
    def test_list_restorable_conversations(self, restore_manager, backup_with_data):
        """Test listing restorable conversations."""
        conversations = restore_manager.list_restorable_conversations(backup_with_data)
        
        assert isinstance(conversations, list)
        assert len(conversations) > 0
        assert "conv_0" in conversations
        assert "conv_1" in conversations
        assert "conv_2" in conversations
    
    def test_get_restore_preview(self, restore_manager, backup_with_data):
        """Test getting restore preview."""
        preview = restore_manager.get_restore_preview(backup_with_data)
        
        assert "backup_id" in preview
        assert preview["backup_id"] == backup_with_data
        assert "backup_type" in preview
        assert "backup_timestamp" in preview
        assert "restorable_conversations" in preview
        assert "total_file_count" in preview
        assert "total_size_bytes" in preview
        
        assert len(preview["restorable_conversations"]) > 0
        assert preview["total_file_count"] > 0
        assert preview["total_size_bytes"] > 0
    
    def test_validate_backup_chain_full_backup(self, restore_manager, backup_with_data):
        """Test validating backup chain for full backup."""
        validation = restore_manager.validate_backup_chain(backup_with_data)
        
        assert validation["backup_id"] == backup_with_data
        assert validation["chain_length"] == 1
        assert validation["is_valid"] is True
        assert len(validation["errors"]) == 0
        assert len(validation["chain_backups"]) == 1
        assert validation["chain_backups"][0]["backup_type"] == "full"
    
    def test_restore_conversation_with_existing_backup(self, restore_manager, backup_with_data, temp_storage):
        """Test restoring conversation when existing file exists (should create backup)."""
        conversations_dir = Path(temp_storage) / "conversations"
        conv_file = conversations_dir / "conv_0.json"
        
        # Ensure file exists
        assert conv_file.exists()
        
        # Count backup files before restore
        backup_files_before = list(conversations_dir.glob("conv_0.backup_*.json"))
        
        # Restore (should create backup of existing file)
        result = restore_manager.restore_conversation("conv_0", backup_with_data)
        assert result is True
        
        # Check that backup file was created
        backup_files_after = list(conversations_dir.glob("conv_0.backup_*.json"))
        assert len(backup_files_after) == len(backup_files_before) + 1
    
    def test_restore_full_backup_with_existing_data(self, restore_manager, backup_with_data, temp_storage):
        """Test full backup restoration with existing data (should create backups)."""
        # Restore with existing data (should create backup of existing data)
        result = restore_manager.restore_full_backup(
            backup_with_data,
            overwrite_existing=False
        )
        
        assert "backed_up_files" in result
        assert len(result["backed_up_files"]) > 0
        
        # Verify backup directories were created
        backup_files = [Path(f) for f in result["backed_up_files"]]
        for backup_file in backup_files:
            assert backup_file.exists()
    
    def test_restore_full_backup_overwrite(self, restore_manager, backup_with_data, temp_storage):
        """Test full backup restoration with overwrite."""
        result = restore_manager.restore_full_backup(
            backup_with_data,
            overwrite_existing=True
        )
        
        assert result["overwrite_existing"] is True
        assert len(result["backed_up_files"]) == 0  # No backups created
    
    def test_restore_full_backup_invalid_backup(self, restore_manager):
        """Test restoring from invalid full backup."""
        with pytest.raises(RestoreError, match="Backup .* not found"):
            restore_manager.restore_full_backup("invalid_backup")
    
    def test_restore_full_backup_not_full_type(self, restore_manager, backup_manager, sample_conversations):
        """Test trying to restore full backup from incremental backup."""
        # Create full backup and then incremental
        full_backup = backup_manager.create_full_backup("Full backup")
        incremental_backup = backup_manager.create_incremental_backup("Incremental backup")
        
        # Try to restore incremental as full backup
        with pytest.raises(RestoreError, match="is not a full backup"):
            restore_manager.restore_full_backup(incremental_backup)
    
    def test_list_restorable_conversations_invalid_backup(self, restore_manager):
        """Test listing restorable conversations from invalid backup."""
        with pytest.raises(RestoreError, match="Backup .* not found"):
            restore_manager.list_restorable_conversations("invalid_backup")
    
    def test_validate_backup_chain_incremental(self, restore_manager, backup_manager, sample_conversations):
        """Test validating backup chain for incremental backup."""
        # Create backup chain
        full_backup = backup_manager.create_full_backup("Full backup")
        incremental_backup = backup_manager.create_incremental_backup("Incremental backup")
        
        validation = restore_manager.validate_backup_chain(incremental_backup)
        
        assert validation["backup_id"] == incremental_backup
        assert validation["chain_length"] == 2  # Full + incremental
        assert validation["is_valid"] is True
        assert len(validation["errors"]) == 0
        assert len(validation["chain_backups"]) == 2
        
        # Chain should be ordered from base to target
        assert validation["chain_backups"][0]["backup_type"] == "full"
        assert validation["chain_backups"][1]["backup_type"] == "incremental"
    
    def test_build_backup_chain(self, restore_manager, backup_manager, sample_conversations):
        """Test building backup chain."""
        # Create backup chain
        full_backup = backup_manager.create_full_backup("Full backup")
        incremental1 = backup_manager.create_incremental_backup("Incremental 1")
        
        # Test full backup chain
        chain = restore_manager._build_backup_chain(full_backup)
        assert chain == [full_backup]
        
        # Test incremental backup chain
        chain = restore_manager._build_backup_chain(incremental1)
        assert chain == [full_backup, incremental1]
    
    def test_find_conversation_in_backups(self, restore_manager, backup_manager, sample_conversations, temp_storage):
        """Test finding conversation in backup chain."""
        # Create initial backup
        full_backup = backup_manager.create_full_backup("Full backup")
        
        # Modify conversation and create incremental backup
        import time
        time.sleep(0.1)
        
        conversations_dir = Path(temp_storage) / "conversations"
        conv_file = conversations_dir / "conv_0.json"
        
        with open(conv_file, 'r', encoding='utf-8') as f:
            conv_data = json.load(f)
        
        conv_data["messages"].append({
            "message_id": "modified_msg",
            "role": "assistant",
            "content": "Modified content",
            "timestamp": datetime.now().timestamp()
        })
        
        with open(conv_file, 'w', encoding='utf-8') as f:
            json.dump(conv_data, f, indent=2)
        
        incremental_backup = backup_manager.create_incremental_backup("Modified backup")
        
        # Find conversation in backup chain
        backup_chain = [full_backup, incremental_backup]
        conversation_data = restore_manager._find_conversation_in_backups("conv_0", backup_chain)
        
        assert conversation_data is not None
        assert conversation_data["conversation_id"] == "conv_0"
        # Should find the most recent version (from incremental backup)
        assert any(msg["message_id"] == "modified_msg" for msg in conversation_data["messages"])
    
    def test_find_best_backup_for_timestamp(self, restore_manager, backup_manager, sample_conversations):
        """Test finding best backup for timestamp."""
        # Create multiple backups with different timestamps
        backup1_time = datetime.now().timestamp()
        backup1 = backup_manager.create_full_backup("Backup 1")
        
        # Small delay
        import time
        time.sleep(0.1)
        
        backup2_time = datetime.now().timestamp()
        backup2 = backup_manager.create_incremental_backup("Backup 2")
        
        time.sleep(0.1)
        future_time = datetime.now().timestamp()
        
        # Find backup for time before any backups
        backup_id = restore_manager._find_best_backup_for_timestamp(backup1_time - 100)
        assert backup_id is None
        
        # Find backup for time between backups
        backup_id = restore_manager._find_best_backup_for_timestamp(backup1_time + 0.05)
        assert backup_id == backup1
        
        # Find backup for time after all backups
        backup_id = restore_manager._find_best_backup_for_timestamp(future_time)
        assert backup_id == backup2
    
    def test_restore_point_in_time(self, restore_manager, backup_manager, sample_conversations, temp_storage):
        """Test point-in-time restoration."""
        # Create backup at specific time
        backup_time = datetime.now().timestamp()
        backup_id = backup_manager.create_full_backup("Point in time backup")
        
        # Clear data
        conversations_dir = Path(temp_storage) / "conversations"
        if conversations_dir.exists():
            shutil.rmtree(conversations_dir)
        
        # Restore to that point in time
        result = restore_manager.restore_point_in_time(backup_time + 1)
        
        assert "backup_id" in result
        assert result["backup_id"] == backup_id
        assert len(result["restored_conversations"]) > 0
        
        # Verify data was restored
        assert conversations_dir.exists()
    
    def test_restore_point_in_time_no_backup(self, restore_manager):
        """Test point-in-time restoration with no suitable backup."""
        past_timestamp = datetime.now().timestamp() - 86400  # 24 hours ago
        
        with pytest.raises(RestoreError, match="No suitable backup found"):
            restore_manager.restore_point_in_time(past_timestamp)
    
    def test_restore_error_handling(self, restore_manager, backup_manager, sample_conversations):
        """Test error handling in restoration operations."""
        backup_id = backup_manager.create_full_backup("Test backup")
        
        # Test restoration with corrupted backup
        # Corrupt the backup by removing files
        backup_dir = restore_manager.backup_path / backup_id
        for conv_file in backup_dir.glob("*.json"):
            conv_file.unlink()
        
        # Verification should fail and restoration should error
        with pytest.raises(RestoreError, match="integrity check failed"):
            restore_manager.restore_conversation("conv_0", backup_id) 