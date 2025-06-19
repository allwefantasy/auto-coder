
# Auto-Coder SDK

Auto-Coder SDK 是一个为第三方开发者提供的 Python SDK，允许通过命令行工具和 Python API 两种方式使用 Auto-Coder 的核心功能。

## 目录结构

```
src/autocoder/sdk/
├── __init__.py                 # SDK主入口，提供公共API
├── constants.py               # 常量定义（版本、默认值、配置选项等）
├── exceptions.py              # 自定义异常类
├── cli/                       # 命令行接口模块
│   ├── __init__.py
│   ├── main.py               # CLI主入口点
│   ├── options.py            # CLI选项定义
│   ├── handlers.py           # 命令处理器（打印模式、会话模式）
│   └── formatters.py         # 输出格式化器
├── core/                      # 核心功能模块
│   ├── __init__.py
│   ├── auto_coder_core.py    # AutoCoder核心封装类
│   └── bridge.py             # 桥接层，连接现有功能
├── models/                    # 数据模型
│   ├── __init__.py
│   ├── options.py            # 配置选项模型
│   ├── messages.py           # 消息模型
│   └── responses.py          # 响应模型
├── session/                   # 会话管理
│   ├── __init__.py
│   ├── session.py            # 单个会话类
│   └── session_manager.py    # 会话管理器
└── utils/                     # 工具函数
    ├── __init__.py
    ├── formatters.py         # 格式化工具
    ├── io_utils.py           # IO工具
    └── validators.py         # 验证工具
```

## 快速开始

### 1. Python API 使用

#### 基本查询

```python
import asyncio
from autocoder.sdk import query, query_sync, AutoCodeOptions

# 同步查询
response = query_sync("Write a function to calculate Fibonacci numbers")
print(response)

# 异步查询
async def async_example():
    options = AutoCodeOptions(
        max_turns=5,
        temperature=0.7,
        verbose=True
    )
    
    async for message in query("Explain how Python decorators work", options):
        print(f"[{message.role}] {message.content}")

asyncio.run(async_example())
```

#### 会话管理

```python
from autocoder.sdk import Session, AutoCodeOptions

# 创建新会话
options = AutoCodeOptions(cwd="/path/to/project")
session = Session(options=options)

# 进行对话
response1 = session.query_sync("Create a simple web server")
print(response1)

response2 = session.query_sync("Add error handling to the server")
print(response2)

# 查看对话历史
history = session.get_history()
for msg in history:
    print(f"[{msg.role}] {msg.content[:100]}...")

# 保存会话
await session.save("web_server_project")
```

#### 配置选项

```python
from autocoder.sdk import AutoCodeOptions

# 创建配置
options = AutoCodeOptions(
    max_turns=10,                    # 最大对话轮数
    system_prompt="You are a helpful coding assistant",  # 系统提示
    cwd="/path/to/project",          # 工作目录
    allowed_tools=["Read", "Write", "Bash"],  # 允许的工具
    permission_mode="acceptedits",    # 权限模式
    output_format="json",            # 输出格式
    stream=True,                     # 流式输出
    model="gpt-4",                   # 模型名称
    temperature=0.3,                 # 温度参数
    timeout=60,                      # 超时时间
    verbose=True,                    # 详细输出
    include_project_structure=True   # 包含项目结构
)

# 验证配置
options.validate()

# 转换为字典
config_dict = options.to_dict()

# 从字典创建
new_options = AutoCodeOptions.from_dict(config_dict)
```

### 2. 命令行工具使用

#### 安装和基本使用

```bash
# 单次运行模式
auto-coder.run -p "Write a function to calculate Fibonacci numbers"

# 通过管道提供输入
echo "Explain this code" | auto-coder.run -p

# 指定输出格式
auto-coder.run -p "Generate a hello world function" --output-format json

# 继续最近的对话
auto-coder.run --continue

# 恢复特定会话
auto-coder.run --resume 550e8400-e29b-41d4-a716-446655440000
```

#### 高级选项

```bash
# 设置最大对话轮数
auto-coder.run -p "Help me debug this code" --max-turns 5

# 指定系统提示
auto-coder.run -p "Create a web API" --system-prompt "You are a backend developer"

# 限制可用工具
auto-coder.run -p "Analyze this file" --allowed-tools Read Search

# 设置权限模式
auto-coder.run -p "Fix this bug" --permission-mode acceptEdits

# 详细输出
auto-coder.run -p "Optimize this algorithm" --verbose
```

## 核心组件详解

### 1. AutoCodeOptions 配置类

配置选项类，提供完整的参数配置和验证：

```python
@dataclass
class AutoCodeOptions:
    # 基础配置
    max_turns: int = 3                    # 最大对话轮数
    system_prompt: Optional[str] = None   # 系统提示
    cwd: Optional[Union[str, Path]] = None # 工作目录
    
    # 工具和权限配置
    allowed_tools: List[str] = []         # 允许的工具列表
    permission_mode: str = "manual"       # 权限模式
    
    # 输出配置
    output_format: str = "text"           # 输出格式
    stream: bool = False                  # 是否流式输出
    
    # 模型配置
    model: Optional[str] = None           # 模型名称
    temperature: float = 0.7              # 温度参数
    
    # 高级配置
    timeout: int = 30                     # 超时时间
    verbose: bool = False                 # 详细输出
    include_project_structure: bool = True # 包含项目结构
```

**支持的配置选项：**

- **输出格式**: `text`, `json`, `stream-json`
- **权限模式**: `manual`, `acceptedits`, `acceptall`
- **允许的工具**: `Read`, `Write`, `Bash`, `Search`, `Index`, `Chat`, `Design`

### 2. Message 消息模型

处理对话消息的数据结构：

```python
@dataclass
class Message:
    role: str                             # 角色：user, assistant, system
    content: str                          # 消息内容
    timestamp: Optional[datetime] = None  # 时间戳
    metadata: Dict[str, Any] = {}         # 元数据
    
    def is_user_message(self) -> bool:
        return self.role == "user"
    
    def is_assistant_message(self) -> bool:
        return self.role == "assistant"
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
```

### 3. Session 会话类

管理单个对话会话：

```python
class Session:
    def __init__(self, session_id: str = None, options: AutoCodeOptions = None):
        self.session_id = session_id or str(uuid.uuid4())
        self.options = options or AutoCodeOptions()
        
    async def query(self, prompt: str) -> str:
        """异步查询"""
        
    def query_sync(self, prompt: str) -> str:
        """同步查询"""
        
    def get_history(self) -> List[Message]:
        """获取对话历史"""
        
    async def save(self, name: str = None) -> None:
        """保存会话"""
        
    @classmethod
    async def load(cls, session_name: str) -> "Session":
        """加载会话"""
```

### 4. AutoCoderCore 核心类

提供统一的查询接口：

```python
class AutoCoderCore:
    def __init__(self, options: AutoCodeOptions):
        self.options = options
        
    async def query_stream(self, prompt: str) -> AsyncIterator[Message]:
        """异步流式查询"""
        
    def query_sync(self, prompt: str) -> str:
        """同步查询"""
```

## 异常处理

SDK 定义了完整的异常体系：

```python
from autocoder.sdk import (
    AutoCoderSDKError,      # 基础异常
    SessionNotFoundError,   # 会话未找到
    InvalidOptionsError,    # 无效选项
    BridgeError,           # 桥接层错误
    ValidationError        # 验证错误
)

try:
    response = query_sync("Hello")
except SessionNotFoundError as e:
    print(f"会话错误: {e}")
except InvalidOptionsError as e:
    print(f"配置错误: {e}")
except AutoCoderSDKError as e:
    print(f"SDK错误: {e}")
```

## 输出格式

### 1. 文本格式 (text)

```
这是一个简单的Python函数：

def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```

### 2. JSON格式 (json)

```json
{
  "content": "这是一个简单的Python函数：\n\ndef fibonacci(n):\n    if n <= 1:\n        return n\n    return fibonacci(n-1) + fibonacci(n-2)",
  "metadata": {
    "model": "gpt-4",
    "temperature": 0.7,
    "timestamp": "2024-01-01T12:00:00"
  }
}
```

### 3. 流式JSON格式 (stream-json)

```json
{"event_type": "start", "data": {"status": "started"}, "timestamp": "2024-01-01T12:00:00"}
{"event_type": "content", "data": {"content": "这是一个简单的Python函数："}, "timestamp": "2024-01-01T12:00:01"}
{"event_type": "content", "data": {"content": "\n\ndef fibonacci(n):"}, "timestamp": "2024-01-01T12:00:02"}
{"event_type": "end", "data": {"status": "completed"}, "timestamp": "2024-01-01T12:00:03"}
```

## 会话管理

### 创建和管理会话

```python
from autocoder.sdk import SessionManager, AutoCodeOptions

# 创建会话管理器
manager = SessionManager("/path/to/storage")

# 创建新会话
options = AutoCodeOptions(max_turns=10)
session = manager.create_session(options)

# 进行对话
response = session.query_sync("Create a web server")

# 保存会话
manager.save_session(session)

# 列出所有会话
sessions = manager.list_sessions()
for session_info in sessions:
    print(f"会话: {session_info.name} ({session_info.session_id})")

# 加载特定会话
loaded_session = manager.get_session("session_id")
```

## 工具和权限

### 允许的工具

- **Read**: 文件读取
- **Write**: 文件写入  
- **Bash**: 命令执行
- **Search**: 文件搜索
- **Index**: 索引操作
- **Chat**: 对话
- **Design**: 设计

### 权限模式

- **manual**: 手动确认每个操作
- **acceptedits**: 自动接受文件编辑
- **acceptall**: 自动接受所有操作

```python
# 限制工具使用
options = AutoCodeOptions(
    allowed_tools=["Read", "Search"],  # 只允许读取和搜索
    permission_mode="manual"           # 手动确认
)

# 自动接受编辑
options = AutoCodeOptions(
    permission_mode="acceptedits"      # 自动接受文件编辑
)
```

## 最佳实践

### 1. 错误处理

```python
from autocoder.sdk import query_sync, AutoCodeOptions, AutoCoderSDKError

def safe_query(prompt: str, options: AutoCodeOptions = None):
    try:
        return query_sync(prompt, options)
    except AutoCoderSDKError as e:
        print(f"SDK错误: {e}")
        return None
    except Exception as e:
        print(f"未知错误: {e}")
        return None
```

### 2. 配置管理

```python
# 创建可重用的配置
def create_coding_config():
    return AutoCodeOptions(
        max_turns=10,
        allowed_tools=["Read", "Write", "Search"],
        permission_mode="acceptedits",
        temperature=0.3,
        verbose=True
    )

def create_chat_config():
    return AutoCodeOptions(
        max_turns=5,
        allowed_tools=["Chat"],
        permission_mode="manual",
        temperature=0.7
    )
```

### 3. 会话持久化

```python
import json
from autocoder.sdk import Session

# 保存会话到文件
def save_session_to_file(session: Session, filename: str):
    session_data = {
        "session_id": session.session_id,
        "options": session.options.to_dict(),
        "history": [msg.to_dict() for msg in session.get_history()]
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2)

# 从文件加载会话
def load_session_from_file(filename: str) -> Session:
    with open(filename, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    options = AutoCodeOptions.from_dict(session_data["options"])
    session = Session(session_data["session_id"], options)
    
    # 重建历史记录
    for msg_data in session_data["history"]:
        message = Message.from_dict(msg_data)
        session.message_batch.add_message(message)
    
    return session
```

## 开发状态

当前 SDK 处于开发阶段，分为以下几个阶段：

- **阶段1** ✅: 基础架构和API设计（已完成）
- **阶段2** 🚧: 桥接层实现，连接现有auto_coder功能
- **阶段3** 📋: 会话持久化和管理功能
- **阶段4** 📋: 高级功能和优化

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 项目
2. 创建功能分支
3. 提交更改
4. 创建 Pull Request

## 许可证

本项目采用 MIT 许可证。详见 LICENSE 文件。
