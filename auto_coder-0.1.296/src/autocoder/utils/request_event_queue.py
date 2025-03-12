from threading import Lock
from datetime import datetime, timedelta
from typing import Dict
from collections import deque
from pydantic import BaseModel, Field
from typing import Any

class RequestEventQueue:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._queue: Dict[str, deque] = {}
        self._last_accessed: Dict[str, datetime] = {}

    def add_event(self, request_id, event):
        with self._lock:
            if request_id not in self._queue:
                self._queue[request_id] = deque()
                self._last_accessed[request_id] = datetime.now()
            self._queue[request_id].append(event)
            self._last_accessed[request_id] = datetime.now()
        if len(self._queue) > 5000:
            self.cleanup_old_requests()

    def get_events(self, request_id):
        with self._lock:
            if request_id in self._queue:
                self._last_accessed[request_id] = datetime.now()
                return self._queue[request_id]
            return None

    def remove_request(self, request_id):
        with self._lock:
            self._queue.pop(request_id, None)
            self._last_accessed.pop(request_id, None)

    def clear(self):
        with self._lock:
            self._queue.clear()
            self._last_accessed.clear()

    def cleanup_old_requests(self):
        with self._lock:
            current_time = datetime.now()
            old_requests = [
                request_id
                for request_id, last_accessed in self._last_accessed.items()
                if (current_time - last_accessed) > timedelta(minutes=10)
            ]
            for request_id in old_requests:
                del self._queue[request_id]
                del self._last_accessed[request_id]
            return len(old_requests)


# Global instance
request_event_queue = RequestEventQueue()