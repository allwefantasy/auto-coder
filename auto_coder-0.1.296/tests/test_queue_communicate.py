import unittest
import threading
from autocoder.utils.queue_communicate import queue_communicate


class Sender:
    def __init__(self, request_id):
        self.request_id = request_id
        
    def send_event(self, event):
        response = queue_communicate.send_event(self.request_id, event)
        print(f"Sender {self.request_id} received response: {response}")
        return response


class Consumer:
    def __init__(self, request_id):
        self.request_id = request_id
        
    def consume_events(self):
        def event_handler(event):
            response = f"Processed by {self.request_id}: {event}"
            return response

        queue_communicate.consume_events(self.request_id, event_handler)


class TestQueueCommunicate(unittest.TestCase):    
    def test_send_and_consume_events(self):
        request_id1 = "request1"
        request_id2 = "request2"
        
        sender1 = Sender(request_id1)
        sender2 = Sender(request_id2)
        consumer1 = Consumer(request_id1)
        consumer2 = Consumer(request_id2)

        # Start the consumer threads
        consumer_thread1 = threading.Thread(target=consumer1.consume_events)
        consumer_thread1.daemon = True
        consumer_thread1.start()

        consumer_thread2 = threading.Thread(target=consumer2.consume_events)
        consumer_thread2.daemon = True
        consumer_thread2.start()

        # Send events from the senders
        response1 = sender1.send_event("Event 1")
        response2 = sender2.send_event("Event 2")
        response3 = sender1.send_event("Event 3")

        # Assert the responses
        self.assertEqual(response1, "Processed by request1: Event 1")
        self.assertEqual(response2, "Processed by request2: Event 2")
        self.assertEqual(response3, "Processed by request1: Event 3")


if __name__ == "__main__":
    unittest.main()
