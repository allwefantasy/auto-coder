"""
Conversation management module for AutoCoder.

This module provides comprehensive conversation and message management
functionality including persistence, caching, search, and concurrent access.
"""

from .exceptions import (
    ConversationManagerError,
    ConversationNotFoundError,
    MessageNotFoundError,
    ConcurrencyError,
    DataIntegrityError,
    LockTimeoutError,
    BackupError,
    RestoreError
)

from .models import (
    ConversationMessage,
    Conversation
)

from .config import ConversationManagerConfig
from .file_locker import FileLocker

# Storage layer
from .storage import (
    BaseStorage,
    FileStorage,
    IndexManager
)

# Cache layer
from .cache import (
    BaseCache,
    MemoryCache,
    CacheManager
)

# Search and filtering layer
from .search import (
    TextSearcher,
    FilterManager
)

# Backup and restore layer
from .backup import (
    BackupManager,
    RestoreManager
)

# Main manager
from .manager import PersistConversationManager

__all__ = [
    # Main manager
    'PersistConversationManager',
    
    # Exceptions
    'ConversationManagerError',
    'ConversationNotFoundError', 
    'MessageNotFoundError',
    'ConcurrencyError',
    'DataIntegrityError',
    'LockTimeoutError',
    'BackupError',
    'RestoreError',
    
    # Models
    'ConversationMessage',
    'Conversation',
    
    # Configuration
    'ConversationManagerConfig',
    
    # File locking
    'FileLocker',
    
    # Storage layer
    'BaseStorage',
    'FileStorage', 
    'IndexManager',
    
    # Cache layer
    'BaseCache',
    'MemoryCache',
    'CacheManager',
    
    # Search and filtering layer
    'TextSearcher',
    'FilterManager',
    
    # Backup and restore layer
    'BackupManager',
    'RestoreManager'
] 