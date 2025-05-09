
import pytest
import os
import shutil
import time
import json
from pathlib import Path
from typing import Generator, Any, Dict
from loguru import logger

from autocoder.common.file_checkpoint.manager import FileChangeManager
from autocoder.common.file_checkpoint.schema import FileChange, FileChangeAction
from autocoder.common.file_checkpoint.store import FileChangeStore
from autocoder.common.file_checkpoint.backup import FileBackupManager

BASE_DIR = Path(__file__).parent
TEMP_CHECKPOINT_DIR = BASE_DIR / "temp_checkpoint_dir_manager_test"
TEST_FILE_DIR = BASE_DIR / "test_files_manager"
TEST_FILE_PATH = TEST_FILE_DIR / "sample.txt"
TEST_FILE_PATH_2 = TEST_FILE_DIR / "another_sample.txt"


def setup_function(function: Any) -> None:
    logger.info(f"Setting up for test: {function.__name__}")
    if TEMP_CHECKPOINT_DIR.exists():
        shutil.rmtree(TEMP_CHECKPOINT_DIR)
    TEMP_CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    if TEST_FILE_DIR.exists():
        shutil.rmtree(TEST_FILE_DIR)
    TEST_FILE_DIR.mkdir(parents=True, exist_ok=True)

    with open(TEST_FILE_PATH, "w") as f:
        f.write("Initial content.\n")
    with open(TEST_FILE_PATH_2, "w") as f:
        f.write("Initial content for file 2.\n")


def teardown_function(function: Any) -> None:
    logger.info(f"Tearing down after test: {function.__name__}")
    if TEMP_CHECKPOINT_DIR.exists():
        shutil.rmtree(TEMP_CHECKPOINT_DIR)
    if TEST_FILE_DIR.exists():
        shutil.rmtree(TEST_FILE_DIR)


@pytest.fixture
def manager() -> Generator[FileChangeManager, None, None]:
    instance = FileChangeManager(
        project_root=str(TEST_FILE_DIR.resolve()),
        checkpoint_dir=str(TEMP_CHECKPOINT_DIR.resolve())
    )
    yield instance
    # Cleanup after instance if necessary, though teardown_function handles most
    logger.info("FileChangeManager instance yielded and test completed.")


def test_initialization(manager: FileChangeManager) -> None:
    logger.info("Testing FileChangeManager initialization...")
    assert manager.project_root == str(TEST_FILE_DIR.resolve())
    assert manager.checkpoint_dir == str(TEMP_CHECKPOINT_DIR.resolve())
    assert isinstance(manager.change_store, FileChangeStore)
    assert isinstance(manager.backup_manager, FileBackupManager)
    assert (TEMP_CHECKPOINT_DIR / "changes").exists()
    assert (TEMP_CHECKPOINT_DIR / "backups").exists()
    logger.info("FileChangeManager initialization test passed.")


def test_record_and_apply_change(manager: FileChangeManager) -> None:
    logger.info("Testing record and apply file change...")
    relative_path = "sample.txt"
    abs_path = str(TEST_FILE_PATH.resolve())

    # Create a change
    new_content = "Updated content.\n"
    change = FileChange(
        file_path=relative_path,
        action=FileChangeAction.UPDATE,
        new_content=new_content,
        timestamp=time.time()
    )
    manager.record_change(change)
    logger.info(f"Recorded change for {relative_path}")

    # Check if change is recorded
    changes = manager.get_changes_for_file(relative_path)
    assert len(changes) == 1
    assert changes[0].new_content == new_content
    logger.info("Change correctly recorded.")

    # Apply the change
    manager.apply_change(changes[0].id)
    with open(abs_path, "r") as f:
        content = f.read()
    assert content == new_content
    logger.info("Change correctly applied to file.")

    # Check backup
    backups = manager.backup_manager.get_backups_for_file(relative_path)
    assert len(backups) == 1
    original_content_from_backup = manager.backup_manager.get_backup_content(backups[0].backup_id)
    assert original_content_from_backup == "Initial content.\n"
    logger.info("Backup correctly created.")

    # Revert the change
    manager.revert_change(changes[0].id)
    with open(abs_path, "r") as f:
        content = f.read()
    assert content == "Initial content.\n"
    logger.info("Change correctly reverted.")
    logger.info("Record and apply file change test passed.")


def test_preview_change(manager: FileChangeManager) -> None:
    logger.info("Testing preview file change...")
    relative_path = "sample.txt"
    
    change = FileChange(
        file_path=relative_path,
        action=FileChangeAction.UPDATE,
        old_content="Initial content.\n",
        new_content="Preview content.\n",
        timestamp=time.time()
    )
    manager.record_change(change)
    changes = manager.get_changes_for_file(relative_path)
    diff = manager.preview_change(changes[0].id)
    
    assert "--- a/sample.txt" in diff
    assert "+++ b/sample.txt" in diff
    assert "-Initial content." in diff
    assert "+Preview content." in diff
    logger.info("Preview file change test passed.")


def test_clear_all_checkpoints(manager: FileChangeManager) -> None:
    logger.info("Testing clear_all_checkpoints...")
    relative_path_1 = "sample.txt"
    relative_path_2 = "another_sample.txt"

    # Record some changes for file 1
    change1_content = "Content for change 1 on sample.txt\n"
    change1 = FileChange(
        file_path=relative_path_1,
        action=FileChangeAction.UPDATE,
        new_content=change1_content,
        timestamp=time.time()
    )
    manager.record_change(change1)
    manager.apply_change(manager.get_changes_for_file(relative_path_1)[0].id) # This creates a backup

    change2_content = "Content for change 2 on sample.txt\n"
    change2 = FileChange(
        file_path=relative_path_1,
        action=FileChangeAction.UPDATE,
        new_content=change2_content,
        timestamp=time.time() + 1
    )
    manager.record_change(change2)
    manager.apply_change(manager.get_changes_for_file(relative_path_1)[1].id) # This creates another backup

    # Record some changes for file 2
    change3_content = "Content for change 1 on another_sample.txt\n"
    change3 = FileChange(
        file_path=relative_path_2,
        action=FileChangeAction.UPDATE,
        new_content=change3_content,
        timestamp=time.time() + 2
    )
    manager.record_change(change3)
    manager.apply_change(manager.get_changes_for_file(relative_path_2)[0].id) # Backup for file 2

    logger.info("Initial changes and backups created.")

    # Verify that changes and backups exist before clearing
    assert len(manager.get_changes_for_file(relative_path_1)) == 2
    assert len(manager.backup_manager.get_backups_for_file(relative_path_1)) == 2
    assert len(manager.get_changes_for_file(relative_path_2)) == 1
    assert len(manager.backup_manager.get_backups_for_file(relative_path_2)) == 1
    
    # Check physical files in store and backup directories
    store_dir = TEMP_CHECKPOINT_DIR / "changes"
    backup_dir = TEMP_CHECKPOINT_DIR / "backups"
    
    # Check store (db file and potentially json files if that's how it works)
    assert (store_dir / "changes.db").exists()
    
    # Check backups (metadata and actual backup files)
    assert (backup_dir / "backup_metadata.json").exists()
    backup_files_count = sum(1 for item in os.listdir(backup_dir) if item != "backup_metadata.json" and os.path.isfile(backup_dir / item))
    assert backup_files_count == 3 # 2 for sample.txt, 1 for another_sample.txt
    
    logger.info("Verified existence of checkpoint data before clearing.")

    # Call the clear_all_checkpoints method
    result = manager.clear_all_checkpoints()
    logger.info(f"clear_all_checkpoints result: {result}")

    # Assertions
    assert result["cleared_changes"] is True
    assert result["cleared_backups"] is True

    # Verify that changes and backups are cleared from the manager's perspective
    assert len(manager.get_changes_for_file(relative_path_1)) == 0
    assert len(manager.backup_manager.get_backups_for_file(relative_path_1)) == 0
    assert len(manager.get_changes_for_file(relative_path_2)) == 0
    assert len(manager.backup_manager.get_backups_for_file(relative_path_2)) == 0
    logger.info("Verified no changes or backups found via manager methods after clearing.")

    # Verify that the physical directories are empty or reset
    # Store directory: changes.db should be re-initialized (empty or just schema)
    # Backup directory: backup_metadata.json should be re-initialized (empty), no backup files
    
    assert (store_dir / "changes.db").exists() # DB is re-initialized, not deleted
    conn = manager.change_store._create_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM changes")
    assert cursor.fetchone()[0] == 0, "Changes table in DB should be empty"
    conn.close()
    
    # Check for other .json files in store_dir (if any were created by older versions or other mechanisms)
    json_files_in_store = [f for f in os.listdir(store_dir) if f.endswith(".json")]
    assert len(json_files_in_store) == 0, "No JSON files should remain in the changes store directory"

    assert (backup_dir / "backup_metadata.json").exists() # Metadata is re-initialized
    with open(backup_dir / "backup_metadata.json", "r") as f:
        backup_meta_content = json.load(f)
    assert backup_meta_content == {}, "Backup metadata should be empty"
    
    remaining_backup_files = [
        item for item in os.listdir(backup_dir) 
        if item != "backup_metadata.json" and os.path.isfile(backup_dir / item)
    ]
    assert len(remaining_backup_files) == 0, f"No backup files should remain in the backup directory. Found: {remaining_backup_files}"
    
    logger.info("Verified physical checkpoint directories are cleared/reset.")
    logger.info("clear_all_checkpoints test passed.")

if __name__ == "__main__":
    # This allows running tests directly with `python test_manager.py`
    # For more comprehensive testing, use `pytest`
    pytest.main([__file__])
