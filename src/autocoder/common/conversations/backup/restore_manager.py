"""
Restore manager for conversation data.

This module provides functionality to restore conversation data from backups,
including version management and data validation.
"""

import os
import json
import shutil
import threading
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple
from pathlib import Path

from ..exceptions import RestoreError, ConversationManagerError, BackupError
from ..config import ConversationManagerConfig
from .backup_manager import BackupManager, BackupMetadata


class RestoreManager:
    """
    Manages restore operations for conversation data.
    
    Provides functionality to restore data from full and incremental backups,
    with validation and version management.
    """
    
    def __init__(self, config: ConversationManagerConfig, backup_manager: BackupManager):
        """
        Initialize restore manager.
        
        Args:
            config: Configuration object containing restore settings
            backup_manager: BackupManager instance for accessing backup metadata
        """
        self.config = config
        self.backup_manager = backup_manager
        self.storage_path = Path(config.storage_path)
        self.backup_path = self.storage_path / "backups"
        self.temp_path = self.storage_path / "temp"
        
        # Ensure directories exist
        self.temp_path.mkdir(parents=True, exist_ok=True)
        
        # Thread lock for restore operations
        self._restore_lock = threading.Lock()
    
    def restore_conversation(
        self, 
        conversation_id: str, 
        backup_id: str,
        target_directory: Optional[str] = None
    ) -> bool:
        """
        Restore a specific conversation from backup.
        
        Args:
            conversation_id: ID of the conversation to restore
            backup_id: ID of the backup to restore from
            target_directory: Optional target directory for restoration
            
        Returns:
            True if restoration was successful
            
        Raises:
            RestoreError: If restoration fails
        """
        with self._restore_lock:
            try:
                # Get backup metadata
                metadata = self.backup_manager.get_backup_metadata(backup_id)
                if metadata is None:
                    raise RestoreError(f"Backup {backup_id} not found")
                
                # Verify backup integrity
                if not self.backup_manager.verify_backup(backup_id):
                    raise RestoreError(f"Backup {backup_id} integrity check failed")
                
                # Build complete backup chain for incremental backups
                backup_chain = self._build_backup_chain(backup_id)
                
                # Find conversation file in backup chain
                conversation_data = self._find_conversation_in_backups(
                    conversation_id, backup_chain
                )
                
                if conversation_data is None:
                    raise RestoreError(
                        f"Conversation {conversation_id} not found in backup {backup_id}"
                    )
                
                # Determine target directory
                if target_directory is None:
                    target_dir = self.storage_path / "conversations"
                else:
                    target_dir = Path(target_directory)
                
                target_dir.mkdir(parents=True, exist_ok=True)
                
                # Create backup of existing conversation if it exists
                existing_file = target_dir / f"{conversation_id}.json"
                if existing_file.exists():
                    backup_file = existing_file.with_suffix(
                        f".backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
                    )
                    shutil.copy2(existing_file, backup_file)
                
                # Write restored conversation data
                with open(existing_file, 'w', encoding='utf-8') as f:
                    json.dump(conversation_data, f, indent=2, ensure_ascii=False)
                
                return True
                
            except Exception as e:
                raise RestoreError(f"Failed to restore conversation {conversation_id}: {str(e)}") from e
    
    def restore_full_backup(
        self, 
        backup_id: str,
        target_directory: Optional[str] = None,
        overwrite_existing: bool = False
    ) -> Dict[str, any]:
        """
        Restore all data from a full backup.
        
        Args:
            backup_id: ID of the backup to restore from
            target_directory: Optional target directory for restoration
            overwrite_existing: Whether to overwrite existing files
            
        Returns:
            Dictionary containing restore results
            
        Raises:
            RestoreError: If restoration fails
        """
        with self._restore_lock:
            try:
                # Get backup metadata
                metadata = self.backup_manager.get_backup_metadata(backup_id)
                if metadata is None:
                    raise RestoreError(f"Backup {backup_id} not found")
                
                if metadata.backup_type != "full":
                    raise RestoreError(f"Backup {backup_id} is not a full backup")
                
                # Verify backup integrity
                if not self.backup_manager.verify_backup(backup_id):
                    raise RestoreError(f"Backup {backup_id} integrity check failed")
                
                backup_dir = self.backup_path / backup_id
                
                # Determine target directory
                if target_directory is None:
                    target_dir = self.storage_path
                else:
                    target_dir = Path(target_directory)
                
                # Create timestamp for backup naming
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                
                # Backup existing data if not overwriting
                existing_conversations_dir = target_dir / "conversations"
                existing_index_dir = target_dir / "index"
                
                backed_up_files = []
                if not overwrite_existing:
                    if existing_conversations_dir.exists():
                        backup_conversations_dir = target_dir / f"conversations.backup_{timestamp}"
                        shutil.copytree(existing_conversations_dir, backup_conversations_dir)
                        backed_up_files.append(str(backup_conversations_dir))
                    
                    if existing_index_dir.exists():
                        backup_index_dir = target_dir / f"index.backup_{timestamp}"
                        shutil.copytree(existing_index_dir, backup_index_dir)
                        backed_up_files.append(str(backup_index_dir))
                
                # Restore conversations
                restored_conversations = []
                conversations_backup_dir = backup_dir
                if conversations_backup_dir.exists():
                    target_conversations_dir = target_dir / "conversations"
                    target_conversations_dir.mkdir(parents=True, exist_ok=True)
                    
                    for conv_file in conversations_backup_dir.glob("*.json"):
                        target_file = target_conversations_dir / conv_file.name
                        shutil.copy2(conv_file, target_file)
                        restored_conversations.append(conv_file.stem)
                
                # Restore index files
                restored_indices = []
                index_backup_dir = backup_dir / "index"
                if index_backup_dir.exists():
                    target_index_dir = target_dir / "index"
                    target_index_dir.mkdir(parents=True, exist_ok=True)
                    
                    for index_file in index_backup_dir.glob("*.json"):
                        target_file = target_index_dir / index_file.name
                        shutil.copy2(index_file, target_file)
                        restored_indices.append(index_file.name)
                
                return {
                    "backup_id": backup_id,
                    "restore_timestamp": datetime.now().isoformat(),
                    "restored_conversations": restored_conversations,
                    "restored_indices": restored_indices,
                    "backed_up_files": backed_up_files,
                    "overwrite_existing": overwrite_existing
                }
                
            except Exception as e:
                raise RestoreError(f"Failed to restore full backup {backup_id}: {str(e)}") from e
    
    def restore_point_in_time(
        self, 
        target_timestamp: float,
        target_directory: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Restore data to a specific point in time.
        
        Args:
            target_timestamp: Target timestamp to restore to
            target_directory: Optional target directory for restoration
            
        Returns:
            Dictionary containing restore results
            
        Raises:
            RestoreError: If restoration fails
        """
        with self._restore_lock:
            try:
                # Find the best backup for the target timestamp
                backup_id = self._find_best_backup_for_timestamp(target_timestamp)
                if backup_id is None:
                    raise RestoreError(f"No suitable backup found for timestamp {target_timestamp}")
                
                metadata = self.backup_manager.get_backup_metadata(backup_id)
                
                if metadata.backup_type == "full":
                    return self.restore_full_backup(
                        backup_id, 
                        target_directory=target_directory
                    )
                else:
                    # For incremental backups, we need to apply the backup chain
                    return self._restore_incremental_chain(
                        backup_id, 
                        target_directory=target_directory
                    )
                
            except Exception as e:
                raise RestoreError(f"Failed to restore to timestamp {target_timestamp}: {str(e)}") from e
    
    def list_restorable_conversations(self, backup_id: str) -> List[str]:
        """
        List conversations that can be restored from a backup.
        
        Args:
            backup_id: ID of the backup to check
            
        Returns:
            List of conversation IDs that can be restored
            
        Raises:
            RestoreError: If backup cannot be accessed
        """
        try:
            metadata = self.backup_manager.get_backup_metadata(backup_id)
            if metadata is None:
                raise RestoreError(f"Backup {backup_id} not found")
            
            if metadata.backup_type == "full":
                return metadata.conversation_ids or []
            else:
                # For incremental backups, get conversations from backup chain
                backup_chain = self._build_backup_chain(backup_id)
                all_conversations = set()
                
                for chain_backup_id in backup_chain:
                    chain_metadata = self.backup_manager.get_backup_metadata(chain_backup_id)
                    if chain_metadata and chain_metadata.conversation_ids:
                        all_conversations.update(chain_metadata.conversation_ids)
                
                return list(all_conversations)
                
        except Exception as e:
            raise RestoreError(f"Failed to list restorable conversations: {str(e)}") from e
    
    def validate_backup_chain(self, backup_id: str) -> Dict[str, any]:
        """
        Validate the integrity of a backup chain.
        
        Args:
            backup_id: ID of the backup to validate
            
        Returns:
            Dictionary containing validation results
            
        Raises:
            RestoreError: If validation fails
        """
        try:
            backup_chain = self._build_backup_chain(backup_id)
            validation_results = {
                "backup_id": backup_id,
                "chain_length": len(backup_chain),
                "chain_backups": [],
                "is_valid": True,
                "errors": []
            }
            
            for chain_backup_id in backup_chain:
                metadata = self.backup_manager.get_backup_metadata(chain_backup_id)
                if metadata is None:
                    validation_results["is_valid"] = False
                    validation_results["errors"].append(f"Backup {chain_backup_id} metadata not found")
                    continue
                
                # Verify backup integrity
                is_valid = self.backup_manager.verify_backup(chain_backup_id)
                
                backup_info = {
                    "backup_id": chain_backup_id,
                    "backup_type": metadata.backup_type,
                    "timestamp": metadata.timestamp,
                    "is_valid": is_valid
                }
                
                if not is_valid:
                    validation_results["is_valid"] = False
                    validation_results["errors"].append(f"Backup {chain_backup_id} integrity check failed")
                
                validation_results["chain_backups"].append(backup_info)
            
            return validation_results
            
        except Exception as e:
            raise RestoreError(f"Failed to validate backup chain: {str(e)}") from e
    
    def get_restore_preview(self, backup_id: str) -> Dict[str, any]:
        """
        Get a preview of what would be restored from a backup.
        
        Args:
            backup_id: ID of the backup to preview
            
        Returns:
            Dictionary containing restore preview information
            
        Raises:
            RestoreError: If preview generation fails
        """
        try:
            metadata = self.backup_manager.get_backup_metadata(backup_id)
            if metadata is None:
                raise RestoreError(f"Backup {backup_id} not found")
            
            backup_chain = self._build_backup_chain(backup_id)
            
            preview = {
                "backup_id": backup_id,
                "backup_type": metadata.backup_type,
                "backup_timestamp": metadata.timestamp,
                "backup_chain": backup_chain,
                "restorable_conversations": self.list_restorable_conversations(backup_id),
                "total_file_count": 0,
                "total_size_bytes": 0
            }
            
            # Calculate total size and file count for the chain
            for chain_backup_id in backup_chain:
                chain_metadata = self.backup_manager.get_backup_metadata(chain_backup_id)
                if chain_metadata:
                    preview["total_file_count"] += chain_metadata.file_count
                    preview["total_size_bytes"] += chain_metadata.total_size_bytes
            
            return preview
            
        except Exception as e:
            raise RestoreError(f"Failed to generate restore preview: {str(e)}") from e
    
    def _build_backup_chain(self, backup_id: str) -> List[str]:
        """
        Build the complete backup chain for a backup.
        
        Args:
            backup_id: ID of the backup to build chain for
            
        Returns:
            List of backup IDs in the chain, ordered from base to target
        """
        chain = []
        current_backup_id = backup_id
        
        while current_backup_id:
            metadata = self.backup_manager.get_backup_metadata(current_backup_id)
            if metadata is None:
                break
            
            chain.insert(0, current_backup_id)  # Insert at beginning
            
            if metadata.backup_type == "full":
                break  # Reached the base backup
            
            current_backup_id = metadata.base_backup_id
        
        return chain
    
    def _find_conversation_in_backups(
        self, 
        conversation_id: str, 
        backup_chain: List[str]
    ) -> Optional[Dict]:
        """
        Find conversation data in backup chain.
        
        Args:
            conversation_id: ID of the conversation to find
            backup_chain: List of backup IDs to search in
            
        Returns:
            Conversation data or None if not found
        """
        # Search from newest to oldest backup
        for backup_id in reversed(backup_chain):
            backup_dir = self.backup_path / backup_id
            conv_file = backup_dir / f"{conversation_id}.json"
            
            if conv_file.exists():
                try:
                    with open(conv_file, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    continue  # Try next backup in chain
        
        return None
    
    def _find_best_backup_for_timestamp(self, target_timestamp: float) -> Optional[str]:
        """
        Find the best backup for a target timestamp.
        
        Args:
            target_timestamp: Target timestamp
            
        Returns:
            Backup ID or None if no suitable backup found
        """
        backups = self.backup_manager.list_backups()
        
        # Find backups that are before or at the target timestamp
        suitable_backups = [
            b for b in backups
            if b.timestamp <= target_timestamp
        ]
        
        if not suitable_backups:
            return None
        
        # Return the most recent suitable backup
        best_backup = max(suitable_backups, key=lambda x: x.timestamp)
        return best_backup.backup_id
    
    def _restore_incremental_chain(
        self, 
        backup_id: str,
        target_directory: Optional[str] = None
    ) -> Dict[str, any]:
        """
        Restore from an incremental backup chain.
        
        Args:
            backup_id: ID of the incremental backup
            target_directory: Optional target directory
            
        Returns:
            Dictionary containing restore results
        """
        backup_chain = self._build_backup_chain(backup_id)
        
        if not backup_chain:
            raise RestoreError(f"Empty backup chain for {backup_id}")
        
        # Start with full backup restoration
        full_backup_id = backup_chain[0]
        results = self.restore_full_backup(
            full_backup_id,
            target_directory=target_directory,
            overwrite_existing=True
        )
        
        # Apply incremental backups in order
        for incremental_backup_id in backup_chain[1:]:
            incremental_results = self._apply_incremental_backup(
                incremental_backup_id,
                target_directory or str(self.storage_path)
            )
            
            # Merge results
            results["restored_conversations"].extend(
                incremental_results.get("restored_conversations", [])
            )
            results["restored_indices"].extend(
                incremental_results.get("restored_indices", [])
            )
        
        # Remove duplicates
        results["restored_conversations"] = list(set(results["restored_conversations"]))
        results["restored_indices"] = list(set(results["restored_indices"]))
        
        return results
    
    def _apply_incremental_backup(
        self, 
        backup_id: str,
        target_directory: str
    ) -> Dict[str, any]:
        """Apply an incremental backup to the target directory."""
        backup_dir = self.backup_path / backup_id
        target_dir = Path(target_directory)
        
        restored_conversations = []
        restored_indices = []
        
        # Apply conversation files
        for conv_file in backup_dir.glob("*.json"):
            target_file = target_dir / "conversations" / conv_file.name
            target_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(conv_file, target_file)
            restored_conversations.append(conv_file.stem)
        
        # Apply index files
        index_backup_dir = backup_dir / "index"
        if index_backup_dir.exists():
            for index_file in index_backup_dir.glob("*.json"):
                target_file = target_dir / "index" / index_file.name
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(index_file, target_file)
                restored_indices.append(index_file.name)
        
        return {
            "restored_conversations": restored_conversations,
            "restored_indices": restored_indices
        } 