import pytest
import json
from datetime import datetime
from pathlib import Path

from autocoder.common.file_checkpoint.models import (
    FileChange, ChangeRecord, DiffResult, ApplyResult, UndoResult
)

class TestFileChange:
    """FileChange类的单元测试"""
    
    def test_init(self):
        """测试FileChange初始化"""
        fc = FileChange(
            file_path="test.py",
            content="print('hello')",
            is_new=True,
            is_deletion=False
        )
        
        assert fc.file_path == "test.py"
        assert fc.content == "print('hello')"
        assert fc.is_new is True
        assert fc.is_deletion is False
    
    def test_from_dict(self):
        """测试从字典创建FileChange对象"""
        data = {
            'file_path': 'test.py',
            'content': "print('hello')",
            'is_new': True,
            'is_deletion': False
        }
        
        fc = FileChange.from_dict(data)
        
        assert fc.file_path == "test.py"
        assert fc.content == "print('hello')"
        assert fc.is_new is True
        assert fc.is_deletion is False
    
    def test_to_dict(self):
        """测试将FileChange对象转换为字典"""
        fc = FileChange(
            file_path="test.py",
            content="print('hello')",
            is_new=True,
            is_deletion=False
        )
        
        data = fc.to_dict()
        
        assert data['file_path'] == "test.py"
        assert data['content'] == "print('hello')"
        assert data['is_new'] is True
        assert data['is_deletion'] is False
    
    def test_default_values(self):
        """测试默认值"""
        fc = FileChange(
            file_path="test.py",
            content="print('hello')"
        )
        
        assert fc.is_new is False
        assert fc.is_deletion is False
    
    def test_from_dict_missing_optionals(self):
        """测试从缺少可选字段的字典创建"""
        data = {
            'file_path': 'test.py',
            'content': "print('hello')"
        }
        
        fc = FileChange.from_dict(data)
        
        assert fc.file_path == "test.py"
        assert fc.content == "print('hello')"
        assert fc.is_new is False
        assert fc.is_deletion is False


class TestChangeRecord:
    """ChangeRecord类的单元测试"""
    
    def test_init(self):
        """测试ChangeRecord初始化"""
        cr = ChangeRecord(
            change_id="123",
            timestamp=1234567890.0,
            file_path="test.py",
            backup_id="456",
            is_new=True,
            is_deletion=False,
            group_id="789"
        )
        
        assert cr.change_id == "123"
        assert cr.timestamp == 1234567890.0
        assert cr.file_path == "test.py"
        assert cr.backup_id == "456"
        assert cr.is_new is True
        assert cr.is_deletion is False
        assert cr.group_id == "789"
    
    def test_create(self):
        """测试创建一个新的变更记录"""
        before_time = datetime.now().timestamp()
        
        cr = ChangeRecord.create(
            file_path="test.py",
            backup_id="456",
            is_new=True,
            is_deletion=False,
            group_id="789"
        )
        
        after_time = datetime.now().timestamp()
        
        assert cr.file_path == "test.py"
        assert cr.backup_id == "456"
        assert cr.is_new is True
        assert cr.is_deletion is False
        assert cr.group_id == "789"
        
        # UUID和时间戳应该是自动生成的
        assert cr.change_id is not None
        assert len(cr.change_id) > 0
        assert before_time <= cr.timestamp <= after_time
    
    def test_from_dict(self):
        """测试从字典创建ChangeRecord对象"""
        data = {
            'change_id': '123',
            'timestamp': 1234567890.0,
            'file_path': 'test.py',
            'backup_id': '456',
            'is_new': True,
            'is_deletion': False,
            'group_id': '789'
        }
        
        cr = ChangeRecord.from_dict(data)
        
        assert cr.change_id == "123"
        assert cr.timestamp == 1234567890.0
        assert cr.file_path == "test.py"
        assert cr.backup_id == "456"
        assert cr.is_new is True
        assert cr.is_deletion is False
        assert cr.group_id == "789"
    
    def test_to_dict(self):
        """测试将ChangeRecord对象转换为字典"""
        cr = ChangeRecord(
            change_id="123",
            timestamp=1234567890.0,
            file_path="test.py",
            backup_id="456",
            is_new=True,
            is_deletion=False,
            group_id="789"
        )
        
        data = cr.to_dict()
        
        assert data['change_id'] == "123"
        assert data['timestamp'] == 1234567890.0
        assert data['file_path'] == "test.py"
        assert data['backup_id'] == "456"
        assert data['is_new'] is True
        assert data['is_deletion'] is False
        assert data['group_id'] == "789"
    
    def test_default_values(self):
        """测试默认值"""
        cr = ChangeRecord(
            change_id="123",
            timestamp=1234567890.0,
            file_path="test.py",
            backup_id="456"
        )
        
        assert cr.is_new is False
        assert cr.is_deletion is False
        assert cr.group_id is None
    
    def test_from_dict_missing_optionals(self):
        """测试从缺少可选字段的字典创建"""
        data = {
            'change_id': '123',
            'timestamp': 1234567890.0,
            'file_path': 'test.py',
            'backup_id': '456'
        }
        
        cr = ChangeRecord.from_dict(data)
        
        assert cr.change_id == "123"
        assert cr.timestamp == 1234567890.0
        assert cr.file_path == "test.py"
        assert cr.backup_id == "456"
        assert cr.is_new is False
        assert cr.is_deletion is False
        assert cr.group_id is None


class TestDiffResult:
    """DiffResult类的单元测试"""
    
    def test_init(self):
        """测试DiffResult初始化"""
        dr = DiffResult(
            file_path="test.py",
            old_content="print('hello')",
            new_content="print('world')",
            is_new=False,
            is_deletion=False
        )
        
        assert dr.file_path == "test.py"
        assert dr.old_content == "print('hello')"
        assert dr.new_content == "print('world')"
        assert dr.is_new is False
        assert dr.is_deletion is False
    
    def test_default_values(self):
        """测试默认值"""
        dr = DiffResult(
            file_path="test.py",
            old_content="print('hello')",
            new_content="print('world')"
        )
        
        assert dr.is_new is False
        assert dr.is_deletion is False
    
    def test_get_diff_summary_modify(self):
        """测试获取修改文件的差异摘要"""
        dr = DiffResult(
            file_path="test.py",
            old_content="line1\nline2\nline3",
            new_content="line1\nline2\nline3\nline4"
        )
        
        summary = dr.get_diff_summary()
        
        assert "修改文件" in summary
        assert "test.py" in summary
        assert "原始行数: 3" in summary
        assert "新行数: 4" in summary
    
    def test_get_diff_summary_new(self):
        """测试获取新文件的差异摘要"""
        dr = DiffResult(
            file_path="test.py",
            old_content=None,
            new_content="print('hello')",
            is_new=True
        )
        
        summary = dr.get_diff_summary()
        
        assert "新文件" in summary
        assert "test.py" in summary
    
    def test_get_diff_summary_delete(self):
        """测试获取删除文件的差异摘要"""
        dr = DiffResult(
            file_path="test.py",
            old_content="print('hello')",
            new_content="",
            is_deletion=True
        )
        
        summary = dr.get_diff_summary()
        
        assert "删除文件" in summary
        assert "test.py" in summary


class TestApplyResult:
    """ApplyResult类的单元测试"""
    
    def test_init(self):
        """测试ApplyResult初始化"""
        ar = ApplyResult(success=True)
        
        assert ar.success is True
        assert ar.change_ids == []
        assert ar.errors == {}
        assert ar.has_errors is False
    
    def test_add_error(self):
        """测试添加错误信息"""
        ar = ApplyResult(success=True)
        
        assert ar.success is True
        assert ar.has_errors is False
        
        ar.add_error("test.py", "文件不存在")
        
        assert ar.success is False
        assert ar.has_errors is True
        assert "test.py" in ar.errors
        assert ar.errors["test.py"] == "文件不存在"
    
    def test_add_change_id(self):
        """测试添加成功应用的变更ID"""
        ar = ApplyResult(success=True)
        
        assert len(ar.change_ids) == 0
        
        ar.add_change_id("123")
        ar.add_change_id("456")
        
        assert len(ar.change_ids) == 2
        assert "123" in ar.change_ids
        assert "456" in ar.change_ids


class TestUndoResult:
    """UndoResult类的单元测试"""
    
    def test_init(self):
        """测试UndoResult初始化"""
        ur = UndoResult(success=True)
        
        assert ur.success is True
        assert ur.restored_files == []
        assert ur.errors == {}
        assert ur.has_errors is False
    
    def test_add_error(self):
        """测试添加错误信息"""
        ur = UndoResult(success=True)
        
        assert ur.success is True
        assert ur.has_errors is False
        
        ur.add_error("test.py", "文件不存在")
        
        assert ur.success is False
        assert ur.has_errors is True
        assert "test.py" in ur.errors
        assert ur.errors["test.py"] == "文件不存在"
    
    def test_add_restored_file(self):
        """测试添加成功恢复的文件"""
        ur = UndoResult(success=True)
        
        assert len(ur.restored_files) == 0
        
        ur.add_restored_file("test.py")
        ur.add_restored_file("main.py")
        
        assert len(ur.restored_files) == 2
        assert "test.py" in ur.restored_files
        assert "main.py" in ur.restored_files 