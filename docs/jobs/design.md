
# Auto-Coder Code SDK 设计文档

## 概述

Auto-Coder Code SDK 是一个为第三方开发者提供的 Python SDK，允许通过命令行工具和 Python API 两种方式使用 Auto-Coder 的核心功能。SDK 将提供简洁易用的接口，支持多种输出格式和交互模式。

---

## 1. 接口使用说明

### 1.1 命令行接口设计

#### 基础使用模式

```bash
# 单次运行模式 (print mode) - 执行一次查询后退出
$ auto-coder.run -p "Write a function to calculate Fibonacci numbers"

# 通过管道提供输入
$ echo "Explain this code" | auto-coder.run -p

# 指定输出格式
$ auto-coder.run -p "Generate a hello world function" --output-format json

# 流式JSON输出
$ auto-coder.run -p "Build a React component" --output-format stream-json
```

#### 会话管理模式

```bash
# 继续最近的对话
$ auto-coder.run --continue

# 继续对话并提供新的提示
$ auto-coder.run --continue "Now refactor this for better performance"

# 恢复特定会话
$ auto-coder.run --resume 550e8400-e29b-41d4-a716-446655440000

# 在print模式下恢复会话
$ auto-coder.run -p --resume 550e8400-e29b-41d4-a716-446655440000 "Update the tests"
```

#### 高级用法

```bash
# 复杂的流式JSON处理
$ echo '{"type":"user","message":{"role":"user","content":[{"type":"text","text":"Explain this code"}]}}' | \
  auto-coder.run -p --output-format=stream-json --input-format=stream-json --verbose

# 在脚本中使用
#!/bin/bash
run_auto_coder() {
    local prompt="$1"
    local output_format="${2:-text}"
    
    if auto-coder.run -p "$prompt" --output-format "$output_format"; then
        echo "Success!"
    else
        echo "Error: Auto-coder failed with exit code $?" >&2
        return 1
    fi
}

# 批处理文件
$ for file in *.js; do
    echo "Processing $file..."
    auto-coder.run -p "Add JSDoc comments to this file:" < "$file" > "${file}.documented"
done
```

### 1.2 Python API 设计

#### 异步查询接口

```python
import anyio
from autocoder.sdk import query, AutoCodeOptions, Message

async def main():
    messages: list[Message] = []
    
    # 基础异步查询
    async for message in query(
        prompt="Write a haiku about foo.py",
        options=AutoCodeOptions(max_turns=3)
    ):
        messages.append(message)
    
    print(messages)

anyio.run(main)
```

#### 完整配置选项

```python
from autocoder.sdk import query, AutoCodeOptions
from pathlib import Path

# 高级配置
options = AutoCodeOptions(
    max_turns=3,
    system_prompt="You are a helpful assistant",
    cwd=Path("/path/to/project"),  # 支持字符串或Path对象
    allowed_tools=["Read", "Write", "Bash"],
    permission_mode="acceptEdits",
    output_format="json",
    stream=True,
    session_id="custom-session-id"
)

async for message in query(prompt="Hello", options=options):
    print(message)
```

#### 会话管理

```python
from autocoder.sdk import Session, AutoCodeOptions

# 创建会话
session = Session(options=AutoCodeOptions(max_turns=5))

# 在会话中进行多轮对话
result1 = await session.query("Create a Python class for managing users")
result2 = await session.query("Add a method to validate email addresses")
result3 = await session.query("Add unit tests for this class")

# 保存会话
await session.save("user_management_session")

# 恢复会话
session = await Session.load("user_management_session")
```

#### 同步接口

```python
from autocoder.sdk import query_sync, AutoCodeOptions

# 同步查询
result = query_sync(
    prompt="Write a simple calculator function",
    options=AutoCodeOptions(max_turns=1)
)
print(result)
```

---

## 2. 单元测试设计

### 2.1 命令行工具测试

```python
import pytest
import subprocess
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from autocoder.sdk.cli import AutoCoderCLI, CLIOptions

class TestAutoCoderCLI:
    
    @pytest.fixture
    def cli(self):
        """测试CLI实例fixture
        Given: 需要一个CLI实例用于测试
        When: 创建AutoCoderCLI实例
        Then: 返回可用的CLI实例
        """
        return AutoCoderCLI()
    
    @pytest.fixture
    def temp_project_dir(self):
        """创建临时项目目录fixture
        Given: 需要一个临时项目目录进行测试
        When: 创建临时目录并设置基本文件
        Then: 返回临时目录路径
        """
        with tempfile.TemporaryDirectory() as temp_dir:
            # 创建基本的项目文件
            os.makedirs(os.path.join(temp_dir, ".auto-coder"))
            yield temp_dir
    
    def test_print_mode_basic_query(self, cli, temp_project_dir):
        """测试基础print模式查询
        Given: 有效的CLI实例和简单查询
        When: 使用-p参数执行查询
        Then: 应该返回成功状态和预期输出
        """
        with patch('autocoder.sdk.core.AutoCoderCore') as mock_core:
            mock_core.return_value.query.return_value = "Test response"
            
            options = CLIOptions(
                print_mode=True,
                prompt="test query",
                output_format="text"
            )
            
            result = cli.run(options, cwd=temp_project_dir)
            
            assert result.success is True
            assert "Test response" in result.output
            mock_core.return_value.query.assert_called_once()
    
    def test_json_output_format(self, cli, temp_project_dir):
        """测试JSON输出格式
        Given: 配置为JSON输出格式的CLI选项
        When: 执行查询
        Then: 应该返回有效的JSON格式响应
        """
        expected_response = {
            "content": "test response",
            "metadata": {"tokens": 100, "model": "test-model"}
        }
        
        with patch('autocoder.sdk.core.AutoCoderCore') as mock_core:
            mock_core.return_value.query.return_value = expected_response
            
            options = CLIOptions(
                print_mode=True,
                prompt="test query",
                output_format="json"
            )
            
            result = cli.run(options, cwd=temp_project_dir)
            
            assert result.success is True
            parsed_output = json.loads(result.output)
            assert parsed_output == expected_response
    
    def test_stream_json_output(self, cli, temp_project_dir):
        """测试流式JSON输出
        Given: 配置为流式JSON输出的CLI选项
        When: 执行查询
        Then: 应该产生流式JSON输出
        """
        def mock_stream_generator():
            yield {"type": "start", "content": "Starting"}
            yield {"type": "content", "content": "Processing"}
            yield {"type": "end", "content": "Complete"}
        
        with patch('autocoder.sdk.core.AutoCoderCore') as mock_core:
            mock_core.return_value.query_stream.return_value = mock_stream_generator()
            
            options = CLIOptions(
                print_mode=True,
                prompt="test query",
                output_format="stream-json"
            )
            
            result = cli.run(options, cwd=temp_project_dir)
            
            assert result.success is True
            # 验证输出包含流式JSON
            lines = result.output.strip().split('\n')
            assert len(lines) == 3
            for line in lines:
                json.loads(line)  # 确保每行都是有效JSON
    
    def test_continue_session(self, cli, temp_project_dir):
        """测试继续会话功能
        Given: 存在历史会话的项目目录
        When: 使用--continue参数
        Then: 应该恢复最近的会话并继续对话
        """
        # 模拟存在的会话文件
        session_dir = os.path.join(temp_project_dir, ".auto-coder", "sessions")
        os.makedirs(session_dir)
        
        with patch('autocoder.sdk.session.SessionManager') as mock_session_manager:
            mock_session = Mock()
            mock_session.continue_conversation.return_value = "Continued response"
            mock_session_manager.return_value.get_latest_session.return_value = mock_session
            
            options = CLIOptions(
                continue_session=True,
                prompt="Continue with this"
            )
            
            result = cli.run(options, cwd=temp_project_dir)
            
            assert result.success is True
            assert "Continued response" in result.output
    
    def test_resume_specific_session(self, cli, temp_project_dir):
        """测试恢复特定会话
        Given: 有效的会话ID和存在的会话文件
        When: 使用--resume参数指定会话ID
        Then: 应该恢复指定的会话
        """
        session_id = "550e8400-e29b-41d4-a716-446655440000"
        
        with patch('autocoder.sdk.session.SessionManager') as mock_session_manager:
            mock_session = Mock()
            mock_session.resume.return_value = "Resumed response"
            mock_session_manager.return_value.get_session.return_value = mock_session
            
            options = CLIOptions(
                resume_session=session_id,
                prompt="Resume with this"
            )
            
            result = cli.run(options, cwd=temp_project_dir)
            
            assert result.success is True
            assert "Resumed response" in result.output
            mock_session_manager.return_value.get_session.assert_called_with(session_id)
    
    def test_stdin_input(self, cli, temp_project_dir):
        """测试从stdin读取输入
        Given: 通过stdin提供的输入内容
        When: 执行不带prompt参数的命令
        Then: 应该从stdin读取内容作为查询
        """
        stdin_content = "Explain this code: print('hello')"
        
        with patch('sys.stdin.read', return_value=stdin_content):
            with patch('autocoder.sdk.core.AutoCoderCore') as mock_core:
                mock_core.return_value.query.return_value = "Code explanation"
                
                options = CLIOptions(print_mode=True)
                
                result = cli.run(options, cwd=temp_project_dir)
                
                assert result.success is True
                mock_core.return_value.query.assert_called_once()
                call_args = mock_core.return_value.query.call_args[1]
                assert call_args['prompt'] == stdin_content
    
    def test_invalid_session_id(self, cli, temp_project_dir):
        """测试无效会话ID处理
        Given: 不存在的会话ID
        When: 尝试恢复会话
        Then: 应该返回错误信息
        """
        invalid_session_id = "invalid-session-id"
        
        with patch('autocoder.sdk.session.SessionManager') as mock_session_manager:
            mock_session_manager.return_value.get_session.side_effect = FileNotFoundError()
            
            options = CLIOptions(resume_session=invalid_session_id)
            
            result = cli.run(options, cwd=temp_project_dir)
            
            assert result.success is False
            assert "Session not found" in result.error
    
    def test_error_handling(self, cli, temp_project_dir):
        """测试错误处理
        Given: 模拟的内部错误
        When: 执行查询时发生异常
        Then: 应该捕获异常并返回友好的错误信息
        """
        with patch('autocoder.sdk.core.AutoCoderCore') as mock_core:
            mock_core.return_value.query.side_effect = Exception("Internal error")
            
            options = CLIOptions(
                print_mode=True,
                prompt="test query"
            )
            
            result = cli.run(options, cwd=temp_project_dir)
            
            assert result.success is False
            assert "Internal error" in result.error
    
    def test_verbose_mode(self, cli, temp_project_dir):
        """测试详细模式
        Given: 启用verbose模式的CLI选项
        When: 执行查询
        Then: 应该输出详细的调试信息
        """
        with patch('autocoder.sdk.core.AutoCoderCore') as mock_core:
            mock_core.return_value.query.return_value = "Response"
            
            options = CLIOptions(
                print_mode=True,
                prompt="test query",
                verbose=True
            )
            
            result = cli.run(options, cwd=temp_project_dir)
            
            assert result.success is True
            # 验证包含调试信息
            assert "[DEBUG]" in result.output or result.debug_info is not None
```

### 2.2 Python API测试

```python
import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from autocoder.sdk import query, query_sync, AutoCodeOptions, Message, Session

class TestAutoCoderSDK:
    
    @pytest.fixture
    def options(self):
        """测试选项fixture
        Given: 需要标准的测试选项
        When: 创建AutoCodeOptions实例
        Then: 返回配置好的选项
        """
        return AutoCodeOptions(
            max_turns=3,
            system_prompt="Test system prompt",
            cwd="/test/project"
        )
    
    @pytest.mark.asyncio
    async def test_basic_async_query(self, options):
        """测试基础异步查询
        Given: 有效的查询参数和选项
        When: 调用异步query函数
        Then: 应该返回预期的消息流
        """
        expected_messages = [
            Message(role="user", content="Test query"),
            Message(role="assistant", content="Test response")
        ]
        
        with patch('autocoder.sdk.core.AutoCoderCore') as mock_core:
            async def mock_query_stream(*args, **kwargs):
                for msg in expected_messages:
                    yield msg
            
            mock_core.return_value.query_stream = mock_query_stream
            
            messages = []
            async for message in query("Test query", options=options):
                messages.append(message)
            
            assert len(messages) == 2
            assert messages[0].content == "Test query"
            assert messages[1].content == "Test response"
    
    @pytest.mark.asyncio
    async def test_query_with_custom_options(self):
        """测试带自定义选项的查询
        Given: 自定义的AutoCodeOptions配置
        When: 执行查询
        Then: 应该使用指定的配置参数
        """
        custom_options = AutoCodeOptions(
            max_turns=5,
            system_prompt="Custom prompt",
            allowed_tools=["Read", "Write"],
            permission_mode="acceptEdits"
        )
        
        with patch('autocoder.sdk.core.AutoCoderCore') as mock_core:
            async def mock_query_stream(*args, **kwargs):
                yield Message(role="assistant", content="Custom response")
            
            mock_core.return_value.query_stream = mock_query_stream
            
            messages = []
            async for message in query("Test", options=custom_options):
                messages.append(message)
            
            # 验证核心组件被正确配置
            mock_core.assert_called_once()
            call_kwargs = mock_core.call_args[1]
            assert call_kwargs['max_turns'] == 5
            assert call_kwargs['system_prompt'] == "Custom prompt"
    
    def test_sync_query(self, options):
        """测试同步查询接口
        Given: 同步查询参数
        When: 调用query_sync函数
        Then: 应该返回完整的响应
        """
        expected_response = "Sync response"
        
        with patch('autocoder.sdk.core.AutoCoderCore') as mock_core:
            mock_core.return_value.query_sync.return_value = expected_response
            
            result = query_sync("Test query", options=options)
            
            assert result == expected_response
            mock_core.return_value.query_sync.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_session_management(self):
        """测试会话管理
        Given: 会话实例和多个查询
        When: 在同一会话中进行多轮对话
        Then: 应该维护对话上下文
        """
        with patch('autocoder.sdk.session.SessionManager') as mock_session_manager:
            mock_session = Mock()
            mock_session.query = AsyncMock()
            mock_session.save = AsyncMock()
            
            # 模拟多轮对话响应
            mock_session.query.side_effect = [
                "First response",
                "Second response",
                "Third response"
            ]
            
            mock_session_manager.return_value.create_session.return_value = mock_session
            
            session = Session(options=AutoCodeOptions(max_turns=3))
            
            result1 = await session.query("First query")
            result2 = await session.query("Second query")
            result3 = await session.query("Third query")
            
            assert result1 == "First response"
            assert result2 == "Second response"
            assert result3 == "Third response"
            
            # 验证查询调用次数
            assert mock_session.query.call_count == 3
    
    @pytest.mark.asyncio
    async def test_session_save_and_load(self):
        """测试会话保存和加载
        Given: 包含对话历史的会话
        When: 保存会话并重新加载
        Then: 应该恢复完整的对话历史
        """
        session_name = "test_session"
        
        with patch('autocoder.sdk.session.SessionManager') as mock_session_manager:
            # 测试保存
            mock_session = Mock()
            mock_session.save = AsyncMock()
            mock_session_manager.return_value.create_session.return_value = mock_session
            
            session = Session()
            await session.save(session_name)
            
            mock_session.save.assert_called_once_with(session_name)
            
            # 测试加载
            mock_loaded_session = Mock()
            mock_session_manager.return_value.load_session = AsyncMock(
                return_value=mock_loaded_session
            )
            
            loaded_session = await Session.load(session_name)
            
            assert loaded_session is not None
            mock_session_manager.return_value.load_session.assert_called_once_with(session_name)
    
    @pytest.mark.asyncio
    async def test_error_handling_async(self, options):
        """测试异步查询错误处理
        Given: 模拟的内部错误
        When: 执行异步查询时发生异常
        Then: 应该正确传播异常
        """
        with patch('autocoder.sdk.core.AutoCoderCore') as mock_core:
            async def mock_error_stream(*args, **kwargs):
                raise ValueError("Test error")
            
            mock_core.return_value.query_stream = mock_error_stream
            
            with pytest.raises(ValueError, match="Test error"):
                async for message in query("Test query", options=options):
                    pass
    
    def test_options_validation(self):
        """测试选项验证
        Given: 无效的选项参数
        When: 创建AutoCodeOptions实例
        Then: 应该抛出验证错误
        """
        with pytest.raises(ValueError, match="max_turns must be positive"):
            AutoCodeOptions(max_turns=-1)
        
        with pytest.raises(ValueError, match="Invalid permission_mode"):
            AutoCodeOptions(permission_mode="invalid_mode")
    
    @pytest.mark.asyncio
    async def test_stream_interruption(self, options):
        """测试流中断处理
        Given: 长时间运行的查询流
        When: 在处理过程中中断流
        Then: 应该正确清理资源
        """
        with patch('autocoder.sdk.core.AutoCoderCore') as mock_core:
            async def mock_long_stream(*args, **kwargs):
                for i in range(100):
                    yield Message(role="assistant", content=f"Message {i}")
                    await asyncio.sleep(0.01)  # 模拟处理时间
            
            mock_core.return_value.query_stream = mock_long_stream
            
            message_count = 0
            async for message in query("Test query", options=options):
                message_count += 1
                if message_count >= 5:
                    break
            
            assert message_count == 5
```

---

## 3. 业务代码实现设计

### 3.1 项目目录结构

```
src/autocoder/sdk/
├── __init__.py                 # SDK入口，导出主要接口
├── cli/                        # 命令行接口模块
│   ├── __init__.py
│   ├── main.py                # CLI主入口点
│   ├── options.py             # CLI选项定义
│   ├── formatters.py          # 输出格式化器
│   └── handlers.py            # 命令处理器
├── core/                       # 核心功能模块
│   ├── __init__.py
│   ├── bridge.py              # 桥接层，连接现有功能
│   ├── auto_coder_core.py     # AutoCoder核心封装
│   └── message_processor.py   # 消息处理器
├── session/                    # 会话管理模块
│   ├── __init__.py
│   ├── session_manager.py     # 会话管理器
│   ├── session.py             # 会话类
│   └── storage.py             # 会话存储
├── models/                     # 数据模型
│   ├── __init__.py
│   ├── options.py             # 选项模型
│   ├── messages.py            # 消息模型
│   └── responses.py           # 响应模型
├── utils/                      # 工具模块
│   ├── __init__.py
│   ├── validators.py          # 验证工具
│   ├── formatters.py          # 格式化工具
│   └── io_utils.py            # IO工具
├── exceptions.py               # 异常定义
└── constants.py               # 常量定义
```

### 3.2 核心模块划分

#### 3.2.1 CLI模块 (cli/)

**职责：**
- 解析命令行参数和选项
- 处理不同的输出格式（text、json、stream-json）
- 管理stdin/stdout交互
- 实现会话恢复和继续功能

**核心类：**
```python
class AutoCoderCLI:
    """命令行接口主类"""
    def run(self, options: CLIOptions, cwd: str = None) -> CLIResult
    def handle_print_mode(self, options: CLIOptions) -> CLIResult
    def handle_session_mode(self, options: CLIOptions) -> CLIResult

class CLIOptions:
    """CLI选项数据类"""
    print_mode: bool
    prompt: Optional[str]
    output_format: str
    input_format: str
    continue_session: bool
    resume_session: Optional[str]
    verbose: bool

class OutputFormatter:
    """输出格式化器"""
    def format_text(self, content: str) -> str
    def format_json(self, content: dict) -> str
    def format_stream_json(self, stream: AsyncIterator) -> AsyncIterator[str]
```

#### 3.2.2 核心模块 (core/)

**职责：**
- 封装现有的auto_coder_runner功能
- 提供统一的查询接口
- 处理同步和异步调用
- 管理与底层系统的桥接

**核心类：**
```python
class AutoCoderCore:
    """AutoCoder核心封装类"""
    def __init__(self, options: AutoCodeOptions)
    async def query_stream(self, prompt: str) -> AsyncIterator[Message]
    def query_sync(self, prompt: str) -> str
    def get_session_manager(self) -> SessionManager

class AutoCoderBridge:
    """桥接层，连接现有功能"""
    def __init__(self, project_root: str)
    def call_auto_command(self, query: str, **kwargs) -> Any
    def call_coding(self, query: str, **kwargs) -> Any
    def call_chat(self, query: str, **kwargs) -> Any
```

#### 3.2.3 会话管理模块 (session/)

**职责：**
- 管理会话的创建、保存和加载
- 维护对话历史和上下文
- 提供会话恢复功能
- 处理会话存储和清理

**核心类：**
```python
class SessionManager:
    """会话管理器"""
    def create_session(self, options: AutoCodeOptions) -> Session
    def get_session(self, session_id: str) -> Session
    def get_latest_session(self) -> Optional[Session]
    def list_sessions(self) -> List[SessionInfo]

class Session:
    """会话类"""
    def __init__(self, session_id: str, options: AutoCodeOptions)
    async def query(self, prompt: str) -> str
    async def save(self, name: str = None) -> None
    def get_history(self) -> List[Message]
    def continue_conversation(self, prompt: str) -> str
```

#### 3.2.4 数据模型模块 (models/)

**职责：**
- 定义所有数据结构和验证规则
- 提供类型安全的接口
- 处理数据序列化和反序列化
- 支持选项验证和默认值

**核心类：**
```python
@dataclass
class AutoCodeOptions:
    """AutoCoder选项配置"""
    max_turns: int = 3
    system_prompt: Optional[str] = None
    cwd: Optional[Union[str, Path]] = None
    allowed_tools: List[str] = field(default_factory=list)
    permission_mode: str = "manual"
    output_format: str = "text"
    stream: bool = False
    session_id: Optional[str] = None
    
    def validate(self) -> None
    def to_dict(self) -> Dict[str, Any]

@dataclass
class Message:
    """消息数据模型"""
    role: str
    content: str
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

class CLIResult:
    """CLI执行结果"""
    success: bool
    output: str
    error: Optional[str] = None
    debug_info: Optional[Dict[str, Any]] = None
```

#### 3.2.5 工具模块 (utils/)

**职责：**
- 提供通用的验证功能
- 处理输入输出格式化
- 提供文件和路径操作工具
- 实现常用的辅助函数

#### 3.2.6 异常处理模块 (exceptions.py)

**职责：**
- 定义所有自定义异常类
- 提供错误码和异常的映射关系
- 统一异常处理策略

```python
class AutoCoderSDKError(Exception):
    """SDK基础异常"""
    pass

class SessionNotFoundError(AutoCoderSDKError):
    """会话未找到异常"""
    pass

class InvalidOptionsError(AutoCoderSDKError):
    """无效选项异常"""
    pass

class BridgeError(AutoCoderSDKError):
    """桥接层异常"""
    pass
```

### 3.3 模块依赖关系

```
cli/ (CLI接口)
├── core/ (核心功能)
│   ├── session/ (会话管理)
│   ├── models/ (数据模型)
│   └── utils/ (工具函数)
├── models/ (数据模型)
├── utils/ (工具函数)
└── exceptions.py (异常处理)

core/bridge.py (桥接层)
├── autocoder.auto_coder_runner (现有功能)
├── autocoder.chat_auto_coder (现有功能)
└── models/ (数据模型)
```

---

## 4. 分阶段实现计划

### 阶段1：基础架构搭建（第1-2周）

**目标：** 建立SDK基础框架，完成核心接口定义

**步骤：**

1. **创建项目目录结构**
   ```bash
   mkdir -p src/autocoder/sdk/{cli,core,session,models,utils}
   touch src/autocoder/sdk/{__init__.py,exceptions.py,constants.py}
   ```

2. **定义核心数据模型**
   - 在`models/options.py`中实现`AutoCodeOptions`类
   - 在`models/messages.py`中实现`Message`类
   - 在`models/responses.py`中实现响应模型
   - 添加基础验证逻辑

3. **实现异常处理框架**
   ```python
   # exceptions.py
   class AutoCoderSDKError(Exception):
       """SDK基础异常类"""
       pass
   
   class SessionNotFoundError(AutoCoderSDKError):
       pass
   
   class InvalidOptionsError(AutoCoderSDKError):
       pass
   ```

4. **创建基础测试框架**
   - 设置pytest配置
   - 创建测试基础fixtures
   - 编写数据模型验证测试

**验收标准：**
- 所有模块可以正常导入
- 数据模型类型安全，验证规则完整
- 基础测试可以运行
- 项目结构符合设计要求

### 阶段2：桥接层实现（第3-4周）

**目标：** 实现与现有auto_coder_runner的桥接功能

**步骤：**

1. **分析现有接口**
   - 研究`auto_coder_runner.py`中的核心函数
   - 分析`chat_auto_coder.py`的交互模式
   - 确定需要桥接的具体功能

2. **实现桥接层**
   ```python
   # core/bridge.py
   class AutoCoderBridge:
       def __init__(self, project_root: str):
           self.project_root = project_root
           self._setup_memory()
       
       def call_auto_command(self, query: str, **kwargs) -> Any:
           # 调用现有的auto_command功能
           pass
       
       def call_coding(self, query: str, **kwargs) -> Any:
           # 调用现有的coding功能
           pass
   ```

3. **实现核心封装类**
   ```python
   # core/auto_coder_core.py
   class AutoCoderCore:
       def __init__(self, options: AutoCodeOptions):
           self.options = options
           self.bridge = AutoCoderBridge(options.cwd or os.getcwd())
       
       async def query_stream(self, prompt: str) -> AsyncIterator[Message]:
           # 实现流式查询
           pass
       
       def query_sync(self, prompt: str) -> str:
           # 实现同步查询
           pass
   ```

4. **编写桥接层测试**
   - 测试与现有功能的集成
   - 验证参数传递正确性
   - 测试错误处理机制

**验收标准：**
- 桥接层可以成功调用现有功能
- 参数转换和传递正确
- 错误处理机制完善
- 集成测试通过

### 阶段3：会话管理实现（第5-6周）

**目标：** 实现完整的会话管理功能

**步骤：**

1. **实现会话存储**
   ```python
   # session/storage.py
   class SessionStorage:
       def save_session(self, session: Session) -> None:
           pass
       
       def load_session(self, session_id: str) -> Session:
           pass
       
       def list_sessions(self) -> List[SessionInfo]:
           pass
   ```

2. **实现会话管理器**
   ```python
   # session/session_manager.py
   class SessionManager:
       def __init__(self, storage_path: str):
           self.storage = SessionStorage(storage_path)
       
       def create_session(self, options: AutoCodeOptions) -> Session:
           pass
       
       def get_latest_session(self) -> Optional[Session]:
           pass
   ```

3. **实现会话类**
   ```python
   # session/session.py
   class Session:
       def __init__(self, session_id: str, options: AutoCodeOptions):
           self.session_id = session_id
           self.options = options
           self.history: List[Message] = []
       
       async def query(self, prompt: str) -> str:
           pass
       
       async def save(self, name: str = None) -> None:
           pass
   ```

4. **编写会话管理测试**
   - 测试会话创建和保存
   - 测试会话恢复功能
   - 测试对话历史维护

**验收标准：**
- 会话可以正确创建、保存和加载
- 对话历史正确维护
- 会话恢复功能正常工作
- 会话管理测试覆盖率达到85%以上

### 阶段4：CLI接口实现（第7-8周）

**目标：** 实现完整的命令行接口功能

**步骤：**

1. **实现CLI选项解析**
   ```python
   # cli/options.py
   @dataclass
   class CLIOptions:
       print_mode: bool = False
       prompt: Optional[str] = None
       output_format: str = "text"
       continue_session: bool = False
       resume_session: Optional[str] = None
       verbose: bool = False
       
       @classmethod
       def from_args(cls, args: List[str]) -> 'CLIOptions':
           pass
   ```

2. **实现输出格式化器**
   ```python
   # cli/formatters.py
   class OutputFormatter:
       @staticmethod
       def format_text(content: str) -> str:
           return content
       
       @staticmethod
       def format_json(content: dict) -> str:
           return json.dumps(content, indent=2)
       
       @staticmethod
       async def format_stream_json(stream: AsyncIterator) -> AsyncIterator[str]:
           async for item in stream:
               yield json.dumps(item.to_dict())
   ```

3. **实现CLI主入口**
   ```python
   # cli/main.py
   class AutoCoderCLI:
       def run(self, options: CLIOptions, cwd: str = None) -> CLIResult:
           if options.print_mode:
               return self.handle_print_mode(options)
           else:
               return self.handle_session_mode(options)
   
   def main():
       # CLI主函数
       pass
   ```

4. **实现命令行工具**
   - 创建`auto-coder.run`可执行脚本
   - 处理stdin输入
   - 实现各种输出格式

**验收标准：**
- CLI工具可以正常安装和运行
- 所有命令行选项正确工作
- 输出格式化正确
- CLI测试覆盖率达到80%以上

### 阶段5：Python API实现（第9-10周）

**目标：** 实现完整的Python API接口

**步骤：**

1. **实现异步查询接口**
   ```python
   # __init__.py
   async def query(
       prompt: str, 
       options: Optional[AutoCodeOptions] = None
   ) -> AsyncIterator[Message]:
       core = AutoCoderCore(options or AutoCodeOptions())
       async for message in core.query_stream(prompt):
           yield message
   ```

2. **实现同步查询接口**
   ```python
   def query_sync(
       prompt: str, 
       options: Optional[AutoCodeOptions] = None
   ) -> str:
       core = AutoCoderCore(options or AutoCodeOptions())
       return core.query_sync(prompt)
   ```

3. **完善会话API**
   ```python
   class Session:
       @classmethod
       async def load(cls, session_name: str) -> 'Session':
           pass
       
       async def save(self, name: str) -> None:
           pass
       
       async def query(self, prompt: str) -> str:
           pass
   ```

4. **编写API使用示例**
   - 创建完整的使用示例
   - 编写API文档
   - 添加类型提示

**验收标准：**
- Python API接口完整可用
- 异步和同步接口都正常工作
- 类型提示完整准确
- API测试覆盖率达到90%以上

### 阶段6：优化和完善（第11-12周）

**目标：** 优化性能，完善用户体验和文档

**步骤：**

1. **性能优化**
   - 分析和优化查询响应时间
   - 优化会话存储性能
   - 实现连接池和缓存机制

2. **错误处理完善**
   ```python
   class AutoCoderSDK:
       def __init__(self, options: AutoCodeOptions):
           self.options = options
           self._validate_options()
       
       def _validate_options(self):
           if self.options.max_turns <= 0:
               raise InvalidOptionsError("max_turns must be positive")
   ```

3. **文档完善**
   - 编写完整的API文档
   - 创建使用指南和最佳实践
   - 添加更多使用示例

4. **集成测试**
   - 编写端到端测试
   - 性能基准测试
   - 兼容性测试

5. **打包和发布准备**
   - 配置setup.py
   - 准备PyPI发布
   - 创建安装脚本

**验收标准：**
- 性能满足预期要求（查询响应时间<2秒）
- 错误信息清晰友好
- 文档完整，用户可以快速上手
- 所有测试通过，代码质量达到发布标准
- 可以通过pip正常安装

## 设计注意事项

1. **向后兼容性**：确保SDK不会破坏现有的auto-coder功能
2. **类型安全**：使用类型提示和数据验证确保接口安全
3. **异步优先**：优先实现异步接口，同步接口作为便利封装
4. **错误处理**：提供清晰的错误信息和恢复建议
5. **可扩展性**：设计时考虑未来功能扩展的可能性
6. **测试覆盖**：严格遵循TDD原则，确保高测试覆盖率
7. **用户体验**：通过用户接口测试确保功能正确性和易用性
