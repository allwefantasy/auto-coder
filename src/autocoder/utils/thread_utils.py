from concurrent.futures import ThreadPoolExecutor, TimeoutError, CancelledError
from threading import Event
from inspect import signature
from functools import wraps
from typing import Any, Optional
import threading
import logging
import time
from autocoder.common.global_cancel import global_cancel

def run_in_raw_thread():
    """A decorator that runs a function in a separate thread and handles exceptions.
    
    Args:
        func: The function to run in a thread
        
    Returns:
        A wrapper function that executes the decorated function in a thread
        
    The decorator will:
    1. Run the function in a separate thread
    2. Handle KeyboardInterrupt properly
    3. Propagate exceptions from the thread
    4. Support function arguments
    5. Preserve function metadata
    """
    def decorator(func):

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Store thread results
            result = []
            exception = []            
            def worker():            
                try:
                    # 如果刚开始就遇到了,可能是用户中断的还没有释放
                    # 等待五秒后强行释放
                    if global_cancel.requested:
                        time.sleep(5)
                        global_cancel.reset()
                    
                    ret = func(*args, **kwargs)
                    result.append(ret)
                    global_cancel.reset()                
                except Exception as e:
                    global_cancel.reset()
                    raise
            
            # Create and start thread with a meaningful name
            thread = threading.Thread(target=worker, name=f"{func.__name__}_thread")
            thread.daemon = True  # Make thread daemon so it doesn't prevent program exit
            
            try:
                thread.start()
                while thread.is_alive():
                    thread.join(0.1)

                return result[0] if result else None            
            except KeyboardInterrupt:  
                global_cancel.set()                              
                raise KeyboardInterrupt("Task was cancelled by user")
            except Exception as e:
                global_cancel.reset()
                raise
                
        return wrapper
    return decorator    
