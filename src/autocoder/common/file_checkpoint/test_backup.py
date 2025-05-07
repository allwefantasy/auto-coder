import pytest
import os
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from pathlib import Path

from autocoder.common.file_checkpoint.backup import FileBackupManager

@pytest.fixture
def temp_test_dir():
    """提供一个临时的测试目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def temp_backup_dir():
    """提供一个临时的备份目录"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)

@pytest.fixture
def sample_file(temp_test_dir):
    """创建一个用于测试的样例文件"""
    file_path = os.path.join(temp_test_dir, "sample.txt")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("这是一个测试文件的内容")
    return file_path

class TestFileBackupManager:
    """FileBackupManager类的单元测试"""
    
    def test_init_with_custom_dir(self, temp_backup_dir):
        """测试使用自定义目录初始化"""
        manager = FileBackupManager(backup_dir=temp_backup_dir)
        
        assert manager.backup_dir == temp_backup_dir
        assert os.path.exists(temp_backup_dir)
    
    def test_init_with_default_dir(self, monkeypatch):
        """测试使用默认目录初始化"""
        # 创建一个临时主目录
        temp_home = tempfile.mkdtemp()
        try:
            # 模拟用户主目录
            monkeypatch.setattr(os.path, 'expanduser', lambda path: temp_home)
            
            manager = FileBackupManager()
            
            expected_dir = os.path.join(temp_home, ".autocoder", "backups")
            assert manager.backup_dir == expected_dir
            assert os.path.exists(expected_dir)
        finally:
            # 清理临时目录
            if os.path.exists(temp_home):
                shutil.rmtree(temp_home)
    
    def test_backup_file(self, temp_backup_dir, sample_file):
        """测试备份文件功能"""
        manager = FileBackupManager(backup_dir=temp_backup_dir)
        
        # 备份文件
        backup_id = manager.backup_file(sample_file)
        
        # 检查备份ID
        assert backup_id is not None
        assert len(backup_id) > 0
        
        # 检查备份文件是否存在
        backup_file_path = os.path.join(temp_backup_dir, backup_id)
        assert os.path.exists(backup_file_path)
        
        # 检查备份文件内容
        with open(backup_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "这是一个测试文件的内容"
        
        # 检查元数据
        assert backup_id in manager.metadata
        assert manager.metadata[backup_id]["original_path"] == sample_file
        assert "timestamp" in manager.metadata[backup_id]
        assert "size" in manager.metadata[backup_id]
    
    def test_backup_nonexistent_file(self, temp_backup_dir):
        """测试备份不存在的文件"""
        manager = FileBackupManager(backup_dir=temp_backup_dir)
        
        # 尝试备份不存在的文件
        backup_id = manager.backup_file("nonexistent_file.txt")
        
        # 应该返回None
        assert backup_id is None
    
    def test_restore_file(self, temp_backup_dir, temp_test_dir, sample_file):
        """测试恢复文件功能"""
        manager = FileBackupManager(backup_dir=temp_backup_dir)
        
        # 备份文件
        backup_id = manager.backup_file(sample_file)
        
        # 修改原始文件
        with open(sample_file, 'w', encoding='utf-8') as f:
            f.write("已修改的内容")
        
        # 恢复到新位置
        restore_path = os.path.join(temp_test_dir, "restored.txt")
        success = manager.restore_file(restore_path, backup_id)
        
        # 检查恢复结果
        assert success is True
        assert os.path.exists(restore_path)
        
        # 检查恢复文件内容
        with open(restore_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "这是一个测试文件的内容"
    
    def test_restore_with_invalid_backup_id(self, temp_backup_dir, temp_test_dir):
        """测试使用无效的备份ID恢复文件"""
        manager = FileBackupManager(backup_dir=temp_backup_dir)
        
        # 尝试恢复不存在的备份
        restore_path = os.path.join(temp_test_dir, "restored.txt")
        success = manager.restore_file(restore_path, "invalid_backup_id")
        
        # 应该失败
        assert success is False
        assert not os.path.exists(restore_path)
    
    def test_get_backup_content(self, temp_backup_dir, sample_file):
        """测试获取备份文件内容"""
        manager = FileBackupManager(backup_dir=temp_backup_dir)
        
        # 备份文件
        backup_id = manager.backup_file(sample_file)
        
        # 获取备份内容
        content = manager.get_backup_content(backup_id)
        
        # 检查内容
        assert content == "这是一个测试文件的内容"
    
    def test_get_backup_content_with_invalid_id(self, temp_backup_dir):
        """测试使用无效的备份ID获取内容"""
        manager = FileBackupManager(backup_dir=temp_backup_dir)
        
        # 尝试获取不存在的备份内容
        content = manager.get_backup_content("invalid_backup_id")
        
        # 应该返回None
        assert content is None
    
    def test_delete_backup(self, temp_backup_dir, sample_file):
        """测试删除备份"""
        manager = FileBackupManager(backup_dir=temp_backup_dir)
        
        # 备份文件
        backup_id = manager.backup_file(sample_file)
        backup_file_path = os.path.join(temp_backup_dir, backup_id)
        
        # 检查备份文件是否存在
        assert os.path.exists(backup_file_path)
        assert backup_id in manager.metadata
        
        # 删除备份
        success = manager.delete_backup(backup_id)
        
        # 检查删除结果
        assert success is True
        assert not os.path.exists(backup_file_path)
        assert backup_id not in manager.metadata
    
    def test_delete_nonexistent_backup(self, temp_backup_dir):
        """测试删除不存在的备份"""
        manager = FileBackupManager(backup_dir=temp_backup_dir)
        
        # 尝试删除不存在的备份
        success = manager.delete_backup("nonexistent_backup_id")
        
        # 应该返回False
        assert success is False
    
    def test_get_backups_for_file(self, temp_backup_dir, sample_file):
        """测试获取指定文件的所有备份"""
        manager = FileBackupManager(backup_dir=temp_backup_dir)
        
        # 创建多个备份
        backup_ids = []
        for i in range(3):
            backup_id = manager.backup_file(sample_file)
            backup_ids.append(backup_id)
        
        # 获取文件的备份列表
        backups = manager.get_backups_for_file(sample_file)
        
        # 检查备份列表
        assert len(backups) == 3
        for backup_id, timestamp in backups:
            assert backup_id in backup_ids
            assert isinstance(timestamp, float)
    
    @pytest.mark.parametrize("max_age_days", [1, 7, 30])
    def test_clean_old_backups(self, temp_backup_dir, sample_file, max_age_days):
        """测试清理旧备份"""
        manager = FileBackupManager(backup_dir=temp_backup_dir)
        
        # 创建一个备份
        backup_id = manager.backup_file(sample_file)
        
        # 修改备份的时间戳为过去的时间
        old_timestamp = (datetime.now() - timedelta(days=max_age_days+1)).timestamp()
        manager.metadata[backup_id]["timestamp"] = old_timestamp
        manager._save_metadata()
        
        # 创建一个新备份
        new_backup_id = manager.backup_file(sample_file)
        
        # 清理旧备份
        cleaned_count = manager.clean_old_backups(max_age_days)
        
        # 检查清理结果
        assert cleaned_count == 1
        assert backup_id not in manager.metadata
        assert not os.path.exists(os.path.join(temp_backup_dir, backup_id))
        assert new_backup_id in manager.metadata
        assert os.path.exists(os.path.join(temp_backup_dir, new_backup_id))
    
    def test_metadata_persistence(self, temp_backup_dir, sample_file):
        """测试元数据持久化"""
        # 创建一个备份
        manager1 = FileBackupManager(backup_dir=temp_backup_dir)
        backup_id = manager1.backup_file(sample_file)
        
        # 创建另一个管理器实例，应该加载已存在的元数据
        manager2 = FileBackupManager(backup_dir=temp_backup_dir)
        
        # 检查元数据是否被正确加载
        assert backup_id in manager2.metadata
        assert manager2.metadata[backup_id]["original_path"] == sample_file 