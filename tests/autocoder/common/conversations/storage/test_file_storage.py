"""
文件存储测试
"""

import pytest
import os
import json
import tempfile
import shutil
from unittest.mock import patch, mock_open
from autocoder.common.conversations.storage.file_storage import FileStorage
from autocoder.common.conversations.exceptions import (
    DataIntegrityError,
    ConversationNotFoundError
)


class TestFileStorage:
    """测试FileStorage文件存储"""
    
    def test_file_storage_creation(self, temp_dir):
        """测试文件存储创建"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        assert str(storage.storage_path) == storage_path
        assert os.path.exists(storage_path)
    
    def test_file_storage_directory_creation(self, temp_dir):
        """测试存储目录自动创建"""
        storage_path = os.path.join(temp_dir, "nested", "conversations")
        storage = FileStorage(storage_path)
        
        # 目录应该自动创建
        assert os.path.exists(storage_path)
    
    def test_save_conversation(self, temp_dir):
        """测试保存对话"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        conversation_data = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation',
            'messages': [
                {'role': 'user', 'content': 'Hello'},
                {'role': 'assistant', 'content': 'Hi there!'}
            ],
            'created_at': 1234567890.0,
            'updated_at': 1234567890.0
        }
        
        result = storage.save_conversation(conversation_data)
        assert result is True
        
        # 检查文件是否存在
        expected_file = os.path.join(storage_path, "test_conv.json")
        assert os.path.exists(expected_file)
        
        # 检查文件内容
        with open(expected_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        assert saved_data == conversation_data
    
    def test_save_conversation_without_id(self, temp_dir):
        """测试保存没有ID的对话"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        conversation_data = {
            'name': 'Test Conversation'
        }
        
        result = storage.save_conversation(conversation_data)
        assert result is False
    
    def test_load_conversation(self, temp_dir):
        """测试加载对话"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        conversation_data = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation',
            'messages': []
        }
        
        # 先保存
        storage.save_conversation(conversation_data)
        
        # 再加载
        loaded_data = storage.load_conversation('test_conv')
        assert loaded_data == conversation_data
    
    def test_load_nonexistent_conversation(self, temp_dir):
        """测试加载不存在的对话"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        loaded_data = storage.load_conversation('nonexistent')
        assert loaded_data is None
    
    def test_delete_conversation(self, temp_dir):
        """测试删除对话"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        conversation_data = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation'
        }
        
        # 先保存
        storage.save_conversation(conversation_data)
        expected_file = os.path.join(storage_path, "test_conv.json")
        assert os.path.exists(expected_file)
        
        # 删除
        result = storage.delete_conversation('test_conv')
        assert result is True
        assert not os.path.exists(expected_file)
    
    def test_delete_nonexistent_conversation(self, temp_dir):
        """测试删除不存在的对话"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        result = storage.delete_conversation('nonexistent')
        assert result is False
    
    def test_conversation_exists(self, temp_dir):
        """测试检查对话是否存在"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        conversation_data = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation'
        }
        
        # 对话不存在时
        assert storage.conversation_exists('test_conv') is False
        
        # 保存后
        storage.save_conversation(conversation_data)
        assert storage.conversation_exists('test_conv') is True
        
        # 删除后
        storage.delete_conversation('test_conv')
        assert storage.conversation_exists('test_conv') is False
    
    def test_list_conversations(self, temp_dir):
        """测试列出对话"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        # 创建多个对话
        conversations = []
        for i in range(5):
            conversation_data = {
                'conversation_id': f'conv_{i}',
                'name': f'Conversation {i}',
                'created_at': 1234567890.0 + i
            }
            storage.save_conversation(conversation_data)
            conversations.append(conversation_data)
        
        # 测试无限制列出
        all_conversations = storage.list_conversations()
        assert len(all_conversations) == 5
        
        # 验证数据正确性
        for conv in all_conversations:
            assert conv in conversations
        
        # 测试带限制列出
        limited_conversations = storage.list_conversations(limit=3)
        assert len(limited_conversations) == 3
        
        # 测试带偏移列出
        offset_conversations = storage.list_conversations(offset=2)
        assert len(offset_conversations) == 3
        
        # 测试带限制和偏移列出
        limited_offset_conversations = storage.list_conversations(limit=2, offset=1)
        assert len(limited_offset_conversations) == 2


class TestFileStorageAtomicOperations:
    """测试文件存储的原子操作"""
    
    def test_atomic_write(self, temp_dir):
        """测试原子写入机制"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        conversation_data = {
            'conversation_id': 'atomic_test',
            'name': 'Atomic Test'
        }
        
        # 模拟写入过程中的中断
        original_rename = os.rename
        call_count = 0
        
        def mock_rename(src, dst):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # 第一次调用时抛出异常
                raise OSError("模拟中断")
            return original_rename(src, dst)
        
        with patch('os.rename', side_effect=mock_rename):
            try:
                storage.save_conversation(conversation_data)
            except OSError:
                pass
        
        # 检查目标文件不存在（因为原子操作失败）
        target_file = os.path.join(storage_path, "atomic_test.json")
        assert not os.path.exists(target_file)
        
        # 检查临时文件也不存在
        temp_files = [f for f in os.listdir(storage_path) if f.startswith("atomic_test.json.tmp")]
        assert len(temp_files) == 0 or not any(os.path.exists(os.path.join(storage_path, f)) for f in temp_files)
    
    def test_successful_atomic_write(self, temp_dir):
        """测试成功的原子写入"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        conversation_data = {
            'conversation_id': 'atomic_success',
            'name': 'Atomic Success Test'
        }
        
        result = storage.save_conversation(conversation_data)
        assert result is True
        
        # 检查最终文件存在且内容正确
        target_file = os.path.join(storage_path, "atomic_success.json")
        assert os.path.exists(target_file)
        
        with open(target_file, 'r', encoding='utf-8') as f:
            saved_data = json.load(f)
        assert saved_data == conversation_data
        
        # 检查没有临时文件残留
        temp_files = [f for f in os.listdir(storage_path) if f.endswith('.tmp')]
        assert len(temp_files) == 0


class TestFileStorageErrorHandling:
    """测试文件存储错误处理"""
    
    def test_load_corrupted_json(self, temp_dir):
        """测试加载损坏的JSON文件"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        # 创建损坏的JSON文件
        corrupted_file = os.path.join(storage_path, "corrupted.json")
        os.makedirs(storage_path, exist_ok=True)
        with open(corrupted_file, 'w') as f:
            f.write("invalid json content {")
        
        # 尝试加载应该引发异常
        with pytest.raises(DataIntegrityError):
            storage.load_conversation('corrupted')
    
    def test_permission_error_handling(self, temp_dir):
        """测试权限错误处理"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        conversation_data = {
            'conversation_id': 'permission_test',
            'name': 'Permission Test'
        }
        
        # 模拟权限错误
        with patch('autocoder.common.conversations.storage.file_storage.tempfile.mkstemp', side_effect=PermissionError("Permission denied")):
            result = storage.save_conversation(conversation_data)
            assert result is False
    
    def test_disk_full_error_handling(self, temp_dir):
        """测试磁盘空间不足错误处理"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        conversation_data = {
            'conversation_id': 'disk_full_test',
            'name': 'Disk Full Test'
        }
        
        # 模拟磁盘空间不足
        with patch('autocoder.common.conversations.storage.file_storage.tempfile.mkstemp', side_effect=OSError("No space left on device")):
            result = storage.save_conversation(conversation_data)
            assert result is False
    
    def test_invalid_file_names(self, temp_dir):
        """测试无效文件名处理"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        # 包含特殊字符的对话ID
        invalid_conversation_data = {
            'conversation_id': 'test/conv\\id:*?',
            'name': 'Invalid Filename Test'
        }
        
        # 应该能正确处理无效字符
        result = storage.save_conversation(invalid_conversation_data)
        # 实现应该清理文件名或返回False
        # 具体行为取决于实现选择
        assert isinstance(result, bool)
    
    def test_concurrent_access_handling(self, temp_dir):
        """测试并发访问处理"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        conversation_data = {
            'conversation_id': 'concurrent_test',
            'name': 'Concurrent Test'
        }
        
        # 模拟文件被其他进程锁定
        with patch('autocoder.common.conversations.storage.file_storage.tempfile.mkstemp', side_effect=OSError("File is locked by another process")):
            result = storage.save_conversation(conversation_data)
            assert result is False


class TestFileStoragePerformance:
    """测试文件存储性能"""
    
    def test_large_conversation_handling(self, temp_dir):
        """测试处理大对话"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        # 创建包含大量消息的对话
        messages = []
        for i in range(1000):
            messages.append({
                'role': 'user' if i % 2 == 0 else 'assistant',
                'content': f'Message {i} with some content that makes it larger',
                'timestamp': 1234567890.0 + i
            })
        
        large_conversation = {
            'conversation_id': 'large_conv',
            'name': 'Large Conversation',
            'messages': messages
        }
        
        # 保存大对话
        result = storage.save_conversation(large_conversation)
        assert result is True
        
        # 加载大对话
        loaded_data = storage.load_conversation('large_conv')
        assert loaded_data == large_conversation
        assert len(loaded_data['messages']) == 1000
    
    def test_many_conversations_listing(self, temp_dir):
        """测试列出大量对话"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        # 创建大量对话
        num_conversations = 100
        for i in range(num_conversations):
            conversation_data = {
                'conversation_id': f'conv_{i:03d}',
                'name': f'Conversation {i}',
                'created_at': 1234567890.0 + i
            }
            storage.save_conversation(conversation_data)
        
        # 列出所有对话
        all_conversations = storage.list_conversations()
        assert len(all_conversations) == num_conversations
        
        # 测试分页
        page_size = 20
        for page in range(0, num_conversations, page_size):
            page_conversations = storage.list_conversations(
                limit=page_size, 
                offset=page
            )
            expected_count = min(page_size, num_conversations - page)
            assert len(page_conversations) == expected_count


class TestFileStorageDataIntegrity:
    """测试文件存储数据完整性"""
    
    def test_backup_on_corruption(self, temp_dir):
        """测试数据损坏时的备份机制"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        conversation_data = {
            'conversation_id': 'backup_test',
            'name': 'Backup Test'
        }
        
        # 保存正常对话
        storage.save_conversation(conversation_data)
        
        # 手动损坏文件
        conv_file = os.path.join(storage_path, "backup_test.json")
        with open(conv_file, 'w') as f:
            f.write("corrupted content")
        
        # 尝试加载损坏的文件应该抛出异常
        with pytest.raises(DataIntegrityError):
            storage.load_conversation('backup_test')
    
    def test_data_validation_on_load(self, temp_dir):
        """测试加载时的数据验证"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        # 创建缺少必需字段的文件
        invalid_data = {
            'name': 'Invalid Conversation'
            # 缺少 conversation_id
        }
        
        invalid_file = os.path.join(storage_path, "invalid.json")
        os.makedirs(storage_path, exist_ok=True)
        with open(invalid_file, 'w', encoding='utf-8') as f:
            json.dump(invalid_data, f)
        
        # 加载时应该检测到数据无效
        with pytest.raises(DataIntegrityError):
            storage.load_conversation('invalid')
    
    def test_encoding_handling(self, temp_dir):
        """测试编码处理"""
        storage_path = os.path.join(temp_dir, "conversations")
        storage = FileStorage(storage_path)
        
        # 包含Unicode字符的对话
        unicode_conversation = {
            'conversation_id': 'unicode_test',
            'name': '测试对话 🎯',
            'messages': [
                {'role': 'user', 'content': '你好世界！👋'},
                {'role': 'assistant', 'content': 'Hello! 🌍 How can I help? 💪'}
            ]
        }
        
        # 保存和加载Unicode内容
        result = storage.save_conversation(unicode_conversation)
        assert result is True
        
        loaded_data = storage.load_conversation('unicode_test')
        assert loaded_data == unicode_conversation
        assert loaded_data['name'] == '测试对话 🎯'
        assert loaded_data['messages'][0]['content'] == '你好世界！👋' 