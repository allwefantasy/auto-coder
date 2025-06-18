




"""
Pytest 配置文件

提供测试fixtures和配置。
"""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock

from src.autocoder.sdk.models.options import AutoCodeOptions
from src.autocoder.sdk.models.messages import Message


@pytest.fixture
def temp_dir():
    """临时目录fixture"""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture
def temp_project_dir():
    """临时项目目录fixture，包含.auto-coder目录"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建项目结构
        auto_coder_dir = Path(temp_dir) / ".auto-coder"
        auto_coder_dir.mkdir()
        
        # 创建SDK会话目录
        session_dir = auto_coder_dir / "sdk" / "sessions"
        session_dir.mkdir(parents=True)
        
        yield temp_dir


@pytest.fixture
def basic_options():
    """基础选项fixture"""
    return AutoCodeOptions(
        max_turns=3,
        system_prompt="Test system prompt",
        allowed_tools=["Read", "Write"],
        permission_mode="manual"
    )


@pytest.fixture
def sample_message():
    """示例消息fixture"""
    return Message(
        role="user",
        content="This is a test message"
    )


@pytest.fixture
def sample_assistant_message():
    """示例助手消息fixture"""
    return Message(
        role="assistant", 
        content="This is a test response"
    )


@pytest.fixture
def mock_auto_coder_core():
    """模拟AutoCoderCore fixture"""
    mock = Mock()
    mock.query_sync.return_value = "Mocked response"
    
    async def mock_query_stream(prompt):
        yield Message(role="user", content=prompt)
        yield Message(role="assistant", content="Mocked response")
    
    mock.query_stream = mock_query_stream
    return mock


@pytest.fixture
def valid_session_id():
    """有效会话ID fixture"""
    return "550e8400-e29b-41d4-a716-446655440000"


@pytest.fixture
def invalid_session_id():
    """无效会话ID fixture"""
    return "invalid-session-id-format!"




