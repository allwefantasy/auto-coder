"""
数据模型测试
"""

import pytest
import time
import uuid
from datetime import datetime
from autocoder.common.conversations.models import (
    ConversationMessage,
    Conversation
)


class TestConversationMessage:
    """测试ConversationMessage数据模型"""
    
    def test_conversation_message_creation_with_required_fields(self):
        """测试用必需字段创建消息"""
        message = ConversationMessage(
            role="user",
            content="Hello world"
        )
        
        assert message.role == "user"
        assert message.content == "Hello world"
        assert isinstance(message.timestamp, float)
        assert isinstance(message.message_id, str)
        assert len(message.message_id) > 0
        assert message.metadata is None
    
    def test_conversation_message_creation_with_all_fields(self):
        """测试用所有字段创建消息"""
        timestamp = time.time()
        message_id = "msg_123"
        metadata = {"source": "test", "priority": "high"}
        
        message = ConversationMessage(
            role="assistant",
            content={"type": "text", "text": "AI response"},
            timestamp=timestamp,
            message_id=message_id,
            metadata=metadata
        )
        
        assert message.role == "assistant"
        assert message.content == {"type": "text", "text": "AI response"}
        assert message.timestamp == timestamp
        assert message.message_id == message_id
        assert message.metadata == metadata
    
    def test_conversation_message_role_validation(self):
        """测试消息角色验证"""
        valid_roles = ["system", "user", "assistant"]
        
        for role in valid_roles:
            message = ConversationMessage(role=role, content="test")
            assert message.role == role
        
        # 测试无效角色
        with pytest.raises(ValueError):
            ConversationMessage(role="invalid_role", content="test")
    
    def test_conversation_message_content_types(self):
        """测试消息内容的不同类型"""
        # 字符串内容
        msg1 = ConversationMessage(role="user", content="Hello")
        assert msg1.content == "Hello"
        
        # 字典内容
        msg2 = ConversationMessage(role="user", content={"type": "code", "code": "print('hello')"})
        assert isinstance(msg2.content, dict)
        
        # 列表内容
        msg3 = ConversationMessage(role="user", content=["item1", "item2"])
        assert isinstance(msg3.content, list)
    
    def test_conversation_message_auto_generated_fields(self):
        """测试自动生成的字段"""
        message = ConversationMessage(role="user", content="test")
        
        # 验证时间戳
        assert isinstance(message.timestamp, float)
        assert message.timestamp > 0
        
        # 验证消息ID
        assert isinstance(message.message_id, str)
        assert len(message.message_id) > 0
        # 应该是UUID格式
        try:
            uuid.UUID(message.message_id)
        except ValueError:
            # 如果不是UUID，至少应该是唯一的字符串
            assert len(message.message_id) >= 8
    
    def test_conversation_message_serialization(self):
        """测试消息序列化"""
        message = ConversationMessage(
            role="user",
            content="Hello",
            metadata={"test": True}
        )
        
        # 测试to_dict方法
        data = message.to_dict()
        assert isinstance(data, dict)
        assert data["role"] == "user"
        assert data["content"] == "Hello"
        assert data["timestamp"] == message.timestamp
        assert data["message_id"] == message.message_id
        assert data["metadata"] == {"test": True}
    
    def test_conversation_message_deserialization(self):
        """测试消息反序列化"""
        data = {
            "role": "assistant",
            "content": "AI response",
            "timestamp": 1234567890.0,
            "message_id": "msg_456",
            "metadata": {"confidence": 0.95}
        }
        
        message = ConversationMessage.from_dict(data)
        assert message.role == "assistant"
        assert message.content == "AI response"
        assert message.timestamp == 1234567890.0
        assert message.message_id == "msg_456"
        assert message.metadata == {"confidence": 0.95}
    
    def test_conversation_message_validation(self):
        """测试消息数据验证"""
        # 空角色
        with pytest.raises(ValueError):
            ConversationMessage(role="", content="test")
        
        # None角色
        with pytest.raises(ValueError):
            ConversationMessage(role=None, content="test")
        
        # 空内容
        with pytest.raises(ValueError):
            ConversationMessage(role="user", content="")
        
        # None内容
        with pytest.raises(ValueError):
            ConversationMessage(role="user", content=None)


class TestConversation:
    """测试Conversation数据模型"""
    
    def test_conversation_creation_with_required_fields(self):
        """测试用必需字段创建对话"""
        conversation = Conversation(name="测试对话")
        
        assert conversation.name == "测试对话"
        assert isinstance(conversation.conversation_id, str)
        assert len(conversation.conversation_id) > 0
        assert isinstance(conversation.created_at, float)
        assert isinstance(conversation.updated_at, float)
        assert conversation.description is None
        assert conversation.messages == []
        assert conversation.metadata is None
        assert conversation.version == 1
    
    def test_conversation_creation_with_all_fields(self):
        """测试用所有字段创建对话"""
        conversation_id = "conv_123"
        created_at = time.time()
        updated_at = created_at + 100
        messages = [{"role": "user", "content": "hello"}]
        metadata = {"category": "test"}
        
        conversation = Conversation(
            conversation_id=conversation_id,
            name="完整测试对话",
            description="这是一个完整的测试对话",
            created_at=created_at,
            updated_at=updated_at,
            messages=messages,
            metadata=metadata,
            version=2
        )
        
        assert conversation.conversation_id == conversation_id
        assert conversation.name == "完整测试对话"
        assert conversation.description == "这是一个完整的测试对话"
        assert conversation.created_at == created_at
        assert conversation.updated_at == updated_at
        assert conversation.messages == messages
        assert conversation.metadata == metadata
        assert conversation.version == 2
    
    def test_conversation_auto_generated_fields(self):
        """测试自动生成的字段"""
        conversation = Conversation(name="测试")
        
        # 验证对话ID
        assert isinstance(conversation.conversation_id, str)
        assert len(conversation.conversation_id) > 0
        try:
            uuid.UUID(conversation.conversation_id)
        except ValueError:
            # 如果不是UUID，至少应该是唯一的字符串
            assert len(conversation.conversation_id) >= 8
        
        # 验证时间戳
        assert isinstance(conversation.created_at, float)
        assert isinstance(conversation.updated_at, float)
        assert conversation.created_at > 0
        assert conversation.updated_at >= conversation.created_at
    
    def test_conversation_serialization(self):
        """测试对话序列化"""
        conversation = Conversation(
            name="测试对话",
            description="测试描述",
            metadata={"type": "test"}
        )
        
        data = conversation.to_dict()
        assert isinstance(data, dict)
        assert data["conversation_id"] == conversation.conversation_id
        assert data["name"] == "测试对话"
        assert data["description"] == "测试描述"
        assert data["created_at"] == conversation.created_at
        assert data["updated_at"] == conversation.updated_at
        assert data["messages"] == []
        assert data["metadata"] == {"type": "test"}
        assert data["version"] == 1
    
    def test_conversation_deserialization(self):
        """测试对话反序列化"""
        data = {
            "conversation_id": "conv_789",
            "name": "反序列化测试",
            "description": "测试反序列化功能",
            "created_at": 1234567890.0,
            "updated_at": 1234567999.0,
            "messages": [{"role": "user", "content": "test"}],
            "metadata": {"source": "test"},
            "version": 1
        }
        
        conversation = Conversation.from_dict(data)
        assert conversation.conversation_id == "conv_789"
        assert conversation.name == "反序列化测试"
        assert conversation.description == "测试反序列化功能"
        assert conversation.created_at == 1234567890.0
        assert conversation.updated_at == 1234567999.0
        assert conversation.messages == [{"role": "user", "content": "test"}]
        assert conversation.metadata == {"source": "test"}
        assert conversation.version == 1
    
    def test_conversation_validation(self):
        """测试对话数据验证"""
        # 空名称
        with pytest.raises(ValueError):
            Conversation(name="")
        
        # None名称
        with pytest.raises(ValueError):
            Conversation(name=None)
        
        # 无效版本号
        with pytest.raises(ValueError):
            Conversation(name="test", version=0)
        
        with pytest.raises(ValueError):
            Conversation(name="test", version=-1)
    
    def test_conversation_add_message(self):
        """测试向对话添加消息"""
        conversation = Conversation(name="测试对话")
        original_updated_at = conversation.updated_at
        
        # 等待一小段时间确保时间戳变化
        import time
        time.sleep(0.01)
        
        message = ConversationMessage(role="user", content="Hello")
        conversation.add_message(message)
        
        assert len(conversation.messages) == 1
        assert conversation.messages[0] == message.to_dict()
        assert conversation.updated_at > original_updated_at
    
    def test_conversation_remove_message(self):
        """测试从对话中删除消息"""
        conversation = Conversation(name="测试对话")
        message = ConversationMessage(role="user", content="Hello")
        conversation.add_message(message)
        
        assert len(conversation.messages) == 1
        
        removed = conversation.remove_message(message.message_id)
        assert removed is True
        assert len(conversation.messages) == 0
        
        # 尝试删除不存在的消息
        removed = conversation.remove_message("nonexistent")
        assert removed is False
    
    def test_conversation_get_message(self):
        """测试从对话中获取消息"""
        conversation = Conversation(name="测试对话")
        message = ConversationMessage(role="user", content="Hello")
        conversation.add_message(message)
        
        retrieved = conversation.get_message(message.message_id)
        assert retrieved is not None
        assert retrieved["message_id"] == message.message_id
        assert retrieved["content"] == "Hello"
        
        # 获取不存在的消息
        not_found = conversation.get_message("nonexistent")
        assert not_found is None


class TestModelIntegration:
    """测试模型集成功能"""
    
    def test_message_and_conversation_integration(self):
        """测试消息和对话的集成"""
        conversation = Conversation(name="集成测试")
        
        # 添加用户消息
        user_msg = ConversationMessage(role="user", content="Hello AI")
        conversation.add_message(user_msg)
        
        # 添加助手回复
        assistant_msg = ConversationMessage(role="assistant", content="Hello human!")
        conversation.add_message(assistant_msg)
        
        assert len(conversation.messages) == 2
        assert conversation.messages[0]["role"] == "user"
        assert conversation.messages[1]["role"] == "assistant"
    
    def test_serialization_round_trip(self):
        """测试序列化往返转换"""
        # 创建对话和消息
        conversation = Conversation(name="往返测试", description="测试序列化往返")
        message = ConversationMessage(role="user", content="Test message")
        conversation.add_message(message)
        
        # 序列化
        data = conversation.to_dict()
        
        # 反序列化
        restored_conversation = Conversation.from_dict(data)
        
        # 验证数据一致性
        assert restored_conversation.conversation_id == conversation.conversation_id
        assert restored_conversation.name == conversation.name
        assert restored_conversation.description == conversation.description
        assert len(restored_conversation.messages) == len(conversation.messages)
        assert restored_conversation.messages[0]["content"] == "Test message" 