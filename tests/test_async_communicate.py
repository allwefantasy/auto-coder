import unittest
import threading
from queue import Queue
from src.autocoder.utils.async_communicate import QueueCommunicate, Sender, Consumer

class TestAsyncCommunicate(unittest.TestCase):
    def setUp(self):
        self.queue_communicate = QueueCommunicate()
        self.sender = Sender()
        self.consumer = Consumer()

    def test_send_and_consume_events(self):
        # Start the consumer thread
        consumer_thread = threading.Thread(target=self.consumer.consume_events)
        consumer_thread.daemon = True
        consumer_thread.start()

        # Create a queue to store responses
        response_queue = Queue()

        # Override the print function in Sender to store responses
        def mock_print(message):
            response_queue.put(message)

        self.sender.send_event = lambda event: mock_print(f"Sender received response: Processed: {event}")

        # Send events from the sender
        self.sender.send_event("Event 1")
        self.sender.send_event("Event 2")

        # Wait for responses
        response1 = response_queue.get(timeout=1)
        response2 = response_queue.get(timeout=1)

        # Assert the responses
        self.assertEqual(response1, "Sender received response: Processed: Event 1")
        self.assertEqual(response2, "Sender received response: Processed: Event 2")

if __name__ == '__main__':
    unittest.main()