import pytest
import os
import json
import sqlite3
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, MagicMock

from autocoder.common.file_checkpoint.store import FileChangeStore
from autocoder.common.file_checkpoint.models import ChangeRecord

@pytest.fixture
def temp_test_dir():
    """提供一个临时的测试目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def temp_store_dir():
    """提供一个临时的存储目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_change_record():
    """创建一个用于测试的变更记录"""
    return ChangeRecord.create(
        file_path="test.py",
        backup_id="backup123",
        is_new=False,
        is_deletion=False,
        group_id="group456"
    )

class TestFileChangeStore:
    """FileChangeStore类的单元测试"""
    
    def test_init_with_custom_dir(self, temp_store_dir):
        """测试使用自定义目录初始化"""
        store = FileChangeStore(store_dir=temp_store_dir)
        
        assert store.store_dir == temp_store_dir
        assert os.path.exists(temp_store_dir)
        assert os.path.exists(os.path.join(temp_store_dir, "changes.db"))
    
    def test_init_with_default_dir(self, monkeypatch):
        """测试使用默认目录初始化"""
        # 创建一个临时主目录
        temp_home = tempfile.mkdtemp()
        try:
            # 模拟用户主目录
            monkeypatch.setattr(os.path, 'expanduser', lambda path: temp_home)
            
            store = FileChangeStore()
            
            expected_dir = os.path.join(temp_home, ".autocoder", "changes")
            assert store.store_dir == expected_dir
            assert os.path.exists(expected_dir)
            assert os.path.exists(os.path.join(expected_dir, "changes.db"))
        finally:
            shutil.rmtree(temp_home)
    
    def test_save_change(self, temp_store_dir, sample_change_record):
        """测试保存变更记录"""
        store = FileChangeStore(store_dir=temp_store_dir)
        
        # 保存变更记录
        change_id = store.save_change(sample_change_record)
        
        # 检查返回的变更ID
        assert change_id == sample_change_record.change_id
        
        # 检查数据库中是否存在该记录
        conn = sqlite3.connect(os.path.join(temp_store_dir, "changes.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM changes WHERE change_id = ?", (change_id,))
        row = cursor.fetchone()
        conn.close()
        
        assert row is not None
        assert row[0] == change_id  # change_id
        assert row[1] == sample_change_record.timestamp  # timestamp
        assert row[2] == sample_change_record.file_path  # file_path
        assert row[3] == sample_change_record.backup_id  # backup_id
        assert row[4] == 0  # is_new (转为int)
        assert row[5] == 0  # is_deletion (转为int)
        assert row[6] == sample_change_record.group_id  # group_id
    
    def test_get_change(self, temp_store_dir, sample_change_record):
        """测试获取变更记录"""
        store = FileChangeStore(store_dir=temp_store_dir)
        
        # 保存变更记录
        change_id = store.save_change(sample_change_record)
        
        # 获取变更记录
        retrieved_record = store.get_change(change_id)
        
        # 检查获取的记录
        assert retrieved_record is not None
        assert retrieved_record.change_id == sample_change_record.change_id
        assert retrieved_record.timestamp == sample_change_record.timestamp
        assert retrieved_record.file_path == sample_change_record.file_path
        assert retrieved_record.backup_id == sample_change_record.backup_id
        assert retrieved_record.is_new == sample_change_record.is_new
        assert retrieved_record.is_deletion == sample_change_record.is_deletion
        assert retrieved_record.group_id == sample_change_record.group_id
    
    def test_get_nonexistent_change(self, temp_store_dir):
        """测试获取不存在的变更记录"""
        store = FileChangeStore(store_dir=temp_store_dir)
        
        # 尝试获取不存在的记录
        retrieved_record = store.get_change("nonexistent_id")
        
        # 应该返回None
        assert retrieved_record is None
    
    def test_get_changes_by_group(self, temp_store_dir):
        """测试按组获取变更记录"""
        store = FileChangeStore(store_dir=temp_store_dir)
        group_id = "group123"
        
        # 创建并保存三个同组的变更记录
        for i in range(3):
            record = ChangeRecord.create(
                file_path=f"file{i}.py",
                backup_id=f"backup{i}",
                group_id=group_id
            )
            store.save_change(record)
        
        # 创建一个不同组的变更记录
        other_record = ChangeRecord.create(
            file_path="other.py",
            backup_id="other_backup",
            group_id="other_group"
        )
        store.save_change(other_record)
        
        # 获取同组的变更记录
        group_records = store.get_changes_by_group(group_id)
        
        # 检查记录数量和组ID
        assert len(group_records) == 3
        for record in group_records:
            assert record.group_id == group_id
    
    def test_get_latest_changes(self, temp_store_dir):
        """测试获取最近的变更记录"""
        store = FileChangeStore(store_dir=temp_store_dir)
        
        # 创建并保存五个变更记录，时间戳递增
        for i in range(5):
            record = ChangeRecord.create(
                file_path=f"file{i}.py",
                backup_id=f"backup{i}"
            )
            # 手动设置时间戳，确保顺序
            record.timestamp = 1000 + i
            store.save_change(record)
        
        # 获取最近的3个变更记录
        latest_records = store.get_latest_changes(limit=3)
        
        # 检查记录数量和顺序
        assert len(latest_records) == 3
        assert latest_records[0].timestamp > latest_records[1].timestamp
        assert latest_records[1].timestamp > latest_records[2].timestamp
    
    def test_get_changes_by_file(self, temp_store_dir):
        """测试按文件获取变更记录"""
        store = FileChangeStore(store_dir=temp_store_dir)
        file_path = "test.py"
        
        # 创建并保存同一文件的三个变更记录
        for i in range(3):
            record = ChangeRecord.create(
                file_path=file_path,
                backup_id=f"backup{i}"
            )
            store.save_change(record)
        
        # 创建一个不同文件的变更记录
        other_record = ChangeRecord.create(
            file_path="other.py",
            backup_id="other_backup"
        )
        store.save_change(other_record)
        
        # 获取同一文件的变更记录
        file_records = store.get_changes_by_file(file_path)
        
        # 检查记录数量和文件路径
        assert len(file_records) == 3
        for record in file_records:
            assert record.file_path == file_path
    
    def test_delete_change(self, temp_store_dir, sample_change_record):
        """测试删除变更记录"""
        store = FileChangeStore(store_dir=temp_store_dir)
        
        # 保存变更记录
        change_id = store.save_change(sample_change_record)
        
        # 确认记录存在
        assert store.get_change(change_id) is not None
        
        # 删除记录
        success = store.delete_change(change_id)
        
        # 检查删除结果
        assert success is True
        assert store.get_change(change_id) is None
        
        # 检查文件系统中的JSON文件是否也被删除
        json_file = os.path.join(temp_store_dir, f"{change_id}.json")
        assert not os.path.exists(json_file)
    
    def test_delete_nonexistent_change(self, temp_store_dir):
        """测试删除不存在的变更记录"""
        store = FileChangeStore(store_dir=temp_store_dir)
        
        # 尝试删除不存在的记录
        success = store.delete_change("nonexistent_id")
        
        # 应该返回False
        assert success is False
    
    def test_get_change_groups(self, temp_store_dir):
        """测试获取变更组列表"""
        store = FileChangeStore(store_dir=temp_store_dir)
        
        # 创建两个不同组的变更记录
        group1_id = "group1"
        group2_id = "group2"
        
        # 为第一个组创建两个记录
        for i in range(2):
            record = ChangeRecord.create(
                file_path=f"file{i}.py",
                backup_id=f"backup{i}",
                group_id=group1_id
            )
            store.save_change(record)
        
        # 为第二个组创建一个记录
        record = ChangeRecord.create(
            file_path="otherfile.py",
            backup_id="other_backup",
            group_id=group2_id
        )
        store.save_change(record)
        
        # 获取变更组列表
        groups = store.get_change_groups()
        
        # 检查组数量
        assert len(groups) == 2
        
        # 检查组信息
        groups_dict = {g[0]: (g[1], g[2]) for g in groups}
        assert group1_id in groups_dict
        assert group2_id in groups_dict
        assert groups_dict[group1_id][1] == 2  # 第一个组有2个记录
        assert groups_dict[group2_id][1] == 1  # 第二个组有1个记录
    
    def test_clean_old_history(self, temp_store_dir):
        """测试清理旧历史记录"""
        store = FileChangeStore(store_dir=temp_store_dir, max_history=5)
        
        # 创建10个变更记录
        for i in range(10):
            record = ChangeRecord.create(
                file_path=f"file{i}.py",
                backup_id=f"backup{i}"
            )
            # 手动设置时间戳，确保顺序
            record.timestamp = 1000 + i
            store.save_change(record)
        
        # 获取所有变更记录
        conn = sqlite3.connect(os.path.join(temp_store_dir, "changes.db"))
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM changes")
        count = cursor.fetchone()[0]
        conn.close()
        
        # 检查记录数量，应该只保留max_history个
        assert count == 5  # max_history
    
    def test_thread_safety(self, temp_store_dir, sample_change_record):
        """测试线程安全性"""
        store = FileChangeStore(store_dir=temp_store_dir)
        
        # 保存变更记录
        change_id = store.save_change(sample_change_record)
        
        # 模拟两个线程同时访问
        with patch('threading.RLock') as mock_lock:
            # 设置锁为MagicMock对象
            mock_lock_instance = MagicMock()
            mock_lock.return_value = mock_lock_instance
            
            # 重新创建存储对象（会使用模拟的锁）
            store = FileChangeStore(store_dir=temp_store_dir)
            
            # 执行一些需要锁的操作
            store.get_change(change_id)
            
            # 创建一个新的记录对象（使用不同的ID）
            new_record = ChangeRecord.create(
                file_path=sample_change_record.file_path,
                backup_id=sample_change_record.backup_id,
                is_new=sample_change_record.is_new,
                is_deletion=sample_change_record.is_deletion,
                group_id=sample_change_record.group_id
            )
            store.save_change(new_record)
            
            # 检查锁是否被使用
            assert mock_lock_instance.__enter__.call_count >= 2
            assert mock_lock_instance.__exit__.call_count >= 2 