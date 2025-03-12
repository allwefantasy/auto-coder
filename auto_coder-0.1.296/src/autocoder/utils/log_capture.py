import sys
import queue
import threading
from contextlib import contextmanager
import io

class TeeStream:
    def __init__(self, stream, queue):
        self.stream = stream
        self.queue = queue

    def write(self, msg):
        self.stream.write(msg)
        self.queue.put(msg)

    def flush(self):
        self.stream.flush()

    def fileno(self):
        return self.stream.fileno()

class LogCapture:
    request_logs = {}
    
    @classmethod
    def get_log_capture(cls, request_id):
        return cls.request_logs.get(request_id)
    
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
        old_stdout, old_stderr = sys.stdout, sys.stderr
        stdout_tee = TeeStream(old_stdout, self.log_queue)
        stderr_tee = TeeStream(old_stderr, self.log_queue)
        sys.stdout = sys.stderr = stdout_tee
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
