import threading

class GlobalCancel:
    def __init__(self):
        self._flag = False
        self._lock = threading.Lock()
    
    @property
    def requested(self):
        with self._lock:
            return self._flag
    
    def set(self):
        with self._lock:
            self._flag = True
    
    def reset(self):
        with self._lock:
            self._flag = False

global_cancel = GlobalCancel()