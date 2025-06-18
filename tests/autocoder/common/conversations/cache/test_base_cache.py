"""
Tests for base cache interface.
"""
import pytest
from abc import ABC, ABCMeta
from typing import Optional, Any

from autocoder.common.conversations.cache.base_cache import BaseCache


class TestBaseCache:
    """Test base cache interface."""
    
    def test_base_cache_is_abstract(self):
        """Test that BaseCache is an abstract base class."""
        assert issubclass(BaseCache, ABC)
        
        # Should not be able to instantiate directly
        with pytest.raises(TypeError):
            BaseCache()
    
    def test_base_cache_interface_methods(self):
        """Test that BaseCache defines required abstract methods."""
        # Check that all required methods are defined as abstract
        abstract_methods = BaseCache.__abstractmethods__
        expected_methods = {
            'get', 'set', 'delete', 'clear', 'exists', 'size', 'keys'
        }
        
        assert expected_methods.issubset(abstract_methods)
    
    def test_concrete_implementation_works(self):
        """Test that a concrete implementation can be created."""
        
        class ConcreteCache(BaseCache):
            def __init__(self):
                self._data = {}
            
            def get(self, key: str) -> Optional[Any]:
                return self._data.get(key)
            
            def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
                self._data[key] = value
            
            def delete(self, key: str) -> bool:
                if key in self._data:
                    del self._data[key]
                    return True
                return False
            
            def clear(self) -> None:
                self._data.clear()
            
            def exists(self, key: str) -> bool:
                return key in self._data
            
            def size(self) -> int:
                return len(self._data)
            
            def keys(self) -> list:
                return list(self._data.keys())
        
        # Should be able to create concrete implementation
        cache = ConcreteCache()
        assert isinstance(cache, BaseCache)
        
        # Test basic functionality
        cache.set("test_key", "test_value")
        assert cache.get("test_key") == "test_value"
        assert cache.exists("test_key") is True
        assert cache.size() == 1
        assert "test_key" in cache.keys()
        
        assert cache.delete("test_key") is True
        assert cache.get("test_key") is None
        assert cache.exists("test_key") is False
        
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        assert cache.size() == 2
        
        cache.clear()
        assert cache.size() == 0
    
    def test_method_signatures(self):
        """Test that method signatures are correctly defined."""
        # This tests that the abstract methods have the correct signatures
        import inspect
        
        # Get method signatures from BaseCache
        get_sig = inspect.signature(BaseCache.get)
        set_sig = inspect.signature(BaseCache.set)
        delete_sig = inspect.signature(BaseCache.delete)
        clear_sig = inspect.signature(BaseCache.clear)
        exists_sig = inspect.signature(BaseCache.exists)
        size_sig = inspect.signature(BaseCache.size)
        keys_sig = inspect.signature(BaseCache.keys)
        
        # Verify parameter names and types
        assert list(get_sig.parameters.keys()) == ['self', 'key']
        assert list(set_sig.parameters.keys()) == ['self', 'key', 'value', 'ttl']
        assert list(delete_sig.parameters.keys()) == ['self', 'key']
        assert list(clear_sig.parameters.keys()) == ['self']
        assert list(exists_sig.parameters.keys()) == ['self', 'key']
        assert list(size_sig.parameters.keys()) == ['self']
        assert list(keys_sig.parameters.keys()) == ['self'] 