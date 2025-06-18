"""
Search and filtering module for conversations.

This module provides text search and filtering capabilities for conversations
and messages, supporting full-text search, keyword matching, and complex
filtering operations.
"""

from .text_searcher import TextSearcher
from .filter_manager import FilterManager

__all__ = [
    'TextSearcher',
    'FilterManager'
] 