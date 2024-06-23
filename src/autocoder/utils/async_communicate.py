import threading
from queue import Queue
from typing import Any, Callable

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class QueueCommunicate(metaclass=Singleton):
    def __init__(self):
        self.request_queue = Queue()
        self.response_queues = {}
        self.lock = threading.Lock()

    def send_event(self,request_id:str,event: Any) -> Any:
        # Create a response queue for the event
        response_queue = Queue()
        with self.lock:
            # Store the response queue for the event
            self.response_queues[event] = response_queue
        # Send the event to the request queue
        self.request_queue.put(event)
        # Wait for the response
        response = response_queue.get()
        with self.lock:
            # Remove the response queue for the event
            del self.response_queues[event]
        return response

    def consume_events(self,request_id:str, event_handler: Callable[[Any], Any]):
        while True:
            # Get the next event from the request queue
            event = self.request_queue.get()
            # Process the event
            response = event_handler(event)
            with self.lock:
                # Get the response queue for the event
                response_queue = self.response_queues.get(event)
            # Put the response in the response queue
            response_queue.put(response)
            self.request_queue.task_done()

# Global instance of AsyncCommunicate
queue_communicate = QueueCommunicate()