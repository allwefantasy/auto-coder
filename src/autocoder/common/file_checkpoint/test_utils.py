import pytest
import os
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from autocoder.common.file_checkpoint.utils import (
    apply_shadow_changes, undo_last_changes, get_change_history
)
from autocoder.common.file_checkpoint.models import FileChange
from autocoder.common.file_checkpoint.manager import FileChangeManager

@pytest.fixture
def temp_test_dir():
    """提供一个临时的测试目录"""
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

class TestApplyShadowChanges:
    """apply_shadow_changes函数的单元测试"""
    
    def test_apply_new_file(self, temp_test_dir):
        """测试应用新文件变更"""
        # 准备影子系统变更
        changes = {
            "new_file.txt": {
                "content": "这是新文件内容"
            }
        }
        
        # 应用变更
        result = apply_shadow_changes(temp_test_dir, changes)
        
        # 检查结果
        assert result['success'] is True
        assert len(result['change_ids']) == 1
        assert not result['errors']
        assert "new_file.txt" in result['changed_files']
        
        # 检查文件是否被创建
        new_file_path = os.path.join(temp_test_dir, "new_file.txt")
        assert os.path.exists(new_file_path)
        
        # 检查文件内容
        with open(new_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "这是新文件内容"
    
    def test_apply_modify_file(self, temp_test_dir, sample_file):
        """测试应用修改文件变更"""
        # 获取相对路径
        rel_path = os.path.relpath(sample_file, temp_test_dir)
        
        # 准备影子系统变更
        changes = {
            rel_path: {
                "content": "修改后的内容"
            }
        }
        
        # 应用变更
        result = apply_shadow_changes(temp_test_dir, changes)
        
        # 检查结果
        assert result['success'] is True
        assert len(result['change_ids']) == 1
        assert not result['errors']
        assert rel_path in result['changed_files']
        
        # 检查文件内容
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "修改后的内容"
    
    def test_apply_delete_file(self, temp_test_dir, sample_file):
        """测试应用删除文件变更"""
        # 获取相对路径
        rel_path = os.path.relpath(sample_file, temp_test_dir)
        
        # 准备影子系统变更
        changes = {
            rel_path: {
                "content": "",
                "is_deletion": True
            }
        }
        
        # 应用变更
        result = apply_shadow_changes(temp_test_dir, changes)
        
        # 检查结果
        assert result['success'] is True
        assert len(result['change_ids']) == 1
        assert not result['errors']
        assert rel_path in result['changed_files']
        
        # 检查文件是否被删除
        assert not os.path.exists(sample_file)
    
    def test_apply_multiple_changes(self, temp_test_dir, sample_file):
        """测试应用多个文件变更"""
        # 获取相对路径
        rel_path = os.path.relpath(sample_file, temp_test_dir)
        
        # 准备影子系统变更
        changes = {
            rel_path: {
                "content": "修改后的内容"
            },
            "new_file.txt": {
                "content": "新文件内容"
            }
        }
        
        # 应用变更
        result = apply_shadow_changes(temp_test_dir, changes)
        
        # 检查结果
        assert result['success'] is True
        assert len(result['change_ids']) == 2
        assert not result['errors']
        assert rel_path in result['changed_files']
        assert "new_file.txt" in result['changed_files']
        
        # 检查文件内容
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "修改后的内容"
        
        new_file_path = os.path.join(temp_test_dir, "new_file.txt")
        assert os.path.exists(new_file_path)
        with open(new_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "新文件内容"


class TestUndoLastChanges:
    """undo_last_changes函数的单元测试"""
    
    def test_undo_single_change(self, temp_test_dir, sample_file):
        """测试撤销单个变更"""
        # 获取相对路径
        rel_path = os.path.relpath(sample_file, temp_test_dir)
        
        # 先应用变更
        changes = {
            rel_path: {
                "content": "修改后的内容"
            }
        }
        apply_result = apply_shadow_changes(temp_test_dir, changes)
        assert apply_result['success'] is True
        
        # 检查文件已被修改
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "修改后的内容"
        
        # 撤销变更
        undo_result = undo_last_changes(temp_test_dir)
        
        # 检查撤销结果
        assert undo_result['success'] is True
        assert len(undo_result['restored_files']) == 1
        assert rel_path in undo_result['restored_files']
        
        # 检查文件内容是否被恢复
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "这是一个测试文件的内容"
    
    def test_undo_multiple_steps(self, temp_test_dir, sample_file):
        """测试撤销多个步骤"""
        # 获取相对路径
        rel_path = os.path.relpath(sample_file, temp_test_dir)
        
        # 应用第一个变更
        changes1 = {
            rel_path: {
                "content": "第一次修改"
            }
        }
        apply_result1 = apply_shadow_changes(temp_test_dir, changes1)
        assert apply_result1['success'] is True
        
        # 应用第二个变更
        changes2 = {
            rel_path: {
                "content": "第二次修改"
            }
        }
        apply_result2 = apply_shadow_changes(temp_test_dir, changes2)
        assert apply_result2['success'] is True
        
        # 检查文件内容
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "第二次修改"
        
        # 撤销两个步骤
        undo_result = undo_last_changes(temp_test_dir, steps=2)
        
        # 检查撤销结果
        assert undo_result['success'] is True
        assert len(undo_result['restored_files']) == 2
        
        # 检查文件内容是否被恢复到原始状态
        with open(sample_file, 'r', encoding='utf-8') as f:
            content = f.read()
        assert content == "这是一个测试文件的内容"
    
    def test_undo_with_error(self, temp_test_dir):
        """测试撤销出错的情况"""
        # 模拟FileChangeManager的undo_last_change方法返回错误
        with patch.object(FileChangeManager, 'undo_last_change') as mock_undo:
            from autocoder.common.file_checkpoint.models import UndoResult
            error_result = UndoResult(success=False)
            error_result.add_error("test.txt", "文件不存在")
            mock_undo.return_value = error_result
            
            # 尝试撤销变更
            undo_result = undo_last_changes(temp_test_dir)
            
            # 检查撤销结果
            assert undo_result['success'] is False
            assert "test.txt" in undo_result['errors']
            assert undo_result['errors']["test.txt"] == "文件不存在"


class TestGetChangeHistory:
    """get_change_history函数的单元测试"""
    
    def test_get_history(self, temp_test_dir, sample_file):
        """测试获取变更历史"""
        # 获取相对路径
        rel_path = os.path.relpath(sample_file, temp_test_dir)
        
        # 应用两个变更
        changes1 = {
            rel_path: {
                "content": "第一次修改"
            }
        }
        changes2 = {
            "new_file.txt": {
                "content": "新文件内容"
            }
        }
        
        apply_shadow_changes(temp_test_dir, changes1)
        apply_shadow_changes(temp_test_dir, changes2)
        
        # 获取变更历史
        history = get_change_history(temp_test_dir)
        
        # 检查历史记录
        assert len(history) >= 2
        
        # 检查第一条记录（最新的，是new_file.txt）
        assert history[0]['file_path'] == "new_file.txt"
        assert history[0]['is_new'] is True
        
        # 检查第二条记录（较早的，是修改的sample_file）
        assert history[1]['file_path'] == rel_path
        assert history[1]['is_new'] is False
    
    def test_get_history_with_limit(self, temp_test_dir):
        """测试限制历史记录数量"""
        # 使用模拟的FileChangeManager
        with patch.object(FileChangeManager, 'get_change_history') as mock_get_history:
            # 创建模拟的返回值
            from autocoder.common.file_checkpoint.models import ChangeRecord
            mock_records = [
                ChangeRecord.create(file_path=f"file{i}.txt", backup_id=f"backup{i}")
                for i in range(5)
            ]
            mock_get_history.return_value = mock_records
            
            # 请求限制为3条记录
            history = get_change_history(temp_test_dir, limit=3)
            
            # 检查参数调用
            mock_get_history.assert_called_once_with(3)
            
            # 检查结果
            assert len(history) == 5  # 模拟返回了5条记录 