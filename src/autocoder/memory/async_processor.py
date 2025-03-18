"""
异步处理器 - 处理异步任务执行
"""

from concurrent.futures import ThreadPoolExecutor, wait
from typing import Dict, List, Optional, Any, Callable
from loguru import logger as global_logger
import sys
import time

class AsyncProcessor:
    """
    AsyncProcessor负责异步执行任务，并提供任务状态管理。
    使用线程池实现并发处理。
    """
    
    def __init__(self, max_workers: int = 3):
        """
        初始化异步处理器
        
        Args:
            max_workers: 最大工作线程数
        """
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.futures = {}  # 使用字典存储futures，以便跟踪
        self.results = {}  # 存储任务结果
        # 创建专用的 logger 实例
        self.logger = global_logger.bind(name="AsyncProcessor")
        
    def schedule(self, func: Callable, task_id: str, *args, **kwargs) -> str:
        """
        调度异步任务
        
        Args:
            func: 要执行的函数
            task_id: 任务ID
            *args, **kwargs: 传递给函数的参数
            
        Returns:
            str: 任务ID
        """
        try:
            future = self.executor.submit(func, task_id, *args, **kwargs)
            self.futures[task_id] = future
            return task_id
        except Exception as e:
            self.logger.error(f"Error scheduling task {task_id}: {e}")
            raise
        
    def cancel_task(self, task_id: str) -> bool:
        """
        取消任务，如果任务正在运行则尝试取消
        
        Args:
            task_id: 任务ID
            
        Returns:
            bool: 是否成功取消
        """
        if task_id in self.futures:
            return self.futures[task_id].cancel()
        return False
    
    def get_task_status(self, task_id: str) -> str:
        """
        获取任务状态
        
        Args:
            task_id: 任务ID
            
        Returns:
            str: 任务状态
        """
        if task_id not in self.futures:
            return "unknown"
        
        future = self.futures[task_id]
        if future.running():
            return "running"
        if future.cancelled():
            return "cancelled"
        if future.done():
            if future.exception():
                return "failed"
            return "completed"
        return "pending"
        
    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> str:
        """
        等待特定任务完成
        
        Args:
            task_id: 任务ID
            timeout: 超时时间（秒）
            
        Returns:
            str: 任务状态
        """
        if task_id not in self.futures:
            return "unknown"
        
        try:
            future = self.futures[task_id]
            future.result(timeout=timeout)
            return "completed"
        except TimeoutError:
            return "timeout"
        except Exception as e:
            self.logger.error(f"Error in task {task_id}: {e}")
            return "failed"
            
    def wait_all(self, timeout: Optional[float] = None):
        """
        等待所有任务完成
        
        Args:
            timeout: 超时时间（秒）
            
        Returns:
            tuple: (已完成任务, 未完成任务)
        """
        return wait(list(self.futures.values()), timeout=timeout)
        
    def shutdown(self, wait: bool = True):
        """
        关闭执行器
        
        Args:
            wait: 是否等待所有任务完成
        """
        self.executor.shutdown(wait=wait)
        
    def get_task_info(self, task_id: str) -> Dict[str, Any]:
        """
        获取任务详细信息
        
        Args:
            task_id: 任务ID
            
        Returns:
            Dict: 任务信息
        """
        status = self.get_task_status(task_id)
        info = {
            "task_id": task_id,
            "status": status,
            "start_time": time.time(),  # 这里应该是实际的启动时间，但我们没有保存
        }
        
        if status == "completed" and task_id in self.results:
            info["result"] = self.results[task_id]
        elif status == "failed" and task_id in self.futures:
            try:
                # 获取异常信息
                future = self.futures[task_id]
                if future.done():
                    info["error"] = str(future.exception())
            except Exception:
                pass
                
        return info 