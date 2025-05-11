"""
Event manager for handling events between System A and System B.
"""
from loguru import logger
import os
import time
import threading
from typing import Optional, List, Dict, Any, Callable, Union, TypeVar, Generic

from .event_store import EventStore, JsonlEventStore
from .event_types import Event, EventType, ResponseEvent

T = TypeVar('T')


class EventManager:
    """
    Manager for handling events between two systems.
    System A writes events and can be blocked by special events.
    System B reads events and can respond to special events.
    """
    
    def __init__(self, event_store: EventStore):
        """
        Initialize an event manager.
        
        Args:
            event_store: The event store to use
        """
        self.event_store = event_store        
        self._last_read_event_id: Optional[str] = self.event_store._last_event_id
        self._blocking_events: Dict[str, threading.Event] = {}
        self._response_callbacks: Dict[str, Callable[[str], None]] = {}
    
    @classmethod
    def create(cls, file_path: str) -> "EventManager":
        """
        Create an event manager with a JSONL event store.
        
        Args:
            file_path: Path to the JSONL file
            
        Returns:
            An initialized event manager
        """
        store = JsonlEventStore(file_path)
        return cls(store)
    
    def write_result(self, content: Union[Dict[str, Any], Any], metadata: Dict[str, Any] = {}) -> Event:
        """
        Write a result event.
        
        Args:
            content: The content of the result
            metadata: The metadata of the result
        Returns:
            The created event
        """
        if not isinstance(content, dict):
            content = content.to_dict()
        event = Event(event_type=EventType.RESULT, content=content, metadata=metadata)
        self.event_store.append_event(event)
        return event
    
    def write_completion(self, content: Union[Dict[str, Any], Any], metadata: Dict[str, Any] = {}) -> Event:
        """
        Write a completion event.
        
        Args:
            content: The content of the completion (CompletionContent or dict)
            
        Returns:
            The created event
        """
        if not isinstance(content, dict):
            content = content.to_dict()
        event = Event(event_type=EventType.COMPLETION, content=content, metadata=metadata)
        self.event_store.append_event(event)
        return event
    
    def write_error(self, content: Union[Dict[str, Any], Any], metadata: Dict[str, Any] = {}) -> Event:
        """
        Write an error event.
        
        Args:
            content: The content of the error (ErrorContent or dict)
            
        Returns:
            The created event
        """
        if not isinstance(content, dict):
            content = content.to_dict()
        event = Event(event_type=EventType.ERROR, content=content, metadata=metadata)
        self.event_store.append_event(event)
        return event
    
    def write_stream(self, content: Union[Dict[str, Any], Any], metadata: Dict[str, Any] = {}) -> Event:
        """
        Write a stream event.
        
        Args:
            content: The content of the stream
            metadata: The metadata of the stream
        Returns:
            The created event
        """
        if not isinstance(content, dict):
            content = content.to_dict()
        event = Event(event_type=EventType.STREAM, content=content, metadata=metadata)
        self.event_store.append_event(event)
        return event
    
    def ask_user(self, 
                prompt: str, 
                options: Optional[List[str]] = None,
                callback: Optional[Callable[[str], None]] = None) -> str:
        """
        Ask the user a question and wait for response.
        This method blocks until a response is received.
        
        Args:
            prompt: The question to ask
            options: Optional list of valid responses
            callback: Optional callback function that will be called with the response
            
        Returns:
            The user's response
        """
        logger.debug(f"ask_user called with prompt: {prompt}")
        content = {"prompt": prompt}
        if options:
            content["options"] = options
        
        event = Event(event_type=EventType.ASK_USER, content=content)
        logger.debug(f"Created ASK_USER event with ID: {event.event_id}")
        
        # Register a blocking event
        blocker = threading.Event()        
        self.event_store.append_event(event)            
        self._blocking_events[event.event_id] = blocker
        logger.info(f"ASK_USER: {self} {self.event_store.file_path} self._blocking_events: {self._blocking_events}")
        if callback:
            self._response_callbacks[event.event_id] = callback
            logger.debug(f"Registered callback for event: {event.event_id}")
        
        # Wait for response
        logger.debug(f"Waiting for response to event: {event.event_id}")
        
        # 无限等待响应，不设超时
        wait_result = blocker.wait(timeout=60.0*60)  # 设置一个较长的超时时间（60秒）
        
        if not wait_result:
            logger.warning(f"Timeout waiting for response to event: {event.event_id}")
            return ""
            
        logger.debug(f"Received signal that response is available for: {event.event_id}")
        
        # Get the response event
        def is_response(e: Event) -> bool:
            return (isinstance(e, ResponseEvent) and 
                    e.event_type == EventType.USER_RESPONSE and 
                    e.response_to == event.event_id)
        
        response_event = self.event_store.wait_for_event(is_response, timeout=1.0)
        
        # 获取响应内容
        response = ""
        if response_event and "response" in response_event.content:
            response = response_event.content["response"]
            logger.debug(f"Retrieved response: '{response}' from event: {response_event.event_id}")
        else:
            logger.warning("No valid response found in event store")
        
        # 清理资源（移到这里确保在获取响应后才清理）        
        if event.event_id in self._blocking_events:
            del self._blocking_events[event.event_id]
            logger.debug(f"Clean up blocker for event: {event.event_id}")
        else:
            logger.debug(f"No blocker found for event: {event.event_id} during cleanup")
            
            # 注意：回调不在这里清理，而是在respond_to_user中清理
            # 这样回调函数仍然可用

        return response
    
    def respond_to_user(self, ask_event_id: str, response: str) -> ResponseEvent:
        """
        Respond to a user question.
        
        Args:
            ask_event_id: ID of the ASK_USER event
            response: The response to provide
            
        Returns:
            The created response event
        """
        logger.info(f"respond_to_user called for event: {ask_event_id} with response: '{response}'")
        
        # 创建响应事件
        event = ResponseEvent(
            event_type=EventType.USER_RESPONSE,
            content={"response": response},
            response_to=ask_event_id
        )
        
        # 存储响应事件
        self.event_store.append_event(event)
        logger.info(f"Response event created and stored with ID: {event.event_id}")
                
        # 获取回调和阻塞器
        callback = None
                
        # 检查是否有回调
        if ask_event_id in self._response_callbacks:
            callback = self._response_callbacks[ask_event_id]
            # 暂时不删除回调，确保不会丢失
            logger.info(f"Retrieved callback for event: {ask_event_id}")
        else:
            logger.info(f"No callback found for event: {ask_event_id}")
                            
        
        # 如果找到了回调，执行它
        if callback:
            try:
                logger.info(f"Executing callback for event: {ask_event_id}")
                callback(response)
                logger.info(f"Callback execution completed for event: {ask_event_id}")
                                
                if ask_event_id in self._response_callbacks:
                    del self._response_callbacks[ask_event_id]
            except Exception as e:
                logger.error(f"Error in response callback: {e}")   

        # 检查是否存在对应的阻塞事件        
        logger.info(f"RESPONSD_TO_USER: {self} {self.event_store.file_path} self._blocking_events: {self._blocking_events}")
        if ask_event_id in self._blocking_events:
            self._blocking_events[ask_event_id].set()
            logger.info(f"Unblocked event: {ask_event_id}")
        else:
            logger.warning(f"No blocking event found for event_id: {ask_event_id}")
        
        return event
    
    def read_events(self, 
                   event_types: Optional[List[EventType]] = None,
                   block: bool = False,
                   timeout: Optional[float] = None) -> List[Event]:
        """
        Read events from the store.
        
        Args:
            event_types: Only get events of these types
            block: Whether to block until new events are available
            timeout: Maximum time to wait if blocking
            
        Returns:
            List of events
        """        
        events = self.event_store.get_events(
            after_id=self._last_read_event_id,
            event_types=event_types
        )
        
        if events:
            self._last_read_event_id = events[-1].event_id
            return events
        
        # No events and not blocking
        if not block:
            return []
        
        # Wait for new events
        def is_new_event(e: Event) -> bool:
            if event_types and e.event_type not in event_types:
                return False
                        
            return self._last_read_event_id is None or e.event_id != self._last_read_event_id
        
        event = self.event_store.wait_for_event(is_new_event, timeout=timeout)
        
        if event:            
            events = self.event_store.get_events(
                after_id=self._last_read_event_id,
                event_types=event_types
            )
            
            if events:
                self._last_read_event_id = events[-1].event_id
                return events
        
        return []
        
    
    def close(self) -> None:
        """
        Close the event manager and its event store.
        """
        # Unblock any waiting threads        
        for blocker in self._blocking_events.values():
            blocker.set()
        
        # Close the event store
        if isinstance(self.event_store, JsonlEventStore):
            self.event_store.close()

    def truncate(self) -> None:
        """
        Clear all events from the event store.
        This truncates the underlying file and resets the last read event ID.
        
        Warning: This operation cannot be undone and will permanently delete all events.
        """
        if not hasattr(self.event_store, 'truncate'):
            raise NotImplementedError("The current event store does not support truncation")
        
        # Reset the last read event ID
        self._last_read_event_id = None
        
        # Clear blocking events and callbacks
        self._blocking_events.clear()
        self._response_callbacks.clear()
        
        # Truncate the store
        self.event_store.truncate()
        
        logger.debug("Event store has been truncated") 