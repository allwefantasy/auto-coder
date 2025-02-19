from concurrent.futures import ThreadPoolExecutor, TimeoutError, CancelledError
from threading import Event
from inspect import signature
from functools import wraps
from typing import Any, Optional
import threading
import logging
import time
from autocoder.common.global_cancel import global_cancel

class CancellationRequested(Exception):
    """Raised when a task is requested to be cancelled."""
    pass


def run_in_thread(timeout: Optional[float] = None):
    """Decorator that runs a function in a thread with signal handling.
    
    Args:
        timeout (float, optional): Maximum time to wait for thread completion in seconds.
            If None, will wait indefinitely.
            
    The decorated function will run in a separate thread and can be interrupted by
    signals like Ctrl+C (KeyboardInterrupt). When interrupted, it will log the event
    and clean up gracefully.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(func, *args, **kwargs)
                start_time = time.time()
                
                while True:
                    try:
                        # 使用较短的超时时间进行轮询，确保能够响应中断信号
                        poll_timeout = 0.1
                        if timeout is not None:
                            remaining = timeout - (time.time() - start_time)
                            if remaining <= 0:
                                future.cancel()
                                raise TimeoutError(f"Timeout after {timeout}s in {func.__name__}")
                            poll_timeout = min(poll_timeout, remaining)
                            
                        try:
                            return future.result(timeout=poll_timeout)
                        except TimeoutError:
                            continue  # 继续轮询
                            
                    except KeyboardInterrupt:
                        logging.warning("KeyboardInterrupt received, attempting to cancel task...")
                        future.cancel()
                        raise
                    except Exception as e:
                        logging.error(f"Error occurred in thread: {str(e)}")
                        raise
        return wrapper
    return decorator

def run_in_thread_with_cancel(timeout: Optional[float] = None):
    """Decorator that runs a function in a thread with explicit cancellation support.
    
    Args:
        timeout (float, optional): Maximum time to wait for thread completion in seconds.
            If None, will wait indefinitely.
            
    The decorated function MUST accept 'cancel_event' as its first parameter.
    This cancel_event is a threading.Event object that can be used to check if
    cancellation has been requested.
    
    The decorated function can be called with an external cancel_event passed as a keyword argument.
    If not provided, a new Event will be created.
    
    Example:
        @run_in_thread_with_cancel(timeout=10)
        def long_task(cancel_event, arg1, arg2):
            while not cancel_event.is_set():
                # do work
                if cancel_event.is_set():
                    raise CancellationRequested()
                    
        # 使用外部传入的cancel_event
        external_cancel = Event()
        try:
            result = long_task(arg1, arg2, cancel_event=external_cancel)
        except CancelledError:
            print("Task was cancelled")
            
        # 在其他地方取消任务
        external_cancel.set()
    """
    def decorator(func):
        # 检查函数签名
        sig = signature(func)
        params = list(sig.parameters.keys())
        if not params or params[0] != 'cancel_event':
            raise ValueError(
                f"Function {func.__name__} must have 'cancel_event' as its first parameter. "
                f"Current parameters: {params}"
            )
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 从kwargs中提取或创建cancel_event
            cancel_event = kwargs.pop('cancel_event', None) or Event()
            
            def cancellable_task():
                try:
                    return func(cancel_event, *args, **kwargs)
                except CancellationRequested:
                    logging.info(f"Task {func.__name__} was cancelled")
                    raise
                except Exception as e:
                    logging.error(f"Error in {func.__name__}: {str(e)}")
                    raise
            
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(cancellable_task)
                start_time = time.time()
                
                while True:
                    try:
                        # 使用较短的超时时间进行轮询，确保能够响应中断信号
                        poll_timeout = 0.1
                        if timeout is not None:
                            remaining = timeout - (time.time() - start_time)
                            if remaining <= 0:
                                cancel_event.set()
                                future.cancel()
                                raise TimeoutError(f"Timeout after {timeout}s in {func.__name__}")
                            poll_timeout = min(poll_timeout, remaining)
                            
                        try:
                            return future.result(timeout=poll_timeout)
                        except TimeoutError:
                            continue  # 继续轮询
                            
                    except KeyboardInterrupt:
                        logging.warning(f"KeyboardInterrupt received, cancelling {func.__name__}...")
                        cancel_event.set()
                        future.cancel()
                        raise CancelledError("Task cancelled by user")
                    except CancellationRequested:
                        logging.info(f"Task {func.__name__} was cancelled")
                        raise CancelledError("Task cancelled by request")
                    except Exception as e:
                        logging.error(f"Error occurred in thread: {str(e)}")
                        raise
                        
        return wrapper
    return decorator


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
