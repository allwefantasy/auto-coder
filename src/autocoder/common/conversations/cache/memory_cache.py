"""
Memory-based cache implementation with LRU eviction and TTL support.

This module provides a thread-safe in-memory cache with configurable
size limits, TTL expiration, and LRU eviction policies.
"""

import time
import threading
from collections import OrderedDict
from typing import Optional, Any, List, Dict
from dataclasses import dataclass

from .base_cache import BaseCache

# Sentinel object to distinguish between "no ttl provided" and "ttl=None"
_TTL_NOT_PROVIDED = object()

@dataclass
class CacheEntry:
    """Cache entry with value and expiration time."""
    value: Any
    expires_at: Optional[float] = None
    
    def is_expired(self) -> bool:
        """Check if this entry has expired."""
        if self.expires_at is None:
            return False
        return time.time() > self.expires_at


class MemoryCache(BaseCache):
    """Thread-safe in-memory cache with LRU eviction and TTL support."""
    
    def __init__(self, max_size: int = 100, default_ttl: float = 300.0):
        """
        Initialize memory cache.
        
        Args:
            max_size: Maximum number of items to cache
            default_ttl: Default TTL in seconds for cached items
        """
        if max_size <= 0:
            raise ValueError("max_size must be positive")
        
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        
        # Optional statistics
        self.hit_count = 0
        self.miss_count = 0
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value or None if not found/expired
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self.miss_count += 1
                return None
            
            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                self.miss_count += 1
                return None
            
            # Move to end (most recently used)
            self._cache.move_to_end(key)
            self.hit_count += 1
            return entry.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = _TTL_NOT_PROVIDED) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: The cache key
            value: The value to cache
            ttl: Time to live in seconds, None for no expiration
        """
        with self._lock:
            # Calculate expiration time
            expires_at = None
            
            if ttl is _TTL_NOT_PROVIDED:
                # No ttl provided, use default_ttl behavior
                if self.default_ttl > 0:
                    expires_at = time.time() + self.default_ttl
            elif ttl is None:
                # Explicit None means permanent caching
                expires_at = None
            elif ttl > 0:
                # Positive ttl value
                expires_at = time.time() + ttl
            # ttl <= 0 means permanent caching (expires_at stays None)
            
            # Create cache entry
            entry = CacheEntry(value=value, expires_at=expires_at)
            
            # If key already exists, update it
            if key in self._cache:
                self._cache[key] = entry
                self._cache.move_to_end(key)
            else:
                # Add new entry
                self._cache[key] = entry
                
                # Evict oldest items if over capacity
                while len(self._cache) > self.max_size:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
    
    def delete(self, key: str) -> bool:
        """
        Delete a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key was deleted, False if it didn't exist
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        with self._lock:
            self._cache.clear()
    
    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache.
        
        Args:
            key: The cache key
            
        Returns:
            True if the key exists and is not expired, False otherwise
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                return False
            
            if entry.is_expired():
                # Remove expired entry
                del self._cache[key]
                return False
            
            return True
    
    def size(self) -> int:
        """
        Get the current number of items in the cache.
        
        Returns:
            The number of items currently in the cache
        """
        with self._lock:
            # Clean up expired items
            self._cleanup_expired()
            return len(self._cache)
    
    def keys(self) -> List[str]:
        """
        Get all keys currently in the cache.
        
        Returns:
            List of keys currently in the cache
        """
        with self._lock:
            # Clean up expired items
            self._cleanup_expired()
            return list(self._cache.keys())
    
    def _cleanup_expired(self) -> None:
        """Remove all expired entries from the cache."""
        current_time = time.time()
        expired_keys = []
        
        for key, entry in self._cache.items():
            if entry.expires_at is not None and current_time > entry.expires_at:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary with cache statistics
        """
        with self._lock:
            self._cleanup_expired()
            
            total_requests = self.hit_count + self.miss_count
            hit_rate = self.hit_count / total_requests if total_requests > 0 else 0.0
            
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_rate": hit_rate,
                "default_ttl": self.default_ttl
            } 