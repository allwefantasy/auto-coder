"""
异常类测试
"""

import pytest
from autocoder.common.conversations.exceptions import (
    ConversationManagerError,
    ConversationNotFoundError,
    MessageNotFoundError,
    ConcurrencyError,
    DataIntegrityError,
    LockTimeoutError
)


class TestExceptionHierarchy:
    """测试异常类继承关系"""
    
    def test_conversation_manager_error_is_base_exception(self):
        """测试ConversationManagerError是基础异常"""
        error = ConversationManagerError("测试错误")
        assert isinstance(error, Exception)
        assert str(error) == "测试错误"
    
    def test_conversation_not_found_error_inheritance(self):
        """测试ConversationNotFoundError继承关系"""
        error = ConversationNotFoundError("conv_123")
        assert isinstance(error, ConversationManagerError)
        assert isinstance(error, Exception)
        assert "conv_123" in str(error)
    
    def test_message_not_found_error_inheritance(self):
        """测试MessageNotFoundError继承关系"""
        error = MessageNotFoundError("msg_123")
        assert isinstance(error, ConversationManagerError)
        assert isinstance(error, Exception)
        assert "msg_123" in str(error)
    
    def test_concurrency_error_inheritance(self):
        """测试ConcurrencyError继承关系"""
        error = ConcurrencyError("并发错误")
        assert isinstance(error, ConversationManagerError)
        assert isinstance(error, Exception)
        assert str(error) == "并发错误"
    
    def test_data_integrity_error_inheritance(self):
        """测试DataIntegrityError继承关系"""
        error = DataIntegrityError("数据完整性错误")
        assert isinstance(error, ConversationManagerError)
        assert isinstance(error, Exception)
        assert str(error) == "数据完整性错误"
    
    def test_lock_timeout_error_inheritance(self):
        """测试LockTimeoutError继承关系"""
        error = LockTimeoutError("锁超时错误")
        assert isinstance(error, ConversationManagerError)
        assert isinstance(error, Exception)
        assert str(error) == "锁超时错误"


class TestConversationNotFoundError:
    """测试ConversationNotFoundError异常"""
    
    def test_conversation_not_found_error_with_id(self):
        """测试包含对话ID的错误消息"""
        conv_id = "conv_123"
        error = ConversationNotFoundError(conv_id)
        assert conv_id in str(error)
        assert "对话" in str(error) or "Conversation" in str(error)
    
    def test_conversation_not_found_error_custom_message(self):
        """测试自定义错误消息"""
        custom_msg = "自定义对话不存在错误"
        error = ConversationNotFoundError(custom_msg)
        assert str(error) == custom_msg


class TestMessageNotFoundError:
    """测试MessageNotFoundError异常"""
    
    def test_message_not_found_error_with_id(self):
        """测试包含消息ID的错误消息"""
        msg_id = "msg_123"
        error = MessageNotFoundError(msg_id)
        assert msg_id in str(error)
        assert "消息" in str(error) or "Message" in str(error)
    
    def test_message_not_found_error_custom_message(self):
        """测试自定义错误消息"""
        custom_msg = "自定义消息不存在错误"
        error = MessageNotFoundError(custom_msg)
        assert str(error) == custom_msg


class TestLockTimeoutError:
    """测试LockTimeoutError异常"""
    
    def test_lock_timeout_error_with_file_and_timeout(self):
        """测试包含文件路径和超时时间的错误消息"""
        file_path = "/path/to/file.lock"
        timeout = 10.0
        error = LockTimeoutError(f"Failed to acquire lock on {file_path} within {timeout}s")
        
        error_str = str(error)
        assert file_path in error_str
        assert str(timeout) in error_str
        assert "lock" in error_str.lower()
    
    def test_lock_timeout_error_simple_message(self):
        """测试简单的锁超时错误消息"""
        error = LockTimeoutError("锁获取超时")
        assert str(error) == "锁获取超时"


class TestErrorCodes:
    """测试错误码功能（如果实现的话）"""
    
    def test_exception_with_error_code(self):
        """测试异常包含错误码"""
        # 如果异常类支持错误码，测试此功能
        error = ConversationManagerError("测试错误")
        # 检查是否有错误码属性
        if hasattr(error, 'error_code'):
            assert error.error_code is not None


class TestExceptionCreation:
    """测试异常创建的各种方式"""
    
    def test_create_exceptions_with_various_arguments(self):
        """测试用各种参数创建异常"""
        
        # 无参数
        error1 = ConversationManagerError()
        assert isinstance(error1, ConversationManagerError)
        
        # 字符串参数
        error2 = ConversationManagerError("错误消息")
        assert str(error2) == "错误消息"
        
        # 多个参数
        error3 = ConversationManagerError("错误", "详细信息")
        assert isinstance(error3, ConversationManagerError)
    
    def test_exception_repr(self):
        """测试异常的repr方法"""
        error = ConversationNotFoundError("conv_123")
        repr_str = repr(error)
        assert "ConversationNotFoundError" in repr_str 