from functools import wraps
from typing import Any, Optional, Dict, Callable
import threading
from autocoder.common.global_cancel import global_cancel, CancelRequestedException
from autocoder.common.printer import Printer

printer = Printer()

def run_in_raw_thread(token: Optional[str] = None, context: Optional[Dict[str, Any]] = None):
    """A decorator that runs a function in a separate thread and handles exceptions.
    
    Args:
        token (Optional[str]): Optional cancellation token for this specific thread
        context (Optional[Dict[str, Any]]): Optional context information for cancellation
        
    Returns:
        A wrapper function that executes the decorated function in a thread
        
    The decorator will:
    1. Run the function in a separate thread
    2. Handle KeyboardInterrupt properly
    3. Propagate exceptions from the thread
    4. Support function arguments
    5. Preserve function metadata
    6. Support token-based cancellation
    7. Provide context information for cancellation
    """
    def decorator(func: Callable):

        @wraps(func)
        def wrapper(*args, **kwargs):
            # Store thread results
            result = []
            thread_token = token
            thread_context = context or {}
            
            def worker():            
                try:                                        
                    # Periodically check for cancellation during execution
                    ret = func(*args, **kwargs)
                    result.append(ret)
                    global_cancel.reset(thread_token)
                except CancelRequestedException as e:
                    # Already a cancellation exception, just propagate
                    printer.print_in_terminal("generation_cancelled")
                    global_cancel.reset(thread_token)
                    raise
                except Exception as e:
                    global_cancel.reset(thread_token)
                    raise
            
            # Create and start thread with a meaningful name
            thread = threading.Thread(target=worker, name=f"{func.__name__}_thread")
            thread.daemon = True  # Make thread daemon so it doesn't prevent program exit
            
            try:
                thread.start()
                # Poll thread status with timeout to allow for interruption
                while thread.is_alive():
                    thread.join(0.1)
                    # Check for cancellation between join attempts
                    if global_cancel.is_requested(thread_token):
                        # Propagate cancellation to the worker thread
                        raise CancelRequestedException(thread_token)

                return result[0] if result else None            
            except KeyboardInterrupt:
                # Set cancellation with context on keyboard interrupt
                cancel_context = {"message": "Task was cancelled by user", "source": "keyboard_interrupt"}
                cancel_context.update(thread_context)
                global_cancel.set(thread_token, cancel_context)                              
                raise KeyboardInterrupt("Task was cancelled by user")
            except CancelRequestedException as e:
                # Re-raise cancellation exceptions with the original token/message
                raise
            except Exception as e:
                global_cancel.reset(thread_token)
                raise
                
        return wrapper
    return decorator    
