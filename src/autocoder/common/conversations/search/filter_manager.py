"""
Filter management for conversations and messages.

This module provides comprehensive filtering capabilities including
time-based filters, content filters, and complex query combinations.
"""

import re
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass
from enum import Enum


class FilterOperator(Enum):
    """Enumeration of filter operators."""
    EQUALS = "eq"
    NOT_EQUALS = "ne"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL = "gte"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL = "lte"
    CONTAINS = "contains"
    NOT_CONTAINS = "not_contains"
    STARTS_WITH = "starts_with"
    ENDS_WITH = "ends_with"
    REGEX = "regex"
    IN = "in"
    NOT_IN = "not_in"


class LogicalOperator(Enum):
    """Enumeration of logical operators for combining filters."""
    AND = "and"
    OR = "or"
    NOT = "not"


@dataclass
class Filter:
    """Represents a single filter condition."""
    field: str
    operator: FilterOperator
    value: Any
    case_sensitive: bool = False
    
    def apply(self, item: Dict[str, Any]) -> bool:
        """Apply this filter to an item."""
        field_value = self._get_field_value(item, self.field)
        
        if field_value is None:
            return False
        
        return self._compare_values(field_value, self.value, self.operator)
    
    def _get_field_value(self, item: Dict[str, Any], field_path: str) -> Any:
        """Get field value supporting nested field access (e.g., 'metadata.tags')."""
        value = item
        
        for field_part in field_path.split('.'):
            if isinstance(value, dict) and field_part in value:
                value = value[field_part]
            else:
                return None
        
        return value
    
    def _compare_values(self, field_value: Any, filter_value: Any, operator: FilterOperator) -> bool:
        """Compare field value with filter value using the specified operator."""
        try:
            if operator == FilterOperator.EQUALS:
                return self._normalize_for_comparison(field_value) == self._normalize_for_comparison(filter_value)
            
            elif operator == FilterOperator.NOT_EQUALS:
                return self._normalize_for_comparison(field_value) != self._normalize_for_comparison(filter_value)
            
            elif operator == FilterOperator.GREATER_THAN:
                return field_value > filter_value
            
            elif operator == FilterOperator.GREATER_THAN_OR_EQUAL:
                return field_value >= filter_value
            
            elif operator == FilterOperator.LESS_THAN:
                return field_value < filter_value
            
            elif operator == FilterOperator.LESS_THAN_OR_EQUAL:
                return field_value <= filter_value
            
            elif operator == FilterOperator.CONTAINS:
                field_str = self._normalize_for_comparison(str(field_value))
                filter_str = self._normalize_for_comparison(str(filter_value))
                return filter_str in field_str
            
            elif operator == FilterOperator.NOT_CONTAINS:
                field_str = self._normalize_for_comparison(str(field_value))
                filter_str = self._normalize_for_comparison(str(filter_value))
                return filter_str not in field_str
            
            elif operator == FilterOperator.STARTS_WITH:
                field_str = self._normalize_for_comparison(str(field_value))
                filter_str = self._normalize_for_comparison(str(filter_value))
                return field_str.startswith(filter_str)
            
            elif operator == FilterOperator.ENDS_WITH:
                field_str = self._normalize_for_comparison(str(field_value))
                filter_str = self._normalize_for_comparison(str(filter_value))
                return field_str.endswith(filter_str)
            
            elif operator == FilterOperator.REGEX:
                field_str = str(field_value)
                flags = 0 if self.case_sensitive else re.IGNORECASE
                return bool(re.search(filter_value, field_str, flags))
            
            elif operator == FilterOperator.IN:
                if not isinstance(filter_value, (list, tuple, set)):
                    return False
                return field_value in filter_value
            
            elif operator == FilterOperator.NOT_IN:
                if not isinstance(filter_value, (list, tuple, set)):
                    return True
                return field_value not in filter_value
            
        except (TypeError, ValueError, AttributeError):
            return False
        
        return False
    
    def _normalize_for_comparison(self, value: Any) -> Any:
        """Normalize value for comparison based on case sensitivity."""
        if isinstance(value, str) and not self.case_sensitive:
            return value.lower()
        return value


@dataclass 
class FilterGroup:
    """Represents a group of filters combined with logical operators."""
    filters: List[Union[Filter, 'FilterGroup']]
    operator: LogicalOperator = LogicalOperator.AND
    
    def apply(self, item: Dict[str, Any]) -> bool:
        """Apply this filter group to an item."""
        if not self.filters:
            return True
            
        if self.operator == LogicalOperator.AND:
            return all(f.apply(item) for f in self.filters)
        
        elif self.operator == LogicalOperator.OR:
            return any(f.apply(item) for f in self.filters)
        
        elif self.operator == LogicalOperator.NOT:
            # For NOT operator, apply AND logic and negate the result
            return not all(f.apply(item) for f in self.filters)
        
        return True


class FilterManager:
    """Manager for building and applying complex filters."""
    
    def __init__(self):
        """Initialize filter manager."""
        self.predefined_filters = {}
        self._register_predefined_filters()
    
    def _register_predefined_filters(self):
        """Register commonly used predefined filters."""
        # Time-based filters
        now = datetime.now().timestamp()
        
        self.predefined_filters.update({
            'today': Filter('created_at', FilterOperator.GREATER_THAN_OR_EQUAL, 
                          now - 24 * 3600),
            'this_week': Filter('created_at', FilterOperator.GREATER_THAN_OR_EQUAL, 
                              now - 7 * 24 * 3600),
            'this_month': Filter('created_at', FilterOperator.GREATER_THAN_OR_EQUAL, 
                               now - 30 * 24 * 3600),
            'has_messages': Filter('message_count', FilterOperator.GREATER_THAN, 0),
            'no_messages': Filter('message_count', FilterOperator.EQUALS, 0),
        })
    
    def create_filter(
        self,
        field: str,
        operator: Union[FilterOperator, str],
        value: Any,
        case_sensitive: bool = False
    ) -> Filter:
        """
        Create a single filter.
        
        Args:
            field: Field name to filter on
            operator: Filter operator
            value: Value to compare against
            case_sensitive: Whether comparison should be case sensitive
            
        Returns:
            Filter instance
        """
        if isinstance(operator, str):
            operator = FilterOperator(operator)
        
        return Filter(field, operator, value, case_sensitive)
    
    def create_filter_group(
        self,
        filters: List[Union[Filter, FilterGroup]],
        operator: Union[LogicalOperator, str] = LogicalOperator.AND
    ) -> FilterGroup:
        """
        Create a filter group.
        
        Args:
            filters: List of filters or filter groups
            operator: Logical operator to combine filters
            
        Returns:
            FilterGroup instance
        """
        if isinstance(operator, str):
            operator = LogicalOperator(operator)
        
        return FilterGroup(filters, operator)
    
    def create_time_range_filter(
        self,
        field: str,
        start_time: Optional[Union[datetime, float]] = None,
        end_time: Optional[Union[datetime, float]] = None
    ) -> FilterGroup:
        """
        Create a time range filter.
        
        Args:
            field: Time field name (e.g., 'created_at', 'updated_at')
            start_time: Start of time range
            end_time: End of time range
            
        Returns:
            FilterGroup with time range filters
        """
        filters = []
        
        if start_time is not None:
            if isinstance(start_time, datetime):
                start_time = start_time.timestamp()
            filters.append(Filter(field, FilterOperator.GREATER_THAN_OR_EQUAL, start_time))
        
        if end_time is not None:
            if isinstance(end_time, datetime):
                end_time = end_time.timestamp()
            filters.append(Filter(field, FilterOperator.LESS_THAN_OR_EQUAL, end_time))
        
        return FilterGroup(filters, LogicalOperator.AND)
    
    def create_text_search_filter(
        self,
        fields: List[str],
        query: str,
        case_sensitive: bool = False
    ) -> FilterGroup:
        """
        Create a text search filter across multiple fields.
        
        Args:
            fields: List of field names to search in
            query: Search query
            case_sensitive: Whether search should be case sensitive
            
        Returns:
            FilterGroup with text search filters
        """
        filters = []
        
        for field in fields:
            filters.append(Filter(field, FilterOperator.CONTAINS, query, case_sensitive))
        
        return FilterGroup(filters, LogicalOperator.OR)
    
    def create_role_filter(self, roles: List[str]) -> Filter:
        """Create a filter for message roles."""
        return Filter('role', FilterOperator.IN, roles)
    
    def create_content_type_filter(self, content_types: List[str]) -> FilterGroup:
        """
        Create a filter for content types (string, dict, list).
        
        Args:
            content_types: List of content types ('string', 'dict', 'list')
            
        Returns:
            FilterGroup for content type filtering
        """
        filters = []
        
        for content_type in content_types:
            if content_type == 'string':
                # Filter for string content
                filters.append(Filter('content', FilterOperator.REGEX, r'^[^{\[].*', case_sensitive=True))
            elif content_type == 'dict':
                # Filter for dict content (starts with {)
                filters.append(Filter('content', FilterOperator.REGEX, r'^\{.*', case_sensitive=True))
            elif content_type == 'list':
                # Filter for list content (starts with [)
                filters.append(Filter('content', FilterOperator.REGEX, r'^\[.*', case_sensitive=True))
        
        return FilterGroup(filters, LogicalOperator.OR)
    
    def apply_filters(
        self,
        items: List[Dict[str, Any]],
        filter_spec: Union[Filter, FilterGroup, str, Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Apply filters to a list of items.
        
        Args:
            items: List of items to filter
            filter_spec: Filter specification (Filter, FilterGroup, predefined name, or dict)
            
        Returns:
            Filtered list of items
        """
        if not items:
            return []
        
        # Convert filter_spec to Filter or FilterGroup
        filter_obj = self._parse_filter_spec(filter_spec)
        
        if filter_obj is None:
            return items
        
        # Apply filter
        return [item for item in items if filter_obj.apply(item)]
    
    def _parse_filter_spec(self, filter_spec: Union[Filter, FilterGroup, str, Dict[str, Any]]) -> Optional[Union[Filter, FilterGroup]]:
        """Parse filter specification into Filter or FilterGroup."""
        if isinstance(filter_spec, (Filter, FilterGroup)):
            return filter_spec
        
        elif isinstance(filter_spec, str):
            # Predefined filter name
            return self.predefined_filters.get(filter_spec)
        
        elif isinstance(filter_spec, dict):
            # Dictionary specification
            return self._parse_dict_filter(filter_spec)
        
        return None
    
    def _parse_dict_filter(self, filter_dict: Dict[str, Any]) -> Optional[Union[Filter, FilterGroup]]:
        """Parse dictionary filter specification."""
        if 'filters' in filter_dict:
            # FilterGroup specification
            filters = []
            for f in filter_dict['filters']:
                parsed_filter = self._parse_filter_spec(f)
                if parsed_filter:
                    filters.append(parsed_filter)
            
            operator = LogicalOperator(filter_dict.get('operator', 'and'))
            return FilterGroup(filters, operator)
        
        elif 'field' in filter_dict and 'operator' in filter_dict and 'value' in filter_dict:
            # Single Filter specification
            return Filter(
                field=filter_dict['field'],
                operator=FilterOperator(filter_dict['operator']),
                value=filter_dict['value'],
                case_sensitive=filter_dict.get('case_sensitive', False)
            )
        
        return None
    
    def create_conversation_filters(self) -> Dict[str, Union[Filter, FilterGroup]]:
        """Create common conversation filters."""
        return {
            'active': Filter('message_count', FilterOperator.GREATER_THAN, 0),
            'empty': Filter('message_count', FilterOperator.EQUALS, 0),
            'recent': Filter('updated_at', FilterOperator.GREATER_THAN_OR_EQUAL, 
                           datetime.now().timestamp() - 7 * 24 * 3600),
            'old': Filter('updated_at', FilterOperator.LESS_THAN, 
                         datetime.now().timestamp() - 30 * 24 * 3600),
        }
    
    def create_message_filters(self) -> Dict[str, Union[Filter, FilterGroup]]:
        """Create common message filters."""
        return {
            'user_messages': Filter('role', FilterOperator.EQUALS, 'user'),
            'assistant_messages': Filter('role', FilterOperator.EQUALS, 'assistant'),
            'system_messages': Filter('role', FilterOperator.EQUALS, 'system'),
            'recent_messages': Filter('timestamp', FilterOperator.GREATER_THAN_OR_EQUAL,
                                    datetime.now().timestamp() - 24 * 3600),
            'has_metadata': Filter('metadata', FilterOperator.NOT_EQUALS, None),
        }
    
    def combine_filters(
        self,
        filters: List[Union[Filter, FilterGroup]],
        operator: LogicalOperator = LogicalOperator.AND
    ) -> FilterGroup:
        """
        Combine multiple filters with a logical operator.
        
        Args:
            filters: List of filters to combine
            operator: Logical operator (AND, OR, NOT)
            
        Returns:
            Combined FilterGroup
        """
        return FilterGroup(filters, operator)
    
    def validate_filter_spec(self, filter_spec: Dict[str, Any]) -> bool:
        """
        Validate a filter specification dictionary.
        
        Args:
            filter_spec: Filter specification to validate
            
        Returns:
            True if valid, False otherwise
        """
        try:
            parsed = self._parse_dict_filter(filter_spec)
            return parsed is not None
        except (ValueError, KeyError, TypeError):
            return False 