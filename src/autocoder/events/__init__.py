"""
Event handling system for autocoder.
This module provides a way for two systems to communicate through events.
"""

from .event_store import EventStore, JsonlEventStore
from .event_types import Event, EventType, ResponseEvent
from .event_manager import EventManager
from .event_manager_singleton import EventManagerSingleton, get_event_manager
from .event_content import (
    BaseEventContent, StreamContent, ResultContent, 
    AskUserContent, UserResponseContent, CodeContent,
    MarkdownContent, ErrorContent, CompletionContent, ContentType, StreamState,
    create_stream_thinking, create_stream_content,
    create_result, create_ask_user, create_user_response,
    create_completion, create_error
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
    
    # Singleton
    "EventManagerSingleton",
    "get_event_manager",
    
    # Content models
    "BaseEventContent",
    "StreamContent",
    "ResultContent",
    "AskUserContent", 
    "UserResponseContent",
    "CodeContent",
    "MarkdownContent",
    "ErrorContent",
    "CompletionContent",
    
    # Enums
    "ContentType",
    "StreamState",
    
    # Factory functions
    "create_stream_thinking",
    "create_stream_content",
    "create_result",
    "create_ask_user",
    "create_user_response",
    "create_completion",
    "create_error"
] 