"""
PersistConversationManager 测试配置
提供共享的 fixtures 和测试辅助函数
"""

import pytest
import tempfile
import shutil
import os
from pathlib import Path


@pytest.fixture
def temp_dir():
    """临时目录fixture"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def conversation_storage_dir(temp_dir):
    """对话存储目录fixture"""
    storage_path = os.path.join(temp_dir, "conversations")
    os.makedirs(storage_path, exist_ok=True)
    return storage_path


@pytest.fixture
def sample_message():
    """示例消息数据fixture"""
    return {
        "role": "user",
        "content": "这是一条测试消息",
        "timestamp": 1234567890.0,
        "message_id": "msg_123",
        "metadata": {"source": "test"}
    }


@pytest.fixture
def sample_conversation():
    """示例对话数据fixture"""
    return {
        "conversation_id": "conv_123",
        "name": "测试对话",
        "description": "这是一个测试对话",
        "created_at": 1234567890.0,
        "updated_at": 1234567890.0,
        "messages": [],
        "metadata": {"type": "test"},
        "version": 1
    } 