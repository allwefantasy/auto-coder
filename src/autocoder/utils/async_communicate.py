import threading
from queue import Queue
from typing import Any, Callable

class Singleton(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]

class AsyncCommunicate(metaclass=Singleton):
    def __init__(self):
        self.request_queue = Queue()
        self.response_queues = {}
        self.lock = threading.Lock()

    def send_event(self, event: Any) -> Any:
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

    def consume_events(self, event_handler: Callable[[Any], Any]):
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
communicate = AsyncCommunicate()

class Sender:
    def send_event(self, event):
        response = communicate.send_event(event)
        print(f"Sender received response: {response}")

class Consumer:
    def consume_events(self):
        def event_handler(event):
            response = f"Processed: {event}"
            return response

        communicate.consume_events(event_handler)

def main():
    sender = Sender()
    consumer = Consumer()

    # Start the consumer thread
    consumer_thread = threading.Thread(target=consumer.consume_events)
    consumer_thread.daemon = True
    consumer_thread.start()

    # Send events from the sender
    sender.send_event("Event 1")
    sender.send_event("Event 2")

if __name__ == "__main__":
    main()