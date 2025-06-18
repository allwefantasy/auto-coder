"""
Base cache interface for conversation caching.

This module defines the abstract base class for all cache implementations,
providing a consistent interface for caching operations.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, List


class BaseCache(ABC):
    """Abstract base class for cache implementations."""
    
    @abstractmethod
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value or None if not found/expired
        """
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time to live in seconds, None for no expiration
        """
        pass
    
    @abstractmethod
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key was deleted, False if it didn't exist
        """
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all items from the cache."""
        pass
    
    @abstractmethod
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key exists and is not expired, False otherwise
        """
        pass
    
    @abstractmethod
    def size(self) -> int:
        """
        Get the current number of items in the cache.
        
        Returns:
            The number of items currently in the cache
        """
        pass
    
    @abstractmethod
    def keys(self) -> List[str]:
        """
        Get all keys currently in the cache.
        
        Returns:
            List of keys currently in the cache
        """
        pass 