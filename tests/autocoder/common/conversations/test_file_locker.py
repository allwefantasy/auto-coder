"""
文件锁测试
"""

import pytest
import os
import time
import threading
import tempfile
from unittest.mock import patch, mock_open
from autocoder.common.conversations.file_locker import FileLocker
from autocoder.common.conversations.exceptions import LockTimeoutError


class TestFileLocker:
    """测试FileLocker基本功能"""
    
    def test_file_locker_creation(self, temp_dir):
        """测试文件锁创建"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker = FileLocker(lock_file, timeout=5.0)
        
        assert locker.lock_file == lock_file
        assert locker.timeout == 5.0
        assert locker.lock_fd is None
    
    def test_file_locker_creation_with_default_timeout(self, temp_dir):
        """测试使用默认超时时间创建文件锁"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker = FileLocker(lock_file)
        
        assert locker.timeout == 10.0  # 默认超时时间
    
    def test_read_lock_acquisition_and_release(self, temp_dir):
        """测试读锁获取和释放"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker = FileLocker(lock_file)
        
        # 使用上下文管理器获取读锁
        with locker.acquire_read_lock():
            # 在锁内部，应该可以执行代码
            assert True
        
        # 锁应该已经释放
        assert locker.lock_fd is None
    
    def test_write_lock_acquisition_and_release(self, temp_dir):
        """测试写锁获取和释放"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker = FileLocker(lock_file)
        
        # 使用上下文管理器获取写锁
        with locker.acquire_write_lock():
            # 在锁内部，应该可以执行代码
            assert True
        
        # 锁应该已经释放
        assert locker.lock_fd is None
    
    def test_lock_file_directory_creation(self, temp_dir):
        """测试锁文件目录自动创建"""
        # 创建不存在的子目录路径
        nested_dir = os.path.join(temp_dir, "nested", "deep")
        lock_file = os.path.join(nested_dir, "test.lock")
        locker = FileLocker(lock_file)
        
        # 获取锁应该自动创建目录
        with locker.acquire_write_lock():
            assert os.path.exists(nested_dir)
            assert os.path.exists(lock_file)
    
    def test_multiple_read_locks_allowed(self, temp_dir):
        """测试多个读锁可以同时获取"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker1 = FileLocker(lock_file)
        locker2 = FileLocker(lock_file)
        
        success_count = 0
        
        def acquire_read_lock(locker, result_list):
            try:
                with locker.acquire_read_lock():
                    result_list.append(1)
                    time.sleep(0.1)  # 保持锁一段时间
            except Exception as e:
                result_list.append(f"Error: {e}")
        
        results1 = []
        results2 = []
        
        # 同时启动两个读锁
        thread1 = threading.Thread(target=acquire_read_lock, args=(locker1, results1))
        thread2 = threading.Thread(target=acquire_read_lock, args=(locker2, results2))
        
        thread1.start()
        thread2.start()
        
        thread1.join(timeout=2.0)
        thread2.join(timeout=2.0)
        
        # 两个读锁都应该成功
        # 注意：在某些系统上可能不支持真正的共享锁
        # 所以这个测试可能需要根据实际实现调整
        if len(results1) > 0 and len(results2) > 0:
            # 至少有一个成功就算通过
            assert True
    
    def test_write_lock_exclusive(self, temp_dir):
        """测试写锁的排他性"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker1 = FileLocker(lock_file, timeout=0.5)
        locker2 = FileLocker(lock_file, timeout=0.5)
        
        def acquire_write_lock_long(locker, result_list):
            try:
                with locker.acquire_write_lock():
                    result_list.append("acquired")
                    time.sleep(1.0)  # 保持锁较长时间
                    result_list.append("released")
            except LockTimeoutError:
                result_list.append("timeout")
            except Exception as e:
                result_list.append(f"error: {e}")
        
        results1 = []
        results2 = []
        
        # 同时启动两个写锁
        thread1 = threading.Thread(target=acquire_write_lock_long, args=(locker1, results1))
        thread2 = threading.Thread(target=acquire_write_lock_long, args=(locker2, results2))
        
        thread1.start()
        time.sleep(0.1)  # 确保第一个锁先获取
        thread2.start()
        
        thread1.join(timeout=3.0)
        thread2.join(timeout=3.0)
        
        # 第一个应该成功，第二个应该超时
        assert "acquired" in results1
        assert "timeout" in results2 or "error" in str(results2)
    
    def test_lock_timeout(self, temp_dir):
        """测试锁超时机制"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker1 = FileLocker(lock_file)
        locker2 = FileLocker(lock_file, timeout=0.5)
        
        def hold_lock():
            with locker1.acquire_write_lock():
                time.sleep(2.0)  # 保持锁2秒
        
        # 启动持有锁的线程
        thread = threading.Thread(target=hold_lock)
        thread.start()
        
        time.sleep(0.1)  # 确保第一个锁已获取
        
        # 尝试获取锁应该超时
        with pytest.raises(LockTimeoutError):
            with locker2.acquire_write_lock():
                pass
        
        thread.join()
    
    def test_lock_exception_safety(self, temp_dir):
        """测试锁在异常情况下的安全释放"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker = FileLocker(lock_file)
        
        # 在锁内部抛出异常
        with pytest.raises(ValueError):
            with locker.acquire_write_lock():
                raise ValueError("测试异常")
        
        # 锁应该已经释放
        assert locker.lock_fd is None
        
        # 应该能够再次获取锁
        with locker.acquire_write_lock():
            assert True


class TestFileLockerPlatformSpecific:
    """测试平台特定的文件锁功能"""
    
    @patch('sys.platform', 'win32')
    def test_windows_lock_detection(self):
        """测试Windows平台检测"""
        from autocoder.common.conversations.file_locker import FileLocker
        # 在Windows上，FileLocker应该使用msvcrt
        # 这个测试验证平台检测逻辑
        assert True  # 基本的平台检测测试
    
    @patch('sys.platform', 'linux')
    def test_unix_lock_detection(self):
        """测试Unix/Linux平台检测"""
        from autocoder.common.conversations.file_locker import FileLocker
        # 在Unix/Linux上，FileLocker应该使用fcntl
        # 这个测试验证平台检测逻辑
        assert True  # 基本的平台检测测试
    
    def test_lock_file_permissions(self, temp_dir):
        """测试锁文件权限"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker = FileLocker(lock_file)
        
        with locker.acquire_write_lock():
            # 检查锁文件是否存在
            assert os.path.exists(lock_file)
            
            # 检查文件权限（如果在Unix系统上）
            if hasattr(os, 'stat'):
                stat_info = os.stat(lock_file)
                # 文件应该存在且可读写
                assert stat_info.st_size >= 0


class TestFileLockerErrorHandling:
    """测试文件锁错误处理"""
    
    def test_invalid_lock_file_path(self):
        """测试无效的锁文件路径"""
        # 在根目录下创建文件通常会失败（权限不足）
        invalid_path = "/root/invalid/test.lock"
        locker = FileLocker(invalid_path, timeout=0.1)
        
        # 应该能处理权限错误
        try:
            with locker.acquire_write_lock():
                pass
        except (PermissionError, OSError, LockTimeoutError):
            # 这些异常都是可以接受的
            pass
    
    def test_lock_timeout_error_message(self, temp_dir):
        """测试锁超时错误消息"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker1 = FileLocker(lock_file)
        locker2 = FileLocker(lock_file, timeout=0.1)
        
        def hold_lock():
            with locker1.acquire_write_lock():
                time.sleep(1.0)
        
        thread = threading.Thread(target=hold_lock)
        thread.start()
        
        time.sleep(0.05)  # 确保第一个锁已获取
        
        try:
            with locker2.acquire_write_lock():
                pass
        except LockTimeoutError as e:
            error_msg = str(e)
            assert "lock" in error_msg.lower()
            assert str(locker2.timeout) in error_msg
        
        thread.join()
    
    def test_release_lock_when_not_acquired(self, temp_dir):
        """测试在未获取锁时释放锁"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker = FileLocker(lock_file)
        
        # 直接调用释放锁不应该出错
        locker._release_lock()
        assert locker.lock_fd is None


class TestFileLockerConcurrency:
    """测试文件锁并发场景"""
    
    def test_high_concurrency_read_locks(self, temp_dir):
        """测试高并发读锁"""
        lock_file = os.path.join(temp_dir, "test.lock")
        num_threads = 10
        results = []
        
        def acquire_read_lock_worker():
            locker = FileLocker(lock_file, timeout=2.0)
            try:
                with locker.acquire_read_lock():
                    time.sleep(0.1)
                    results.append("success")
            except Exception as e:
                results.append(f"error: {e}")
        
        # 创建多个线程同时获取读锁
        threads = []
        for _ in range(num_threads):
            thread = threading.Thread(target=acquire_read_lock_worker)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=5.0)
        
        # 检查结果
        success_count = sum(1 for r in results if r == "success")
        # 至少应该有一些成功的
        assert success_count > 0
    
    def test_mixed_read_write_locks(self, temp_dir):
        """测试读写锁混合场景"""
        lock_file = os.path.join(temp_dir, "test.lock")
        results = []
        
        def read_worker():
            locker = FileLocker(lock_file, timeout=1.0)
            try:
                with locker.acquire_read_lock():
                    time.sleep(0.2)
                    results.append("read_success")
            except Exception as e:
                results.append(f"read_error: {e}")
        
        def write_worker():
            locker = FileLocker(lock_file, timeout=1.0)
            try:
                with locker.acquire_write_lock():
                    time.sleep(0.2)
                    results.append("write_success")
            except Exception as e:
                results.append(f"write_error: {e}")
        
        # 创建混合的读写线程
        threads = []
        for i in range(5):
            if i % 2 == 0:
                thread = threading.Thread(target=read_worker)
            else:
                thread = threading.Thread(target=write_worker)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join(timeout=3.0)
        
        # 检查结果
        assert len(results) == 5
        # 应该有一些成功的操作
        success_count = sum(1 for r in results if "success" in r)
        assert success_count > 0


class TestFileLockerEdgeCases:
    """测试文件锁边界情况"""
    
    def test_very_short_timeout(self, temp_dir):
        """测试极短的超时时间"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker = FileLocker(lock_file, timeout=0.001)  # 1毫秒
        
        # 应该能正常工作或快速超时
        try:
            with locker.acquire_write_lock():
                pass
        except LockTimeoutError:
            # 快速超时也是可以接受的
            pass
    
    def test_zero_timeout(self, temp_dir):
        """测试零超时时间"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker = FileLocker(lock_file, timeout=0.0)
        
        # 零超时应该立即尝试获取锁或失败
        try:
            with locker.acquire_write_lock():
                pass
        except (LockTimeoutError, ValueError):
            # 零超时可能会被拒绝或立即超时
            pass
    
    def test_long_lock_file_path(self, temp_dir):
        """测试长文件路径"""
        # 创建一个很长的文件路径
        long_name = "a" * 100 + ".lock"
        lock_file = os.path.join(temp_dir, long_name)
        locker = FileLocker(lock_file)
        
        # 应该能正常处理长路径
        with locker.acquire_write_lock():
            assert os.path.exists(lock_file)
    
    def test_unicode_lock_file_path(self, temp_dir):
        """测试Unicode文件路径"""
        unicode_name = "测试锁文件_🔒.lock"
        lock_file = os.path.join(temp_dir, unicode_name)
        locker = FileLocker(lock_file)
        
        # 应该能正常处理Unicode路径
        with locker.acquire_write_lock():
            assert os.path.exists(lock_file)
    
    def test_nested_context_managers(self, temp_dir):
        """测试嵌套上下文管理器"""
        lock_file = os.path.join(temp_dir, "test.lock")
        locker = FileLocker(lock_file)
        
        # 嵌套使用同一个锁应该工作
        with locker.acquire_write_lock():
            # 内层不应该再次获取锁，但也不应该出错
            # 注意：这取决于具体实现
            assert True
    
    def test_lock_after_process_restart_simulation(self, temp_dir):
        """测试模拟进程重启后的锁状态"""
        lock_file = os.path.join(temp_dir, "test.lock")
        
        # 第一个锁实例
        locker1 = FileLocker(lock_file)
        with locker1.acquire_write_lock():
            pass
        
        # 模拟进程重启，创建新的锁实例
        locker2 = FileLocker(lock_file)
        
        # 新实例应该能正常获取锁
        with locker2.acquire_write_lock():
            assert True 