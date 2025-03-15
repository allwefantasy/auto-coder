"""
Event store implementation for storing and retrieving events.
"""

import os
import json
import time
import threading
from typing import List, Optional, Dict, Any, Iterator, Union, Callable, Tuple
from abc import ABC, abstractmethod
# import fcntl
from pathlib import Path
from readerwriterlock import rwlock

from .event_types import Event, EventType, ResponseEvent


class EventStore(ABC):
    """
    Abstract base class for event stores.
    """
    
    @abstractmethod
    def append_event(self, event: Event) -> None:
        """
        Append an event to the store.
        
        Args:
            event: The event to append
        """
        pass
    
    @abstractmethod
    def get_events(self, 
                  after_id: Optional[str] = None, 
                  event_types: Optional[List[EventType]] = None,
                  limit: Optional[int] = None) -> List[Event]:
        """
        Get events from the store with optional filtering.
        
        Args:
            after_id: Only get events after this ID
            event_types: Only get events of these types
            limit: Maximum number of events to return
            
        Returns:
            List of events matching the criteria
        """
        pass
    
    @abstractmethod
    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """
        Get a specific event by ID.
        
        Args:
            event_id: The ID of the event to retrieve
            
        Returns:
            The event if found, None otherwise
        """
        pass
    
    @abstractmethod
    def wait_for_event(self, 
                      condition: Callable[[Event], bool], 
                      timeout: Optional[float] = None) -> Optional[Event]:
        """
        Wait for an event matching the given condition.
        
        Args:
            condition: Function that takes an event and returns True if it matches
            timeout: Maximum time to wait in seconds, or None to wait indefinitely
            
        Returns:
            The matching event, or None if timeout occurs
        """
        pass

    @abstractmethod
    def truncate(self) -> None:
        """
        Clear the event store by truncating the file.
        This removes all events from the store.
        """
        pass


class JsonlEventStore(EventStore):
    """
    Event store implementation using JSONL files.
    This implementation uses reader-writer locks and file locks to ensure thread safety.
    """
    
    def __init__(self, file_path: str, flush_interval: float = 0.1):
        """
        Initialize a JSONL event store.
        
        Args:
            file_path: Path to the JSONL file
            flush_interval: How often to flush events to disk (in seconds)
        """
        self.file_path = file_path
        self.flush_interval = flush_interval
        self.rwlock = rwlock.RWLockFair()
        self._last_event_id: Optional[str] = None
        self._watchers: List[threading.Event] = []
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        # Create file if it doesn't exist
        if not os.path.exists(file_path):
            with open(file_path, 'w', encoding='utf-8') as f:
                pass
        
        # Update last event ID from file
        self._update_last_event_id()
        
        # Start a background thread to monitor for new events
        self._stop_monitoring = threading.Event()
        self._monitor_thread = threading.Thread(target=self._monitor_events, daemon=True)
        self._monitor_thread.start()
    
    def _update_last_event_id(self) -> None:
        """Update the last event ID by reading the last event from the file."""
        with self.rwlock.gen_rlock():
            try:
                with open(self.file_path, 'r', encoding='utf-8') as f:
                    # fcntl.flock(f, fcntl.LOCK_SH)
                    try:
                        # Get the last line of the file that contains a valid event
                        last_event = None
                        for line in f:
                            line = line.strip()
                            if not line:
                                continue
                            try:
                                event_data = json.loads(line)
                                if "event_type" not in event_data:
                                    continue
                                
                                if "response_to" in event_data:
                                    event = ResponseEvent.from_dict(event_data)
                                else:
                                    event = Event.from_dict(event_data)
                                
                                last_event = event
                            except json.JSONDecodeError:
                                # Skip invalid lines
                                pass
                        
                        if last_event:
                            self._last_event_id = last_event.event_id
                    finally:
                        # fcntl.flock(f, fcntl.LOCK_UN)
                        pass
            except FileNotFoundError:
                # File doesn't exist yet
                pass
    
    def _read_events_from_file(self) -> List[Event]:
        """
        Read all events from the file.
        
        Returns:
            List of all events from the file
        """
        events = []
        with open(self.file_path, 'r', encoding='utf-8') as f:                        
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event_data = json.loads(line)
                    if "event_type" not in event_data:
                        continue
                    
                    if "response_to" in event_data:
                        event = ResponseEvent.from_dict(event_data)
                    else:
                        event = Event.from_dict(event_data)
                    
                    events.append(event)
                except json.JSONDecodeError:
                    # Skip invalid lines
                    pass                    
        return events
    
    def append_event(self, event: Event) -> None:
        """
        Append an event to the store.
        
        Args:
            event: The event to append
        """
        with self.rwlock.gen_wlock():
            with open(self.file_path, 'a', encoding='utf-8') as f:
                # fcntl.flock(f, fcntl.LOCK_EX)
                try:
                    f.write(event.to_json() + '\n')
                    f.flush()
                finally:
                    # fcntl.flock(f, fcntl.LOCK_UN)
                    pass
            
            self._last_event_id = event.event_id
            
            # Notify all watchers
            for watcher in self._watchers:
                watcher.set()
    
    def get_events(self, 
                  after_id: Optional[str] = None, 
                  event_types: Optional[List[EventType]] = None,
                  limit: Optional[int] = None) -> List[Event]:
        """
        Get events from the store with optional filtering.
        
        Args:
            after_id: Only get events after this ID
            event_types: Only get events of these types
            limit: Maximum number of events to return
            
        Returns:
            List of events matching the criteria
        """
        with self.rwlock.gen_rlock():
            events = self._read_events_from_file()
            
            # Sort by timestamp
            events.sort(key=lambda e: e.timestamp)
            
            # Filter by ID
            if after_id:
                after_index = None
                for i, event in enumerate(events):
                    if event.event_id == after_id:
                        after_index = i
                        break
                
                if after_index is not None:
                    events = events[after_index + 1:]
                else:
                    events = []
            
            # Filter by event type
            if event_types:
                events = [e for e in events if e.event_type in event_types]
            
            # Apply limit
            if limit is not None and limit > 0:
                events = events[:limit]
            
            return events
    
    def get_event_by_id(self, event_id: str) -> Optional[Event]:
        """
        Get a specific event by ID.
        
        Args:
            event_id: The ID of the event to retrieve
            
        Returns:
            The event if found, None otherwise
        """
        with self.rwlock.gen_rlock():
            events = self._read_events_from_file()
            
            for event in events:
                if event.event_id == event_id:
                    return event
            
            return None
    
    def wait_for_event(self, 
                      condition: Callable[[Event], bool], 
                      timeout: Optional[float] = None) -> Optional[Event]:
        """
        Wait for an event matching the given condition.
        
        Args:
            condition: Function that takes an event and returns True if it matches
            timeout: Maximum time to wait in seconds, or None to wait indefinitely
            
        Returns:
            The matching event, or None if timeout occurs
        """
        watcher = threading.Event()
        
        # Check if we already have a matching event
        with self.rwlock.gen_rlock():
            events = self._read_events_from_file()
            
            for event in events:
                if condition(event):
                    return event
            
            # No existing event, add the watcher
            self._watchers.append(watcher)
        
        try:
            # Wait for a notification
            if watcher.wait(timeout):
                # Check for new matching events
                with self.rwlock.gen_rlock():
                    events = self._read_events_from_file()
                    
                    for event in events:
                        if condition(event):
                            return event
            
            # Timeout or no matching event
            return None
        finally:
            # Remove the watcher
            with self.rwlock.gen_wlock():
                if watcher in self._watchers:
                    self._watchers.remove(watcher)
    
    def _monitor_events(self) -> None:
        """
        Background thread to monitor for new events.
        """
        last_size = os.path.getsize(self.file_path)
        last_check = time.time()
        
        while not self._stop_monitoring.is_set():
            try:
                # Only check every flush_interval seconds
                time.sleep(self.flush_interval)
                
                current_time = time.time()
                if current_time - last_check < self.flush_interval:
                    continue
                
                last_check = current_time
                
                # Check if file has changed
                current_size = os.path.getsize(self.file_path)
                if current_size > last_size:
                    self._update_last_event_id()
                    last_size = current_size
                    
                    # Notify all watchers
                    for watcher in self._watchers:
                        watcher.set()
            except Exception:
                # Ignore any errors during monitoring
                pass
    
    def close(self) -> None:
        """
        Close the event store and stop monitoring.
        """
        self._stop_monitoring.set()
        if self._monitor_thread.is_alive():
            self._monitor_thread.join(timeout=1.0)
    
    def truncate(self) -> None:
        """
        Clear the event store by truncating the file.
        This removes all events from the store.
        """
        with self.rwlock.gen_wlock():
            # Open the file in write mode with truncation ('w')
            with open(self.file_path, 'w', encoding='utf-8') as f:
                pass  # Just open and close to truncate
            
            # Reset the last event ID
            self._last_event_id = None
            
            # Notify all watchers
            for watcher in self._watchers:
                watcher.set() 