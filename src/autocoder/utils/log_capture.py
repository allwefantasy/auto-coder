import sys
import queue
import threading
from contextlib import contextmanager


class QueueStream:
    def __init__(self, queue):
        self.queue = queue

    def write(self, msg):
        self.queue.put(msg)

    def flush(self):
        pass


class LogCapture:
    request_logs = {}
    @staticmethod
    def get_log_capture(request_id):
        return LogCapture.request_logs.get(request_id)
    
    def __init__(self, request_id:str):
        self.log_queue = queue.Queue()    
        self.finished = False      
        self.request_logs[request_id] = self

    def run_async(self, target, args=()):
        thread = threading.Thread(target=target, args=args)
        thread.daemon = True
        thread.start()          

    @contextmanager
    def capture(self):        
        queue_stream = QueueStream(self.log_queue)
        old_stdout, old_stderr = sys.stdout, sys.stderr
        sys.stdout = sys.stderr = queue_stream        
        try:
            yield self.log_queue
        finally:
            self.finished = True
            sys.stdout, sys.stderr = old_stdout, old_stderr                        

    def get_captured_logs(self): 
        if self.finished:
            return None       
        v = []
        while not self.log_queue.empty():
            v.append(self.log_queue.get())
        return v    
