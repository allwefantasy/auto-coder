"""
Backup manager for conversation data.

This module provides functionality to create, manage, and schedule backups
of conversation data, supporting both incremental and full backup strategies.
"""

import os
import json
import shutil
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path
from dataclasses import dataclass, asdict

from ..exceptions import BackupError, ConversationManagerError
from ..config import ConversationManagerConfig


@dataclass
class BackupMetadata:
    """Backup metadata information."""
    backup_id: str
    backup_type: str  # 'full' or 'incremental'
    timestamp: float
    created_at: str
    base_backup_id: Optional[str] = None  # For incremental backups
    conversation_ids: Optional[List[str]] = None
    file_count: int = 0
    total_size_bytes: int = 0
    checksum: Optional[str] = None
    description: Optional[str] = None


class BackupManager:
    """
    Manages backup operations for conversation data.
    
    Supports both full and incremental backups, with automatic scheduling
    and retention management.
    """
    
    def __init__(self, config: ConversationManagerConfig):
        """
        Initialize backup manager.
        
        Args:
            config: Configuration object containing backup settings
        """
        self.config = config
        self.storage_path = Path(config.storage_path)
        self.backup_path = self.storage_path / "backups"
        self.temp_path = self.storage_path / "temp"
        
        # Ensure backup directories exist
        self.backup_path.mkdir(parents=True, exist_ok=True)
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Backup metadata file
        self.metadata_file = self.backup_path / "backup_metadata.json"
        
        # Thread lock for backup operations
        self._backup_lock = threading.Lock()
        
        # Load existing backup metadata
        self._metadata: Dict[str, BackupMetadata] = self._load_metadata()
        
        # Track last backup timestamps
        self._last_full_backup: Optional[float] = None
        self._last_incremental_backup: Optional[float] = None
        self._update_backup_timestamps()
    
    def create_full_backup(self, description: Optional[str] = None) -> str:
        """
        Create a full backup of all conversation data.
        
        Args:
            description: Optional description for the backup
            
        Returns:
            Backup ID of the created backup
            
        Raises:
            BackupError: If backup creation fails
        """
        with self._backup_lock:
            try:
                backup_id = self._generate_backup_id("full")
                backup_dir = self.backup_path / backup_id
                backup_dir.mkdir(parents=True, exist_ok=True)
                
                # Get all conversation files
                conversations_dir = self.storage_path / "conversations"
                if not conversations_dir.exists():
                    # Create empty backup if no conversations exist
                    conversation_files = []
                else:
                    conversation_files = list(conversations_dir.glob("*.json"))
                
                # Copy conversation files to backup directory
                copied_files = []
                total_size = 0
                
                for conv_file in conversation_files:
                    if conv_file.name.endswith('.lock'):
                        continue
                        
                    dest_file = backup_dir / conv_file.name
                    shutil.copy2(conv_file, dest_file)
                    copied_files.append(conv_file.name)
                    total_size += conv_file.stat().st_size
                
                # Copy index files
                index_dir = self.storage_path / "index"
                if index_dir.exists():
                    backup_index_dir = backup_dir / "index"
                    backup_index_dir.mkdir(parents=True, exist_ok=True)
                    
                    for index_file in index_dir.glob("*.json"):
                        dest_file = backup_index_dir / index_file.name
                        shutil.copy2(index_file, dest_file)
                        total_size += index_file.stat().st_size
                
                # Calculate backup checksum
                checksum = self._calculate_backup_checksum(backup_dir)
                
                # Create backup metadata
                metadata = BackupMetadata(
                    backup_id=backup_id,
                    backup_type="full",
                    timestamp=datetime.now().timestamp(),
                    created_at=datetime.now().isoformat(),
                    conversation_ids=[f.stem for f in conversation_files],
                    file_count=len(copied_files),
                    total_size_bytes=total_size,
                    checksum=checksum,
                    description=description
                )
                
                # Save metadata
                self._metadata[backup_id] = metadata
                self._save_metadata()
                
                # Update last backup timestamp
                self._last_full_backup = metadata.timestamp
                
                # Clean up old backups if necessary
                self._cleanup_old_backups()
                
                return backup_id
                
            except Exception as e:
                # Clean up partial backup on failure
                backup_dir = self.backup_path / backup_id
                if backup_dir.exists():
                    shutil.rmtree(backup_dir, ignore_errors=True)
                raise BackupError(f"Failed to create full backup: {str(e)}") from e
    
    def create_incremental_backup(
        self, 
        base_backup_id: Optional[str] = None,
        description: Optional[str] = None
    ) -> str:
        """
        Create an incremental backup based on changes since the last backup.
        
        Args:
            base_backup_id: Base backup ID to compare against. If None, uses latest full backup
            description: Optional description for the backup
            
        Returns:
            Backup ID of the created incremental backup
            
        Raises:
            BackupError: If incremental backup creation fails
        """
        with self._backup_lock:
            try:
                # Find base backup
                if base_backup_id is None:
                    base_backup_id = self._get_latest_full_backup_id()
                    if base_backup_id is None:
                        raise BackupError("No full backup found for incremental backup")
                
                if base_backup_id not in self._metadata:
                    raise BackupError(f"Base backup {base_backup_id} not found")
                
                base_metadata = self._metadata[base_backup_id]
                base_timestamp = base_metadata.timestamp
                
                # Find changed files since base backup
                changed_files = self._find_changed_files_since(base_timestamp)
                
                if not changed_files:
                    # No changes, create empty incremental backup
                    pass
                
                backup_id = self._generate_backup_id("incremental")
                backup_dir = self.backup_path / backup_id
                backup_dir.mkdir(parents=True, exist_ok=True)
                
                # Copy changed files
                copied_files = []
                total_size = 0
                
                for file_path in changed_files:
                    rel_path = file_path.relative_to(self.storage_path)
                    dest_file = backup_dir / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    shutil.copy2(file_path, dest_file)
                    copied_files.append(str(rel_path))
                    total_size += file_path.stat().st_size
                
                # Calculate backup checksum
                checksum = self._calculate_backup_checksum(backup_dir)
                
                # Create backup metadata
                metadata = BackupMetadata(
                    backup_id=backup_id,
                    backup_type="incremental",
                    timestamp=datetime.now().timestamp(),
                    created_at=datetime.now().isoformat(),
                    base_backup_id=base_backup_id,
                    conversation_ids=self._extract_conversation_ids_from_files(copied_files),
                    file_count=len(copied_files),
                    total_size_bytes=total_size,
                    checksum=checksum,
                    description=description
                )
                
                # Save metadata
                self._metadata[backup_id] = metadata
                self._save_metadata()
                
                # Update last backup timestamp
                self._last_incremental_backup = metadata.timestamp
                
                return backup_id
                
            except Exception as e:
                # Clean up partial backup on failure
                try:
                    backup_dir = self.backup_path / backup_id
                    if backup_dir.exists():
                        shutil.rmtree(backup_dir, ignore_errors=True)
                except NameError:
                    # backup_id not defined yet, no cleanup needed
                    pass
                raise BackupError(f"Failed to create incremental backup: {str(e)}") from e
    
    def list_backups(self) -> List[BackupMetadata]:
        """
        List all available backups.
        
        Returns:
            List of backup metadata, sorted by timestamp (newest first)
        """
        backups = list(self._metadata.values())
        return sorted(backups, key=lambda x: x.timestamp, reverse=True)
    
    def get_backup_metadata(self, backup_id: str) -> Optional[BackupMetadata]:
        """
        Get metadata for a specific backup.
        
        Args:
            backup_id: ID of the backup
            
        Returns:
            Backup metadata or None if not found
        """
        return self._metadata.get(backup_id)
    
    def delete_backup(self, backup_id: str) -> bool:
        """
        Delete a specific backup.
        
        Args:
            backup_id: ID of the backup to delete
            
        Returns:
            True if backup was deleted, False if not found
            
        Raises:
            BackupError: If deletion fails
        """
        with self._backup_lock:
            try:
                if backup_id not in self._metadata:
                    return False
                
                # Check if this backup is referenced by incremental backups
                dependent_backups = [
                    b for b in self._metadata.values()
                    if b.base_backup_id == backup_id
                ]
                
                if dependent_backups:
                    dependent_ids = [b.backup_id for b in dependent_backups]
                    raise BackupError(
                        f"Cannot delete backup {backup_id}: it is referenced by "
                        f"incremental backups: {', '.join(dependent_ids)}"
                    )
                
                # Remove backup directory
                backup_dir = self.backup_path / backup_id
                if backup_dir.exists():
                    shutil.rmtree(backup_dir)
                
                # Remove from metadata
                del self._metadata[backup_id]
                self._save_metadata()
                
                return True
                
            except Exception as e:
                raise BackupError(f"Failed to delete backup {backup_id}: {str(e)}") from e
    
    def cleanup_old_backups(self) -> int:
        """
        Clean up old backups according to retention policy.
        
        Returns:
            Number of backups deleted
        """
        with self._backup_lock:
            return self._cleanup_old_backups()
    
    def get_backup_statistics(self) -> Dict:
        """
        Get backup statistics.
        
        Returns:
            Dictionary containing backup statistics
        """
        backups = list(self._metadata.values())
        full_backups = [b for b in backups if b.backup_type == "full"]
        incremental_backups = [b for b in backups if b.backup_type == "incremental"]
        
        total_size = sum(b.total_size_bytes for b in backups)
        
        return {
            "total_backups": len(backups),
            "full_backups": len(full_backups),
            "incremental_backups": len(incremental_backups),
            "total_size_bytes": total_size,
            "total_size_mb": round(total_size / (1024 * 1024), 2),
            "last_full_backup": self._last_full_backup,
            "last_incremental_backup": self._last_incremental_backup,
            "oldest_backup": min(b.timestamp for b in backups) if backups else None,
            "newest_backup": max(b.timestamp for b in backups) if backups else None,
        }
    
    def verify_backup(self, backup_id: str) -> bool:
        """
        Verify the integrity of a backup.
        
        Args:
            backup_id: ID of the backup to verify
            
        Returns:
            True if backup is valid, False otherwise
        """
        try:
            if backup_id not in self._metadata:
                return False
            
            metadata = self._metadata[backup_id]
            backup_dir = self.backup_path / backup_id
            
            if not backup_dir.exists():
                return False
            
            # Verify checksum
            current_checksum = self._calculate_backup_checksum(backup_dir)
            return current_checksum == metadata.checksum
            
        except Exception:
            return False
    
    def should_create_backup(self) -> Tuple[bool, str]:
        """
        Check if a backup should be created based on schedule.
        
        Returns:
            Tuple of (should_backup, backup_type)
        """
        now = datetime.now().timestamp()
        
        # Check if full backup is needed
        if (self._last_full_backup is None or 
            now - self._last_full_backup > self.config.backup_interval):
            return True, "full"
        
        # Check if incremental backup is needed
        incremental_interval = self.config.backup_interval / 4  # 4 times more frequent
        if (self._last_incremental_backup is None or
            now - self._last_incremental_backup > incremental_interval):
            return True, "incremental"
        
        return False, ""
    
    def _generate_backup_id(self, backup_type: str) -> str:
        """Generate a unique backup ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{backup_type}_{timestamp}"
    
    def _load_metadata(self) -> Dict[str, BackupMetadata]:
        """Load backup metadata from file."""
        if not self.metadata_file.exists():
            return {}
        
        try:
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = {}
            for backup_id, backup_data in data.items():
                metadata[backup_id] = BackupMetadata(**backup_data)
            
            return metadata
            
        except Exception as e:
            # If metadata is corrupted, start fresh but log the error
            backup_file = self.metadata_file.with_suffix('.corrupted')
            if self.metadata_file.exists():
                shutil.move(str(self.metadata_file), str(backup_file))
            return {}
    
    def _save_metadata(self) -> None:
        """Save backup metadata to file."""
        try:
            data = {
                backup_id: asdict(metadata)
                for backup_id, metadata in self._metadata.items()
            }
            
            # Write to temporary file first
            temp_file = self.metadata_file.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            # Atomic replace
            temp_file.replace(self.metadata_file)
            
        except Exception as e:
            raise BackupError(f"Failed to save backup metadata: {str(e)}") from e
    
    def _calculate_backup_checksum(self, backup_dir: Path) -> str:
        """Calculate checksum for entire backup directory."""
        hasher = hashlib.sha256()
        
        for file_path in sorted(backup_dir.rglob("*")):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    while chunk := f.read(8192):
                        hasher.update(chunk)
                hasher.update(file_path.name.encode('utf-8'))
        
        return hasher.hexdigest()
    
    def _find_changed_files_since(self, timestamp: float) -> List[Path]:
        """Find files modified since given timestamp."""
        changed_files = []
        
        # Check conversation files
        conversations_dir = self.storage_path / "conversations"
        if conversations_dir.exists():
            for conv_file in conversations_dir.glob("*.json"):
                if conv_file.stat().st_mtime > timestamp:
                    changed_files.append(conv_file)
        
        # Check index files
        index_dir = self.storage_path / "index"
        if index_dir.exists():
            for index_file in index_dir.glob("*.json"):
                if index_file.stat().st_mtime > timestamp:
                    changed_files.append(index_file)
        
        return changed_files
    
    def _extract_conversation_ids_from_files(self, file_paths: List[str]) -> List[str]:
        """Extract conversation IDs from file paths."""
        conversation_ids = []
        for file_path in file_paths:
            if file_path.startswith("conversations/") and file_path.endswith(".json"):
                conv_id = Path(file_path).stem
                conversation_ids.append(conv_id)
        return conversation_ids
    
    def _get_latest_full_backup_id(self) -> Optional[str]:
        """Get the ID of the latest full backup."""
        full_backups = [
            b for b in self._metadata.values()
            if b.backup_type == "full"
        ]
        
        if not full_backups:
            return None
        
        latest = max(full_backups, key=lambda x: x.timestamp)
        return latest.backup_id
    
    def _update_backup_timestamps(self) -> None:
        """Update last backup timestamps from metadata."""
        full_backups = [
            b for b in self._metadata.values()
            if b.backup_type == "full"
        ]
        incremental_backups = [
            b for b in self._metadata.values()
            if b.backup_type == "incremental"
        ]
        
        if full_backups:
            self._last_full_backup = max(b.timestamp for b in full_backups)
        
        if incremental_backups:
            self._last_incremental_backup = max(b.timestamp for b in incremental_backups)
    
    def _cleanup_old_backups(self) -> int:
        """Clean up old backups according to retention policy."""
        if not self.config.backup_enabled or self.config.max_backups <= 0:
            return 0
        
        backups = sorted(
            self._metadata.values(),
            key=lambda x: x.timestamp,
            reverse=True
        )
        
        if len(backups) <= self.config.max_backups:
            return 0
        
        # Keep the most recent backups
        backups_to_delete = backups[self.config.max_backups:]
        deleted_count = 0
        
        for backup in backups_to_delete:
            try:
                # Don't delete if it's referenced by other backups
                dependent_backups = [
                    b for b in self._metadata.values()
                    if b.base_backup_id == backup.backup_id
                ]
                
                if not dependent_backups:
                    backup_dir = self.backup_path / backup.backup_id
                    if backup_dir.exists():
                        shutil.rmtree(backup_dir)
                    
                    del self._metadata[backup.backup_id]
                    deleted_count += 1
                    
            except Exception:
                # Continue with other backups if one fails
                continue
        
        if deleted_count > 0:
            self._save_metadata()
        
        return deleted_count 