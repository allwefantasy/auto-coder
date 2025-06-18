








"""
测试Message和MessageBatch模型
"""

import pytest
import json
from datetime import datetime

from src.autocoder.sdk.models.messages import Message, MessageBatch


class TestMessage:
    """测试Message类"""
    
    def test_basic_initialization(self):
        """测试基础初始化
        Given: 基本的role和content参数
        When: 创建Message实例
        Then: 应该正确初始化所有字段
        """
        message = Message(role="user", content="Hello world")
        
        assert message.role == "user"
        assert message.content == "Hello world"
        assert message.timestamp is not None
        assert isinstance(message.timestamp, datetime)
        assert isinstance(message.metadata, dict)
        assert len(message.metadata) == 0
    
    def test_initialization_with_metadata(self):
        """测试带元数据的初始化
        Given: 包含元数据的参数
        When: 创建Message实例
        Then: 应该正确设置元数据
        """
        metadata = {"source": "test", "priority": "high"}
        message = Message(
            role="assistant",
            content="Response content",
            metadata=metadata
        )
        
        assert message.role == "assistant"
        assert message.content == "Response content"
        assert message.metadata == metadata
    
    def test_invalid_role_validation(self):
        """测试无效role验证
        Given: 无效的role值
        When: 创建Message实例
        Then: 应该抛出ValueError
        """
        with pytest.raises(ValueError, match="Invalid role"):
            Message(role="invalid_role", content="test content")
    
    def test_role_validation_success(self):
        """测试有效role验证
        Given: 有效的role值
        When: 创建Message实例
        Then: 应该成功创建
        """
        for role in ["user", "assistant", "system"]:
            message = Message(role=role, content="test content")
            assert message.role == role
    
    def test_to_dict(self):
        """测试to_dict方法
        Given: Message实例
        When: 调用to_dict方法
        Then: 应该返回正确的字典格式
        """
        timestamp = datetime.now()
        metadata = {"key": "value"}
        message = Message(
            role="user",
            content="test content",
            timestamp=timestamp,
            metadata=metadata
        )
        
        result = message.to_dict()
        
        assert result["role"] == "user"
        assert result["content"] == "test content"
        assert result["timestamp"] == timestamp.isoformat()
        assert result["metadata"] == metadata
    
    def test_from_dict(self):
        """测试from_dict方法
        Given: 有效的字典数据
        When: 调用from_dict方法
        Then: 应该创建正确的Message实例
        """
        timestamp = datetime.now()
        data = {
            "role": "assistant",
            "content": "response content",
            "timestamp": timestamp.isoformat(),
            "metadata": {"key": "value"}
        }
        
        message = Message.from_dict(data)
        
        assert message.role == "assistant"
        assert message.content == "response content"
        assert message.timestamp == timestamp
        assert message.metadata == {"key": "value"}
    
    def test_to_json_and_from_json(self):
        """测试JSON序列化和反序列化
        Given: Message实例
        When: 转换为JSON再转换回来
        Then: 应该保持数据完整性
        """
        original = Message(
            role="user",
            content="test content",
            metadata={"key": "value"}
        )
        
        json_str = original.to_json()
        reconstructed = Message.from_json(json_str)
        
        assert reconstructed.role == original.role
        assert reconstructed.content == original.content
        assert reconstructed.metadata == original.metadata
        # 注意：时间戳可能有微小差异，所以不做严格比较
    
    def test_metadata_operations(self):
        """测试元数据操作
        Given: Message实例
        When: 添加和获取元数据
        Then: 应该正确操作元数据
        """
        message = Message(role="user", content="test")
        
        # 添加元数据
        message.add_metadata("key1", "value1")
        message.add_metadata("key2", {"nested": "value"})
        
        # 获取元数据
        assert message.get_metadata("key1") == "value1"
        assert message.get_metadata("key2") == {"nested": "value"}
        assert message.get_metadata("nonexistent") is None
        assert message.get_metadata("nonexistent", "default") == "default"
    
    def test_role_check_methods(self):
        """测试角色检查方法
        Given: 不同角色的Message实例
        When: 调用角色检查方法
        Then: 应该返回正确的布尔值
        """
        user_msg = Message(role="user", content="test")
        assistant_msg = Message(role="assistant", content="test")
        system_msg = Message(role="system", content="test")
        
        # 用户消息检查
        assert user_msg.is_user_message() is True
        assert user_msg.is_assistant_message() is False
        assert user_msg.is_system_message() is False
        
        # 助手消息检查
        assert assistant_msg.is_user_message() is False
        assert assistant_msg.is_assistant_message() is True
        assert assistant_msg.is_system_message() is False
        
        # 系统消息检查
        assert system_msg.is_user_message() is False
        assert system_msg.is_assistant_message() is False
        assert system_msg.is_system_message() is True
    
    def test_string_representations(self):
        """测试字符串表示
        Given: Message实例
        When: 调用str()和repr()
        Then: 应该返回有意义的字符串表示
        """
        message = Message(role="user", content="This is a long test message for string representation")
        
        str_repr = str(message)
        assert "Message(role=user" in str_repr
        assert "This is a long test message for string representat..." in str_repr
        
        repr_str = repr(message)
        assert "Message(role='user'" in repr_str
        assert "This is a long test message for string representation" in repr_str


class TestMessageBatch:
    """测试MessageBatch类"""
    
    def test_basic_initialization(self):
        """测试基础初始化
        Given: 无参数创建MessageBatch
        When: 实例化对象
        Then: 应该正确初始化
        """
        batch = MessageBatch()
        
        assert len(batch.messages) == 0
        assert batch.batch_id is not None
        assert batch.created_at is not None
        assert isinstance(batch.created_at, datetime)
    
    def test_initialization_with_messages(self):
        """测试带消息的初始化
        Given: 消息列表
        When: 创建MessageBatch实例
        Then: 应该包含指定的消息
        """
        messages = [
            Message(role="user", content="Hello"),
            Message(role="assistant", content="Hi there")
        ]
        
        batch = MessageBatch(messages=messages)
        
        assert len(batch.messages) == 2
        assert batch.messages[0].content == "Hello"
        assert batch.messages[1].content == "Hi there"
    
    def test_add_message(self):
        """测试添加消息
        Given: MessageBatch实例
        When: 添加消息
        Then: 消息应该被正确添加
        """
        batch = MessageBatch()
        message = Message(role="user", content="Test message")
        
        batch.add_message(message)
        
        assert len(batch.messages) == 1
        assert batch.messages[0] == message
    
    def test_add_typed_messages(self):
        """测试添加特定类型的消息
        Given: MessageBatch实例
        When: 使用类型化的添加方法
        Then: 应该创建正确类型的消息
        """
        batch = MessageBatch()
        
        user_msg = batch.add_user_message("User message", {"source": "test"})
        assistant_msg = batch.add_assistant_message("Assistant message")
        system_msg = batch.add_system_message("System message")
        
        assert len(batch.messages) == 3
        
        assert batch.messages[0].role == "user"
        assert batch.messages[0].content == "User message"
        assert batch.messages[0].metadata == {"source": "test"}
        
        assert batch.messages[1].role == "assistant"
        assert batch.messages[1].content == "Assistant message"
        
        assert batch.messages[2].role == "system"
        assert batch.messages[2].content == "System message"
    
    def test_get_messages_by_role(self):
        """测试按角色获取消息
        Given: 包含多种角色消息的MessageBatch
        When: 按角色获取消息
        Then: 应该返回正确的消息列表
        """
        batch = MessageBatch()
        batch.add_user_message("User 1")
        batch.add_assistant_message("Assistant 1")
        batch.add_user_message("User 2")
        batch.add_system_message("System 1")
        
        user_messages = batch.get_user_messages()
        assistant_messages = batch.get_assistant_messages()
        system_messages = batch.get_system_messages()
        
        assert len(user_messages) == 2
        assert len(assistant_messages) == 1
        assert len(system_messages) == 1
        
        assert user_messages[0].content == "User 1"
        assert user_messages[1].content == "User 2"
        assert assistant_messages[0].content == "Assistant 1"
        assert system_messages[0].content == "System 1"
    
    def test_to_dict_and_from_dict(self):
        """测试字典序列化和反序列化
        Given: MessageBatch实例
        When: 转换为字典再转换回来
        Then: 应该保持数据完整性
        """
        original = MessageBatch()
        original.add_user_message("Test message")
        original.add_assistant_message("Response message")
        
        dict_data = original.to_dict()
        reconstructed = MessageBatch.from_dict(dict_data)
        
        assert len(reconstructed.messages) == len(original.messages)
        assert reconstructed.batch_id == original.batch_id
        assert reconstructed.created_at == original.created_at
        
        for i, msg in enumerate(reconstructed.messages):
            assert msg.role == original.messages[i].role
            assert msg.content == original.messages[i].content
    
    def test_json_serialization(self):
        """测试JSON序列化
        Given: MessageBatch实例
        When: 转换为JSON再转换回来
        Then: 应该保持数据完整性
        """
        original = MessageBatch()
        original.add_user_message("Test message")
        
        json_str = original.to_json()
        reconstructed = MessageBatch.from_json(json_str)
        
        assert len(reconstructed.messages) == 1
        assert reconstructed.messages[0].content == "Test message"
    
    def test_iteration_and_indexing(self):
        """测试迭代和索引访问
        Given: 包含消息的MessageBatch
        When: 进行迭代和索引访问
        Then: 应该正确工作
        """
        batch = MessageBatch()
        batch.add_user_message("Message 1")
        batch.add_user_message("Message 2")
        batch.add_user_message("Message 3")
        
        # 测试长度
        assert len(batch) == 3
        
        # 测试索引访问
        assert batch[0].content == "Message 1"
        assert batch[1].content == "Message 2"
        assert batch[2].content == "Message 3"
        
        # 测试迭代
        contents = [msg.content for msg in batch]
        assert contents == ["Message 1", "Message 2", "Message 3"]








