from threading import Lock

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
        self._queue = {}

    def add_request(self, request_id, result):
        with self._lock:
            self._queue[request_id] = result

    def get_request(self, request_id):
        with self._lock:
            return self._queue.get(request_id)

    def remove_request(self, request_id):
        with self._lock:
            return self._queue.pop(request_id, None)

    def clear(self):
        with self._lock:
            self._queue.clear()

# Global instance
request_queue = RequestQueue()