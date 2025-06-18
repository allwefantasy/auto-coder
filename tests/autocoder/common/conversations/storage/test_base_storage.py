"""
存储基类测试
"""

import pytest
from abc import ABC, abstractmethod
from autocoder.common.conversations.storage.base_storage import BaseStorage


class TestBaseStorage:
    """测试BaseStorage基类"""
    
    def test_base_storage_is_abstract(self):
        """测试BaseStorage是抽象基类"""
        # 不能直接实例化抽象基类
        with pytest.raises(TypeError):
            BaseStorage()
    
    def test_base_storage_abstract_methods(self):
        """测试BaseStorage包含必需的抽象方法"""
        # 检查抽象方法是否存在
        abstract_methods = BaseStorage.__abstractmethods__
        expected_methods = {
            'save_conversation',
            'load_conversation',
            'delete_conversation',
            'conversation_exists',
            'list_conversations'
        }
        
        assert expected_methods.issubset(abstract_methods)
    
    def test_base_storage_interface_definition(self):
        """测试基础存储接口定义"""
        # 检查方法签名是否正确
        methods = dir(BaseStorage)
        
        assert 'save_conversation' in methods
        assert 'load_conversation' in methods
        assert 'delete_conversation' in methods
        assert 'conversation_exists' in methods
        assert 'list_conversations' in methods


class MockStorage(BaseStorage):
    """模拟存储实现，用于测试"""
    
    def __init__(self):
        self.conversations = {}
    
    def save_conversation(self, conversation_data: dict) -> bool:
        """保存对话"""
        conversation_id = conversation_data.get('conversation_id')
        if conversation_id:
            self.conversations[conversation_id] = conversation_data
            return True
        return False
    
    def load_conversation(self, conversation_id: str) -> dict:
        """加载对话"""
        return self.conversations.get(conversation_id)
    
    def delete_conversation(self, conversation_id: str) -> bool:
        """删除对话"""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False
    
    def conversation_exists(self, conversation_id: str) -> bool:
        """检查对话是否存在"""
        return conversation_id in self.conversations
    
    def list_conversations(self, limit: int = None, offset: int = 0) -> list:
        """列出对话"""
        conv_list = list(self.conversations.values())
        if limit is not None:
            return conv_list[offset:offset + limit]
        return conv_list[offset:]


class TestMockStorage:
    """测试模拟存储实现"""
    
    def test_mock_storage_instantiation(self):
        """测试模拟存储可以实例化"""
        storage = MockStorage()
        assert isinstance(storage, BaseStorage)
        assert storage.conversations == {}
    
    def test_mock_storage_save_conversation(self):
        """测试保存对话"""
        storage = MockStorage()
        conversation_data = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation',
            'messages': []
        }
        
        result = storage.save_conversation(conversation_data)
        assert result is True
        assert 'test_conv' in storage.conversations
        assert storage.conversations['test_conv'] == conversation_data
    
    def test_mock_storage_save_invalid_conversation(self):
        """测试保存无效对话"""
        storage = MockStorage()
        conversation_data = {'name': 'Test'}  # 缺少conversation_id
        
        result = storage.save_conversation(conversation_data)
        assert result is False
        assert len(storage.conversations) == 0
    
    def test_mock_storage_load_conversation(self):
        """测试加载对话"""
        storage = MockStorage()
        conversation_data = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation'
        }
        storage.conversations['test_conv'] = conversation_data
        
        loaded_data = storage.load_conversation('test_conv')
        assert loaded_data == conversation_data
    
    def test_mock_storage_load_nonexistent_conversation(self):
        """测试加载不存在的对话"""
        storage = MockStorage()
        
        loaded_data = storage.load_conversation('nonexistent')
        assert loaded_data is None
    
    def test_mock_storage_delete_conversation(self):
        """测试删除对话"""
        storage = MockStorage()
        conversation_data = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation'
        }
        storage.conversations['test_conv'] = conversation_data
        
        result = storage.delete_conversation('test_conv')
        assert result is True
        assert 'test_conv' not in storage.conversations
    
    def test_mock_storage_delete_nonexistent_conversation(self):
        """测试删除不存在的对话"""
        storage = MockStorage()
        
        result = storage.delete_conversation('nonexistent')
        assert result is False
    
    def test_mock_storage_conversation_exists(self):
        """测试检查对话是否存在"""
        storage = MockStorage()
        conversation_data = {
            'conversation_id': 'test_conv',
            'name': 'Test Conversation'
        }
        storage.conversations['test_conv'] = conversation_data
        
        assert storage.conversation_exists('test_conv') is True
        assert storage.conversation_exists('nonexistent') is False
    
    def test_mock_storage_list_conversations(self):
        """测试列出对话"""
        storage = MockStorage()
        
        # 添加多个对话
        for i in range(5):
            conversation_data = {
                'conversation_id': f'conv_{i}',
                'name': f'Conversation {i}'
            }
            storage.conversations[f'conv_{i}'] = conversation_data
        
        # 测试无限制列出
        all_conversations = storage.list_conversations()
        assert len(all_conversations) == 5
        
        # 测试带限制列出
        limited_conversations = storage.list_conversations(limit=3)
        assert len(limited_conversations) == 3
        
        # 测试带偏移列出
        offset_conversations = storage.list_conversations(offset=2)
        assert len(offset_conversations) == 3
        
        # 测试带限制和偏移列出
        limited_offset_conversations = storage.list_conversations(limit=2, offset=1)
        assert len(limited_offset_conversations) == 2


class TestBaseStorageInterface:
    """测试存储接口的契约"""
    
    def test_storage_interface_contract(self):
        """测试存储接口契约"""
        storage = MockStorage()
        
        # 测试完整的存储生命周期
        conversation_data = {
            'conversation_id': 'lifecycle_test',
            'name': 'Lifecycle Test',
            'messages': [
                {'role': 'user', 'content': 'Hello'},
                {'role': 'assistant', 'content': 'Hi there!'}
            ]
        }
        
        # 1. 确认对话不存在
        assert not storage.conversation_exists('lifecycle_test')
        
        # 2. 保存对话
        assert storage.save_conversation(conversation_data) is True
        
        # 3. 确认对话存在
        assert storage.conversation_exists('lifecycle_test')
        
        # 4. 加载对话
        loaded_data = storage.load_conversation('lifecycle_test')
        assert loaded_data == conversation_data
        
        # 5. 列出对话（应该包含我们的对话）
        conversations = storage.list_conversations()
        assert len(conversations) >= 1
        assert any(conv['conversation_id'] == 'lifecycle_test' for conv in conversations)
        
        # 6. 删除对话
        assert storage.delete_conversation('lifecycle_test') is True
        
        # 7. 确认对话已删除
        assert not storage.conversation_exists('lifecycle_test')
        assert storage.load_conversation('lifecycle_test') is None


class TestStorageErrorHandling:
    """测试存储错误处理"""
    
    def test_storage_handles_empty_conversation_id(self):
        """测试处理空对话ID"""
        storage = MockStorage()
        
        # 空字符串
        assert storage.load_conversation('') is None
        assert not storage.conversation_exists('')
        assert not storage.delete_conversation('')
        
        # None值（如果实现支持的话）
        if hasattr(storage, '_handle_none_id'):
            assert storage.load_conversation(None) is None
    
    def test_storage_handles_invalid_data_types(self):
        """测试处理无效数据类型"""
        storage = MockStorage()
        
        # 非字符串对话ID
        try:
            storage.load_conversation(123)
            storage.conversation_exists(123)
            storage.delete_conversation(123)
        except TypeError:
            # 如果实现选择抛出TypeError，也是可以接受的
            pass
    
    def test_storage_consistency(self):
        """测试存储操作的一致性"""
        storage = MockStorage()
        conversation_data = {
            'conversation_id': 'consistency_test',
            'name': 'Consistency Test'
        }
        
        # 保存后立即加载应该返回相同数据
        storage.save_conversation(conversation_data)
        loaded_data = storage.load_conversation('consistency_test')
        assert loaded_data == conversation_data
        
        # 删除后再加载应该返回None
        storage.delete_conversation('consistency_test')
        loaded_data = storage.load_conversation('consistency_test')
        assert loaded_data is None 