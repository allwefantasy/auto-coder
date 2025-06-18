"""
Tests for memory cache implementation.
"""
import pytest
import time
import threading
from unittest.mock import patch

from autocoder.common.conversations.cache.memory_cache import MemoryCache


class TestMemoryCache:
    """Test memory cache implementation."""
    
    def test_cache_creation(self):
        """Test cache creation with default and custom parameters."""
        # Default parameters
        cache = MemoryCache()
        assert cache.max_size == 100
        assert cache.default_ttl == 300.0
        assert cache.size() == 0
        
        # Custom parameters
        cache = MemoryCache(max_size=50, default_ttl=600.0)
        assert cache.max_size == 50
        assert cache.default_ttl == 600.0
        assert cache.size() == 0
    
    def test_basic_get_set(self):
        """Test basic get and set operations."""
        cache = MemoryCache()
        
        # Test set and get
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Test non-existent key
        assert cache.get("non_existent") is None
        
        # Test different value types
        cache.set("string", "test")
        cache.set("number", 42)
        cache.set("list", [1, 2, 3])
        cache.set("dict", {"a": 1, "b": 2})
        
        assert cache.get("string") == "test"
        assert cache.get("number") == 42
        assert cache.get("list") == [1, 2, 3]
        assert cache.get("dict") == {"a": 1, "b": 2}
    
    def test_exists_and_keys(self):
        """Test exists and keys methods."""
        cache = MemoryCache()
        
        # Empty cache
        assert cache.exists("key1") is False
        assert cache.keys() == []
        
        # Add some items
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        assert cache.exists("key1") is True
        assert cache.exists("key2") is True
        assert cache.exists("key3") is False
        
        keys = cache.keys()
        assert len(keys) == 2
        assert "key1" in keys
        assert "key2" in keys
    
    def test_delete(self):
        """Test delete operation."""
        cache = MemoryCache()
        
        # Delete non-existent key
        assert cache.delete("non_existent") is False
        
        # Add and delete key
        cache.set("key1", "value1")
        assert cache.exists("key1") is True
        
        assert cache.delete("key1") is True
        assert cache.exists("key1") is False
        assert cache.get("key1") is None
        
        # Delete already deleted key
        assert cache.delete("key1") is False
    
    def test_clear(self):
        """Test clear operation."""
        cache = MemoryCache()
        
        # Clear empty cache
        cache.clear()
        assert cache.size() == 0
        
        # Add items and clear
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        cache.clear()
        assert cache.size() == 0
        assert cache.keys() == []
        assert cache.get("key1") is None
        assert cache.get("key2") is None
    
    def test_size_tracking(self):
        """Test size tracking."""
        cache = MemoryCache()
        
        assert cache.size() == 0
        
        cache.set("key1", "value1")
        assert cache.size() == 1
        
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        cache.delete("key1")
        assert cache.size() == 1
        
        cache.clear()
        assert cache.size() == 0
    
    def test_ttl_expiration(self):
        """Test TTL expiration mechanism."""
        cache = MemoryCache(default_ttl=0.1)  # 100ms default TTL
        
        # Test with default TTL
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        # Wait for expiration
        time.sleep(0.15)
        assert cache.get("key1") is None
        assert cache.exists("key1") is False
        assert cache.size() == 0  # Should be cleaned up
        
        # Test with custom TTL
        cache.set("key2", "value2", ttl=0.2)
        assert cache.get("key2") == "value2"
        
        time.sleep(0.1)
        assert cache.get("key2") == "value2"  # Should still exist
        
        time.sleep(0.15)
        assert cache.get("key2") is None  # Should be expired
    
    def test_no_ttl(self):
        """Test items without TTL (permanent)."""
        cache = MemoryCache(default_ttl=0.1)
        
        # Set item without TTL
        cache.set("permanent", "value", ttl=None)
        
        # Wait longer than default TTL
        time.sleep(0.15)
        
        # Should still exist
        assert cache.get("permanent") == "value"
        assert cache.exists("permanent") is True
    
    def test_lru_eviction(self):
        """Test LRU eviction when cache is full."""
        cache = MemoryCache(max_size=3)
        
        # Fill cache to capacity
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        assert cache.size() == 3
        
        # Add another item, should evict least recently used (key1)
        cache.set("key4", "value4")
        assert cache.size() == 3
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"
        assert cache.get("key4") == "value4"
        
        # Access key2 to make it more recently used
        cache.get("key2")
        
        # Add another item, should evict key3 (now least recently used)
        cache.set("key5", "value5")
        assert cache.size() == 3
        assert cache.get("key2") == "value2"  # Still exists
        assert cache.get("key3") is None  # Evicted
        assert cache.get("key4") == "value4"
        assert cache.get("key5") == "value5"
    
    def test_lru_with_updates(self):
        """Test LRU behavior with updates."""
        cache = MemoryCache(max_size=2)
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Update key1 (should make it most recently used)
        cache.set("key1", "updated_value1")
        
        # Add new key, key2 should be evicted
        cache.set("key3", "value3")
        
        assert cache.get("key1") == "updated_value1"
        assert cache.get("key2") is None  # Evicted
        assert cache.get("key3") == "value3"
    
    def test_expired_items_cleanup(self):
        """Test that expired items are cleaned up."""
        cache = MemoryCache(max_size=5, default_ttl=0.1)
        
        # Add items that will expire
        cache.set("temp1", "value1")
        cache.set("temp2", "value2")
        cache.set("permanent", "value", ttl=None)
        
        assert cache.size() == 3
        
        # Wait for expiration
        time.sleep(0.15)
        
        # Access cache to trigger cleanup
        cache.get("permanent")
        
        # Only permanent item should remain
        assert cache.size() == 1
        assert cache.get("permanent") == "value"
        assert cache.get("temp1") is None
        assert cache.get("temp2") is None
    
    def test_thread_safety(self):
        """Test thread safety of cache operations."""
        cache = MemoryCache(max_size=1000)
        errors = []
        
        def worker(thread_id: int):
            try:
                for i in range(100):
                    key = f"thread_{thread_id}_key_{i}"
                    value = f"thread_{thread_id}_value_{i}"
                    
                    cache.set(key, value)
                    retrieved = cache.get(key)
                    
                    if retrieved != value:
                        errors.append(f"Thread {thread_id}: Expected {value}, got {retrieved}")
                    
                    if i % 10 == 0:
                        cache.delete(key)
            except Exception as e:
                errors.append(f"Thread {thread_id} error: {e}")
        
        # Run multiple threads
        threads = []
        for i in range(5):
            thread = threading.Thread(target=worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Check for errors
        assert len(errors) == 0, f"Thread safety errors: {errors}"
    
    def test_edge_cases(self):
        """Test edge cases and error conditions."""
        # Zero max size
        with pytest.raises((ValueError, AssertionError)):
            MemoryCache(max_size=0)
        
        # Negative max size
        with pytest.raises((ValueError, AssertionError)):
            MemoryCache(max_size=-1)
        
        # Very small cache
        cache = MemoryCache(max_size=1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        
        cache.set("key2", "value2")
        assert cache.get("key1") is None  # Evicted
        assert cache.get("key2") == "value2"
        
        # Empty key
        cache = MemoryCache()
        cache.set("", "empty_key_value")
        assert cache.get("") == "empty_key_value"
        
        # None value
        cache.set("none_value", None)
        assert cache.get("none_value") is None
        assert cache.exists("none_value") is True  # Should still exist
    
    @patch('time.time')
    def test_ttl_precision(self, mock_time):
        """Test TTL precision and timing."""
        # Mock time to control timing precisely
        mock_time.return_value = 1000.0
        
        cache = MemoryCache()
        cache.set("key1", "value1", ttl=10.0)
        
        # Should exist immediately
        assert cache.get("key1") == "value1"
        
        # Move time forward but not past expiration
        mock_time.return_value = 1009.9
        assert cache.get("key1") == "value1"
        
        # Move time past expiration
        mock_time.return_value = 1010.1
        assert cache.get("key1") is None
    
    def test_cache_statistics(self):
        """Test cache hit/miss statistics if implemented."""
        cache = MemoryCache()
        
        # Set some values
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        
        # Multiple gets (hits)
        cache.get("key1")
        cache.get("key1")
        cache.get("key2")
        
        # Miss
        cache.get("non_existent")
        
        # Verify statistics
        assert cache.hit_count >= 3
        assert cache.miss_count >= 1
        
        stats = cache.get_statistics()
        assert stats["hit_count"] >= 3
        assert stats["miss_count"] >= 1
        assert stats["size"] == 2
        assert stats["max_size"] == 100 