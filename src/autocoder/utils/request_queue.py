from threading import Lock
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from typing import Dict


class RequestValue(BaseModel):
    value: any
    last_accessed: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    class Config:
        arbitrary_types_allowed = True


class RequestQueue:
    _instance = None
    _lock = Lock()

    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        self._queue: Dict[str, RequestValue] = {}

    def close(self):
        with self._lock:
            self._queue.clear()

    def add_request(self, request_id, result):
        with self._lock:
            self._queue[request_id] = RequestValue(
                value=result, created_at=datetime.now(), last_accessed=datetime.now()
            )
        if len(self._queue) > 5000:
            self.cleanup_old_requests()

    def get_request(self, request_id):
        with self._lock:
            request_value = self._queue.get(request_id)
            if request_value:
                request_value.last_accessed = datetime.now()
                return request_value.value
            return None

    def remove_request(self, request_id):
        with self._lock:
            return self._queue.pop(request_id, None)

    def clear(self):
        with self._lock:
            self._queue.clear()

    def cleanup_old_requests(self):
        with self._lock:
            current_time = datetime.now()
            old_requests = [
                request_id
                for request_id, request_value in self._queue.items()
                if (current_time - request_value.last_accessed) > timedelta(minutes=10)
            ]
            for request_id in old_requests:
                del self._queue[request_id]
            return len(old_requests)


# Global instance
request_queue = RequestQueue()
