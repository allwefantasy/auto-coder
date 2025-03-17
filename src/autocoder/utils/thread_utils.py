from functools import wraps
from typing import Any, Optional, Dict, Callable
import threading
import time
from autocoder.common.global_cancel import global_cancel, CancelRequestedException
from autocoder.common.printer import Printer
from autocoder.common.auto_coder_lang import get_message, get_message_with_format
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events import event_content as EventContentCreator
from autocoder.events.event_types import EventMetadata

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
            exception_raised = [None]  # 存储工作线程中的异常
            thread_token = token
            thread_context = context or {}
            thread_terminated = threading.Event()  # 用于标记线程是否已终止
            
            def worker():
                try:                                        
                    # 执行用户函数
                    ret = func(*args, **kwargs)
                    result.append(ret)
                except CancelRequestedException as e:
                    # 处理取消异常
                    printer.print_in_terminal("generation_cancelled")
                    exception_raised[0] = e
                except Exception as e:
                    # 存储其他异常
                    exception_raised[0] = e
                finally:
                    # 无论如何执行完毕后，重置取消标志并标记线程已终止
                    global_cancel.reset(thread_token)
                    thread_terminated.set()
            
            # Create and start thread with a meaningful name
            thread = threading.Thread(target=worker, name=f"{func.__name__}_thread")
            thread.daemon = True  # Make thread daemon so it doesn't prevent program exit
            
            try:
                thread.start()
                
                # Poll thread status with timeout to allow for interruption
                cancelled_by_keyboard = False
                max_wait_time = 30  # 最大等待时间（秒）
                wait_start_time = time.time()
                
                while thread.is_alive():
                    # 每次等待较短时间，以便能够及时响应中断
                    thread.join(0.1)
                    
                    # 检查是否已经超过最大等待时间（仅适用于已取消的情况）
                    elapsed_time = time.time() - wait_start_time
                    if cancelled_by_keyboard and elapsed_time > max_wait_time:
                        printer.print_in_terminal("force_terminating_thread")
                        break
                    
                    # 检查线程间的取消请求
                    if global_cancel.is_requested(thread_token):
                        # 传播取消请求到工作线程
                        raise CancelRequestedException(thread_token)

                # 如果工作线程出现了异常，在主线程中重新抛出
                if exception_raised[0] is not None:
                    raise exception_raised[0]
                    
                # 返回结果
                return result[0] if result else None            
                
            except KeyboardInterrupt:
                # 设置取消标志
                cancel_context = {"message": get_message("task_cancelled_by_user"), "source": "keyboard_interrupt"}
                cancel_context.update(thread_context)
                global_cancel.set(thread_token, cancel_context)
                printer.print_in_terminal("cancellation_requested")

                # 标记为键盘中断取消
                cancelled_by_keyboard = True
                wait_start_time = time.time()
                
                # 等待线程终止或检测到取消
                while thread.is_alive() and not thread_terminated.is_set():
                    thread.join(0.5)
                    elapsed_time = time.time() - wait_start_time
                    if elapsed_time > max_wait_time:
                        printer.print_in_terminal("force_raising_keyboard_interrupt")
                        break
                
                # 如果线程已终止且有异常，优先抛出该异常
                if exception_raised[0] is not None:
                    raise exception_raised[0]                                                
                
        return wrapper
    return decorator    
