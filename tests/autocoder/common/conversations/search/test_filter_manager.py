"""Tests for filter management functionality."""

import pytest
from src.autocoder.common.conversations.search.filter_manager import (
    FilterManager, Filter, FilterGroup, FilterOperator, LogicalOperator
)

class TestFilter:
    def test_filter_creation(self):
        """Test filter creation."""
        filter_obj = Filter('name', FilterOperator.EQUALS, 'test')
        assert filter_obj.field == 'name'
        assert filter_obj.operator == FilterOperator.EQUALS
        assert filter_obj.value == 'test'
        
    def test_filter_apply_equals(self):
        """Test filter application with equals operator."""
        filter_obj = Filter('name', FilterOperator.EQUALS, 'test')
        assert filter_obj.apply({'name': 'test'}) == True
        assert filter_obj.apply({'name': 'other'}) == False
        
    def test_filter_apply_contains(self):
        """Test filter application with contains operator."""
        filter_obj = Filter('description', FilterOperator.CONTAINS, 'python')
        assert filter_obj.apply({'description': 'python programming'}) == True
        assert filter_obj.apply({'description': 'Python is great'}) == True
        assert filter_obj.apply({'description': 'javascript coding'}) == False

class TestFilterGroup:
    def test_and_filter_group(self):
        """Test AND filter group."""
        filters = [
            Filter('role', FilterOperator.EQUALS, 'user'),
            Filter('active', FilterOperator.EQUALS, True)
        ]
        group = FilterGroup(filters, LogicalOperator.AND)
        
        assert group.apply({'role': 'user', 'active': True}) == True
        assert group.apply({'role': 'user', 'active': False}) == False
        
    def test_or_filter_group(self):
        """Test OR filter group."""
        filters = [
            Filter('role', FilterOperator.EQUALS, 'admin'),
            Filter('permissions', FilterOperator.CONTAINS, 'write')
        ]
        group = FilterGroup(filters, LogicalOperator.OR)
        
        assert group.apply({'role': 'admin', 'permissions': 'read'}) == True
        assert group.apply({'role': 'user', 'permissions': 'write'}) == True
        assert group.apply({'role': 'user', 'permissions': 'read'}) == False

class TestFilterManager:
    def test_filter_manager_creation(self):
        """Test filter manager creation."""
        manager = FilterManager()
        assert hasattr(manager, 'predefined_filters')
        assert 'has_messages' in manager.predefined_filters
        
    def test_create_filter(self):
        """Test creating individual filters."""
        manager = FilterManager()
        filter_obj = manager.create_filter('name', 'eq', 'test')
        assert isinstance(filter_obj, Filter)
        assert filter_obj.field == 'name'
        assert filter_obj.operator == FilterOperator.EQUALS
        
    def test_apply_filters_basic(self):
        """Test applying basic filters."""
        manager = FilterManager()
        items = [
            {'name': 'test', 'active': True},
            {'name': 'other', 'active': False},
            {'name': 'test', 'active': True}
        ]
        
        filter_obj = manager.create_filter('name', 'eq', 'test')
        results = manager.apply_filters(items, filter_obj)
        
        assert len(results) == 2
        assert all(item['name'] == 'test' for item in results)
        
    def test_apply_multiple_filters(self):
        """Test applying multiple filters."""
        manager = FilterManager()
        items = [
            {'name': 'test', 'count': 5, 'active': True},
            {'name': 'other', 'count': 10, 'active': True},
            {'name': 'test', 'count': 3, 'active': False}
        ]
        
        filters = [
            manager.create_filter('name', 'eq', 'test'),
            manager.create_filter('active', 'eq', True)
        ]
        filter_group = manager.create_filter_group(filters, 'and')
        results = manager.apply_filters(items, filter_group)
        
        assert len(results) == 1
        assert results[0]['name'] == 'test' and results[0]['active'] == True
        
    def test_text_search_filter(self):
        """Test text search filter creation."""
        manager = FilterManager()
        search_filter = manager.create_text_search_filter(['name', 'description'], 'python')
        
        assert isinstance(search_filter, FilterGroup)
        assert search_filter.operator == LogicalOperator.OR
        assert len(search_filter.filters) == 2 