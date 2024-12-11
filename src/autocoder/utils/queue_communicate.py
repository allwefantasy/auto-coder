import threading
from queue import Queue
from typing import Any, Callable, Dict
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum


class CommunicateEventType(Enum):
    CODE_MERGE = "code_merge"
    CODE_GENERATE = "code_generate"
    CODE_MERGE_RESULT = "code_merge_result"
    CODE_UNMERGE_RESULT = "code_unmerge_result"
    CODE_START = "code_start"
    CODE_END = "code_end"
    CODE_GENERATE_START = "code_generate_start"
    CODE_GENERATE_END = "code_generate_end"
    CODE_HUMAN_AS_MODEL = "code_human_as_model"
    ASK_HUMAN = "ask_human"
    CODE_ERROR = "code_error"
    CODE_INDEX_BUILD_START = "code_index_build_start"
    CODE_INDEX_BUILD_END = "code_index_build_end"   
    CODE_INDEX_FILTER_START = "code_index_filter_start"
    CODE_INDEX_FILTER_END = "code_index_filter_end"
    CODE_INDEX_FILTER_FILE_SELECTED = "code_index_filter_file_selected"
    CODE_RAG_SEARCH_START = "code_rag_search_start"
    CODE_RAG_SEARCH_END = "code_rag_search_end"

TIMEOUT = 600*3
@dataclass(eq=True, frozen=True)
class CommunicateEvent:
    event_type: str
    data: str


class Singleton(type):
    _instances = {}
    _lock = threading.Lock()

    def __call__(cls, *args, **kwargs):
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class QueueCommunicate(metaclass=Singleton):
    def __init__(self):
        # Structure:
        # {
        #    "request_id_1": Queue(),
        #    "request_id_2": Queue(),
        #    ...
        # }
        self.request_queues = {}

        # Structure:
        # {
        #    "request_id_1": {
        #        event1: Queue(),
        #        event2: Queue(),
        #        ...
        #    },
        #    "request_id_2": {
        #        event1: Queue(),
        #        event2: Queue(),
        #        ...
        #    }
        # }
        self.response_queues = {}
        self.lock = threading.Lock()
        self.send_event_executor = ThreadPoolExecutor(max_workers=100)
        self.consume_event_executor = ThreadPoolExecutor(max_workers=100)

    def shutdown(self):
        self.send_event_executor.shutdown()
        self.consume_event_executor.shutdown()
        for request_queue in self.request_queues.values():
            request_queue.put(None)
        for request_id in list(self.request_queues.keys()):
            self.close(request_id)

    def close(self, request_id: str):
        with self.lock:
            if request_id in self.request_queues:
                request_queue = self.request_queues.pop(request_id)
                request_queue.put(None)
            if request_id in self.response_queues:
                self.response_queues.pop(request_id)

    def send_event(self, request_id: str, event: Any, timeout: int = TIMEOUT) -> Any:
        if not request_id:
            return None

        future = self.send_event_executor.submit(
            self._send_event_task, request_id, event
        )
        return future.result(timeout=timeout)

    def send_event_no_wait(self, request_id: str, event: Any, timeout: int = TIMEOUT) -> Any:
        if not request_id:
            return None

        future = self.send_event_executor.submit(
            self._send_event_task, request_id, event
        )
        return future

    def _send_event_task(self, request_id: str, event: Any, timeout: int = TIMEOUT) -> Any:
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
        response = response_queue.get(timeout=timeout)
        return response

    def consume_events(self, request_id: str, event_handler: Callable[[Any], Any]):

        future = self.consume_event_executor.submit(
            self._consume_events_task, request_id, event_handler
        )
        return future.result()

    def get_event(self, request_id: str):
        with self.lock:
            if request_id not in self.request_queues:
                return None
            request_queue = self.request_queues[request_id]
            response_queues = self.response_queues[request_id]

        if request_queue.empty():
            return None

        event = request_queue.get()
        return event

    def response_event(self, request_id: str, event: Any, response: Any):
        with self.lock:
            if request_id not in self.request_queues:
                return None
            request_queue = self.request_queues[request_id]
            response_queues = self.response_queues[request_id]

        with self.lock:
            response_queue = response_queues.get(event)
            response_queue.put(response)
            request_queue.task_done()

    def consume_events_no_wait(
        self, request_id: str, event_handler: Callable[[Any], Any]
    ):
        future = self.consume_event_executor.submit(
            self._consume_events_task_no_wait, request_id, event_handler
        )
        return future.result()

    def _consume_events_task(
        self, request_id: str, event_handler: Callable[[Any], Any]
    ):
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

    def _consume_events_task_no_wait(
        self, request_id: str, event_handler: Callable[[Any], Any]
    ):
        with self.lock:
            if request_id not in self.request_queues:
                return None
            request_queue = self.request_queues[request_id]
            response_queues = self.response_queues[request_id]

        if request_queue.empty():
            return None

        event = request_queue.get()
        response = event_handler(event)

        with self.lock:
            response_queue = response_queues.get(event)
            response_queue.put(response)
            request_queue.task_done()

        return response


# Global instance of AsyncCommunicate
queue_communicate = QueueCommunicate()
