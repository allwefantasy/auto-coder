import pytest
import os
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock, call

from autocoder.common.file_checkpoint.manager import FileChangeManager
from autocoder.common.file_checkpoint.models import (
    FileChange, ChangeRecord, ApplyResult, UndoResult, DiffResult
)
from autocoder.common.file_checkpoint.backup import FileBackupManager
from autocoder.common.file_checkpoint.store import FileChangeStore

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
def temp_store_dir():
    """提供一个临时的存储目录"""
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

@pytest.fixture
def nested_sample_file(temp_test_dir):
    """创建一个位于嵌套目录中的样例文件"""
    nested_dir = os.path.join(temp_test_dir, "nested", "dir")
    os.makedirs(nested_dir, exist_ok=True)
    
    file_path = os.path.join(nested_dir, "nested_sample.txt")
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write("这是一个嵌套目录中的测试文件")
    
    return file_path

@pytest.fixture
def sample_change():
    """创建一个用于测试的文件变更"""
    return FileChange(
        file_path="test.py",
        content="print('hello world')",
        is_new=True,
        is_deletion=False
    )

class TestFileChangeManager:
    """FileChangeManager类的单元测试"""
    
    def test_init(self, temp_test_dir, temp_backup_dir, temp_store_dir):
        """测试初始化"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        assert manager.project_dir == os.path.abspath(temp_test_dir)
        assert isinstance(manager.backup_manager, FileBackupManager)
        assert isinstance(manager.change_store, FileChangeStore)
    
    def test_apply_changes_new_file(self, temp_test_dir, temp_backup_dir, temp_store_dir):
        """测试应用新文件变更"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 准备变更
        test_file_path = "test_new.py"
        change = FileChange(
            file_path=test_file_path,
            content="print('hello world')",
            is_new=True
        )
        changes = {test_file_path: change}
        
        # 应用变更
        result = manager.apply_changes(changes)
        
        # 检查结果
        assert result.success is True
        assert len(result.change_ids) == 1
        assert not result.has_errors
        
        # 检查文件是否被创建
        expected_file_path = os.path.join(temp_test_dir, test_file_path)
        assert os.path.exists(expected_file_path)
        
        # 检查文件内容
        with open(expected_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "print('hello world')"
    
    def test_apply_changes_modify_file(self, temp_test_dir, temp_backup_dir, temp_store_dir, sample_file):
        """测试应用修改文件变更"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 准备变更
        rel_path = os.path.basename(sample_file)
        change = FileChange(
            file_path=rel_path,
            content="修改后的内容",
            is_new=False
        )
        changes = {rel_path: change}
        
        # 应用变更
        result = manager.apply_changes(changes)
        
        # 检查结果
        assert result.success is True
        assert len(result.change_ids) == 1
        assert not result.has_errors
        
        # 检查文件内容
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "修改后的内容"
    
    def test_apply_changes_delete_file(self, temp_test_dir, temp_backup_dir, temp_store_dir, sample_file):
        """测试应用删除文件变更"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 准备变更
        rel_path = os.path.basename(sample_file)
        change = FileChange(
            file_path=rel_path,
            content="",
            is_deletion=True
        )
        changes = {rel_path: change}
        
        # 应用变更
        result = manager.apply_changes(changes)
        
        # 检查结果
        assert result.success is True
        assert len(result.change_ids) == 1
        assert not result.has_errors
        
        # 检查文件是否被删除
        assert not os.path.exists(sample_file)
    
    def test_apply_changes_create_nested_dirs(self, temp_test_dir, temp_backup_dir, temp_store_dir):
        """测试应用变更时创建嵌套目录"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 准备变更
        nested_path = os.path.join("nested", "path", "to", "file.txt")
        change = FileChange(
            file_path=nested_path,
            content="嵌套目录中的文件内容",
            is_new=True
        )
        changes = {nested_path: change}
        
        # 应用变更
        result = manager.apply_changes(changes)
        
        # 检查结果
        assert result.success is True
        assert len(result.change_ids) == 1
        assert not result.has_errors
        
        # 检查文件是否被创建
        expected_file_path = os.path.join(temp_test_dir, nested_path)
        assert os.path.exists(expected_file_path)
        
        # 检查目录结构是否被创建
        nested_dir = os.path.dirname(expected_file_path)
        assert os.path.isdir(nested_dir)
    
    def test_apply_changes_with_error(self, temp_test_dir, temp_backup_dir, temp_store_dir):
        """测试应用变更出错的情况"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 创建一个目标是目录的变更，这应该会导致错误
        os.makedirs(os.path.join(temp_test_dir, "existing_dir"))
        change = FileChange(
            file_path="existing_dir",
            content="这不会成功，因为目标已经是一个目录",
            is_new=False
        )
        changes = {"existing_dir": change}
        
        # 应用变更
        result = manager.apply_changes(changes)
        
        # 检查结果
        assert result.success is False
        assert result.has_errors
        assert "existing_dir" in result.errors
    
    def test_apply_changes_with_group_id(self, temp_test_dir, temp_backup_dir, temp_store_dir):
        """测试使用组ID应用变更"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 准备变更
        change1 = FileChange(
            file_path="file1.txt",
            content="文件1内容"
        )
        change2 = FileChange(
            file_path="file2.txt",
            content="文件2内容"
        )
        changes = {
            "file1.txt": change1,
            "file2.txt": change2
        }
        
        # 应用变更，使用自定义组ID
        group_id = "test_group_123"
        result = manager.apply_changes(changes, change_group_id=group_id)
        
        # 检查结果
        assert result.success is True
        assert len(result.change_ids) == 2
        
        # 检查变更记录是否使用了指定的组ID
        for change_id in result.change_ids:
            record = manager.change_store.get_change(change_id)
            assert record.group_id == group_id
    
    def test_preview_changes(self, temp_test_dir, temp_backup_dir, temp_store_dir, sample_file):
        """测试预览变更"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 准备变更
        rel_path = os.path.basename(sample_file)
        change1 = FileChange(
            file_path=rel_path,
            content="修改后的内容"
        )
        change2 = FileChange(
            file_path="new_file.txt",
            content="新文件内容",
            is_new=True
        )
        change3 = FileChange(
            file_path="to_be_deleted.txt",
            content="",
            is_deletion=True
        )
        
        # 创建to_be_deleted.txt文件
        delete_file_path = os.path.join(temp_test_dir, "to_be_deleted.txt")
        with open(delete_file_path, 'w', encoding='utf-8') as f:
            f.write("将被删除的文件")
        
        changes = {
            rel_path: change1,
            "new_file.txt": change2,
            "to_be_deleted.txt": change3
        }
        
        # 预览变更
        diff_results = manager.preview_changes(changes)
        
        # 检查结果
        assert len(diff_results) == 3
        
        # 检查修改文件的差异
        assert rel_path in diff_results
        modify_diff = diff_results[rel_path]
        assert modify_diff.file_path == rel_path
        assert modify_diff.old_content == "这是一个测试文件的内容"
        assert modify_diff.new_content == "修改后的内容"
        assert not modify_diff.is_new
        assert not modify_diff.is_deletion
        
        # 检查新文件的差异
        assert "new_file.txt" in diff_results
        new_diff = diff_results["new_file.txt"]
        assert new_diff.file_path == "new_file.txt"
        assert new_diff.old_content is None
        assert new_diff.new_content == "新文件内容"
        assert new_diff.is_new
        assert not new_diff.is_deletion
        
        # 检查删除文件的差异
        assert "to_be_deleted.txt" in diff_results
        delete_diff = diff_results["to_be_deleted.txt"]
        assert delete_diff.file_path == "to_be_deleted.txt"
        assert delete_diff.old_content in ["将被删除的文件", None]
        assert delete_diff.new_content == ""
        assert not delete_diff.is_new
        assert delete_diff.is_deletion
    
    def test_get_diff_text(self, temp_test_dir, temp_backup_dir, temp_store_dir):
        """测试获取差异文本"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        old_content = "line1\nline2\nline3\n"
        new_content = "line1\nline2 modified\nline3\nline4\n"
        
        diff_text = manager.get_diff_text(old_content, new_content)
        
        # 检查差异文本
        assert "line2" in diff_text
        assert "line2 modified" in diff_text
        assert "line4" in diff_text
    
    def test_undo_last_change(self, temp_test_dir, temp_backup_dir, temp_store_dir, sample_file):
        """测试撤销最近的变更"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 应用变更
        rel_path = os.path.basename(sample_file)
        change = FileChange(
            file_path=rel_path,
            content="修改后的内容"
        )
        changes = {rel_path: change}
        
        apply_result = manager.apply_changes(changes)
        assert apply_result.success is True
        
        # 检查文件已被修改
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "修改后的内容"
        
        # 撤销最近的变更
        undo_result = manager.undo_last_change()
        
        # 检查撤销结果
        assert undo_result.success is True
        assert len(undo_result.restored_files) == 1
        assert rel_path in undo_result.restored_files
        
        # 检查文件内容是否被恢复
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "这是一个测试文件的内容"
    
    def test_undo_change_group(self, temp_test_dir, temp_backup_dir, temp_store_dir):
        """测试撤销变更组"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 准备变更
        change1 = FileChange(
            file_path="file1.txt",
            content="文件1内容"
        )
        change2 = FileChange(
            file_path="file2.txt",
            content="文件2内容"
        )
        changes = {
            "file1.txt": change1,
            "file2.txt": change2
        }
        
        # 应用变更，使用自定义组ID
        group_id = "test_group_456"
        apply_result = manager.apply_changes(changes, change_group_id=group_id)
        assert apply_result.success is True
        
        # 检查文件已被创建
        file1_path = os.path.join(temp_test_dir, "file1.txt")
        file2_path = os.path.join(temp_test_dir, "file2.txt")
        assert os.path.exists(file1_path)
        assert os.path.exists(file2_path)
        
        # 撤销变更组
        undo_result = manager.undo_change_group(group_id)
        
        # 检查撤销结果
        assert undo_result.success is True
        assert len(undo_result.restored_files) == 2
        assert "file1.txt" in undo_result.restored_files
        assert "file2.txt" in undo_result.restored_files
        
        # 检查文件是否被删除（因为是新文件）
        assert not os.path.exists(file1_path)
        assert not os.path.exists(file2_path)
    
    def test_undo_to_version(self, temp_test_dir, temp_backup_dir, temp_store_dir, sample_file):
        """测试撤销到指定版本"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 应用多个变更
        rel_path = os.path.basename(sample_file)
        changes1 = {rel_path: FileChange(file_path=rel_path, content="第一次修改")}
        changes2 = {rel_path: FileChange(file_path=rel_path, content="第二次修改")}
        changes3 = {rel_path: FileChange(file_path=rel_path, content="第三次修改")}
        
        result1 = manager.apply_changes(changes1)
        result2 = manager.apply_changes(changes2)
        result3 = manager.apply_changes(changes3)
        
        assert result1.success and result2.success and result3.success
        
        # 获取变更历史
        history = manager.get_change_history()
        assert len(history) >= 3
        
        # 撤销到第一次变更后的版本
        version_id = result1.change_ids[0]
        undo_result = manager.undo_to_version(version_id)
        
        # 检查撤销结果
        assert undo_result.success is True
        assert len(undo_result.restored_files) >= 1
        assert rel_path in undo_result.restored_files
        
        # 检查文件内容是否被恢复到第一次修改后的状态
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "第一次修改"
    
    def test_get_change_history(self, temp_test_dir, temp_backup_dir, temp_store_dir):
        """测试获取变更历史"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 模拟存储器的get_latest_changes方法
        mock_records = [
            ChangeRecord.create(file_path="file1.txt", backup_id="backup1"),
            ChangeRecord.create(file_path="file2.txt", backup_id="backup2")
        ]
        
        with patch.object(manager.change_store, 'get_latest_changes', return_value=mock_records) as mock_method:
            history = manager.get_change_history(limit=5)
            
            # 检查是否调用了正确的方法
            mock_method.assert_called_once_with(5)
            
            # 检查结果
            assert len(history) == 2
            assert history[0].file_path == "file1.txt"
            assert history[1].file_path == "file2.txt"
    
    def test_get_file_history(self, temp_test_dir, temp_backup_dir, temp_store_dir):
        """测试获取文件变更历史"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 模拟存储器的get_changes_by_file方法
        mock_records = [
            ChangeRecord.create(file_path="test.py", backup_id="backup1"),
            ChangeRecord.create(file_path="test.py", backup_id="backup2")
        ]
        
        with patch.object(manager.change_store, 'get_changes_by_file', return_value=mock_records) as mock_method:
            history = manager.get_file_history("test.py", limit=5)
            
            # 检查是否调用了正确的方法
            mock_method.assert_called_once_with("test.py", 5)
            
            # 检查结果
            assert len(history) == 2
            assert history[0].file_path == "test.py"
            assert history[1].file_path == "test.py"
    
    def test_get_change_groups(self, temp_test_dir, temp_backup_dir, temp_store_dir):
        """测试获取变更组"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 模拟存储器的get_change_groups方法
        mock_groups = [
            ("group1", 1000.0, 2),
            ("group2", 2000.0, 3)
        ]
        
        with patch.object(manager.change_store, 'get_change_groups', return_value=mock_groups) as mock_method:
            groups = manager.get_change_groups(limit=5)
            
            # 检查是否调用了正确的方法
            mock_method.assert_called_once_with(5)
            
            # 检查结果
            assert len(groups) == 2
            assert groups[0][0] == "group1"
            assert groups[1][0] == "group2"
    
    def test_get_absolute_path(self, temp_test_dir, temp_backup_dir, temp_store_dir):
        """测试获取绝对路径"""
        manager = FileChangeManager(
            project_dir=temp_test_dir,
            backup_dir=temp_backup_dir,
            store_dir=temp_store_dir
        )
        
        # 测试相对路径
        rel_path = "test/path.txt"
        abs_path = manager._get_absolute_path(rel_path)
        
        expected_path = os.path.join(temp_test_dir, rel_path)
        assert abs_path == expected_path
        
        # 测试绝对路径
        abs_path_input = os.path.abspath("/some/abs/path.txt")
        abs_path_output = manager._get_absolute_path(abs_path_input)
        
        # 应该保持原样
        assert abs_path_output == abs_path_input 