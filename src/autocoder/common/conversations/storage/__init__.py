"""
Storage module for conversation management.

This module provides storage functionality for conversations and messages,
including file-based storage and indexing capabilities.
"""

from .base_storage import BaseStorage
from .file_storage import FileStorage
from .index_manager import IndexManager

__all__ = [
    'BaseStorage',
    'FileStorage', 
    'IndexManager'
] 