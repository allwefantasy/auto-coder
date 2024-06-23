import threading
from queue import Queue
from typing import Any, Callable, Dict
import time
from concurrent.futures import ThreadPoolExecutor


class Singleton:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        pass


class QueueCommunicate(metaclass=Singleton):
    def __init__(self):
        self.request_queues = {}
        self.response_queues = {}
        self.lock = threading.Lock()
        self.send_event_executor = ThreadPoolExecutor(max_workers=10)
        self.consume_event_executor = ThreadPoolExecutor(max_workers=10)

    def send_event(self, request_id: str, event: Any) -> Any:
        future = self.send_event_executor.submit(self._send_event_task, request_id, event)
        return future.result()

    def _send_event_task(self, request_id: str, event: Any) -> Any:
        with self.lock:
            if request_id not in self.request_queues:
                self.request_queues[request_id] = Queue()
                self.response_queues[request_id] = {}

        with self.lock:
            request_queue = self.request_queues[request_id]
            response_queues = self.response_queues[request_id]
            response_queue = Queue()
            response_queues[event] = response_queue

        request_queue.put(event)
        response = response_queue.get()

        with self.lock:
            del response_queues[event]

        return response

    def consume_events(self, request_id: str, event_handler: Callable[[Any], Any]):
        
        future = self.consume_event_executor.submit(self._consume_events_task, request_id, event_handler)
        return future.result()

    def _consume_events_task(self, request_id: str, event_handler: Callable[[Any], Any]):
        while True:
            with self.lock:
                if request_id not in self.request_queues:
                    time.sleep(0.001)
                    continue
                request_queue = self.request_queues[request_id]
                response_queues = self.response_queues[request_id]

            event = request_queue.get()
            response = event_handler(event)

            with self.lock:
                response_queue = response_queues.get(event)
                response_queue.put(response)
                request_queue.task_done()


# Global instance of AsyncCommunicate
queue_communicate = QueueCommunicate()
