"""
Event handling system for autocoder.
This module provides a way for two systems to communicate through events.
"""

from .event_store import EventStore, JsonlEventStore
from .event_types import Event, EventType, ResponseEvent
from .event_manager import EventManager
from .event_content import (
    BaseEventContent, StreamContent, ResultContent, 
    AskUserContent, UserResponseContent, CodeContent,
    MarkdownContent, ErrorContent, ContentType, StreamState,
    create_stream_thinking, create_stream_content,
    create_result, create_ask_user, create_user_response
)

__all__ = [
    # Event store
    "EventStore", 
    "JsonlEventStore",
    
    # Event types
    "Event",
    "EventType",
    "ResponseEvent",
    "EventManager",
    
    # Content models
    "BaseEventContent",
    "StreamContent",
    "ResultContent",
    "AskUserContent", 
    "UserResponseContent",
    "CodeContent",
    "MarkdownContent",
    "ErrorContent",
    
    # Enums
    "ContentType",
    "StreamState",
    
    # Factory functions
    "create_stream_thinking",
    "create_stream_content",
    "create_result",
    "create_ask_user",
    "create_user_response"
] 