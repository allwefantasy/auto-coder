"""
PersistConversationManager 跨平台文件锁实现
"""

import os
import sys
import time
import contextlib
from typing import Generator
from .exceptions import LockTimeoutError


# 跨平台文件锁实现
if sys.platform == "win32":
    import msvcrt
    
    class FileLocker:
        """Windows 平台文件锁实现"""
        
        def __init__(self, lock_file: str, timeout: float = 10.0):
            self.lock_file = lock_file
            self.timeout = timeout
            self.lock_fd = None
        
        @contextlib.contextmanager
        def acquire_read_lock(self) -> Generator[None, None, None]:
            """获取读锁（共享锁）- Windows 实现"""
            self._acquire_lock(shared=True)
            try:
                yield
            finally:
                self._release_lock()
        
        @contextlib.contextmanager
        def acquire_write_lock(self) -> Generator[None, None, None]:
            """获取写锁（排他锁）- Windows 实现"""
            self._acquire_lock(shared=False)
            try:
                yield
            finally:
                self._release_lock()
        
        def _acquire_lock(self, shared: bool = False):
            """Windows 文件锁实现"""
            start_time = time.time()
            while True:
                try:
                    # 确保锁文件目录存在
                    os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
                    
                    # 打开文件用于锁定
                    self.lock_fd = open(self.lock_file, 'w+')
                    
                    # Windows 下使用 msvcrt.locking
                    # 注意：Windows 不直接支持共享锁，这里简化处理
                    msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
                    return
                    
                except (IOError, OSError):
                    if self.lock_fd:
                        self.lock_fd.close()
                        self.lock_fd = None
                    
                    if time.time() - start_time > self.timeout:
                        raise LockTimeoutError(f"Failed to acquire lock on {self.lock_file} within {self.timeout}s")
                    
                    time.sleep(0.1)
        
        def _release_lock(self):
            """释放锁"""
            if self.lock_fd:
                try:
                    msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                    self.lock_fd.close()
                except:
                    # 忽略释放时的错误
                    pass
                finally:
                    self.lock_fd = None

else:
    # Unix/Linux/Mac 系统使用 fcntl
    import fcntl
    
    class FileLocker:
        """Unix/Linux/Mac 平台文件锁实现"""
        
        def __init__(self, lock_file: str, timeout: float = 10.0):
            self.lock_file = lock_file
            self.timeout = timeout
            self.lock_fd = None
        
        @contextlib.contextmanager
        def acquire_read_lock(self) -> Generator[None, None, None]:
            """获取读锁（共享锁）- Unix/Linux/Mac 实现"""
            self._acquire_lock(fcntl.LOCK_SH)
            try:
                yield
            finally:
                self._release_lock()
        
        @contextlib.contextmanager
        def acquire_write_lock(self) -> Generator[None, None, None]:
            """获取写锁（排他锁）- Unix/Linux/Mac 实现"""
            self._acquire_lock(fcntl.LOCK_EX)
            try:
                yield
            finally:
                self._release_lock()
        
        def _acquire_lock(self, lock_type: int):
            """Unix/Linux/Mac 文件锁实现"""
            start_time = time.time()
            
            # 确保锁文件目录存在
            os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
            
            # 打开锁文件
            self.lock_fd = open(self.lock_file, 'w+')
            
            while True:
                try:
                    # 尝试获取非阻塞锁
                    fcntl.flock(self.lock_fd.fileno(), lock_type | fcntl.LOCK_NB)
                    return
                    
                except (IOError, OSError):
                    if time.time() - start_time > self.timeout:
                        self.lock_fd.close()
                        self.lock_fd = None
                        raise LockTimeoutError(f"Failed to acquire lock on {self.lock_file} within {self.timeout}s")
                    
                    time.sleep(0.1)
        
        def _release_lock(self):
            """释放锁"""
            if self.lock_fd:
                try:
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                    self.lock_fd.close()
                except:
                    # 忽略释放时的错误
                    pass
                finally:
                    self.lock_fd = None 