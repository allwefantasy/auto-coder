# PersistConversationManager 设计文档

## 概述

`PersistConversationManager` 是一个基于文件的对话管理系统，用于持久化存储和管理 AutoCoder 项目中的对话数据。该组件提供了创建、读取、更新、删除对话的完整功能，并支持并发访问。

## 设计目标

1. **持久化存储**: 将对话数据持久化到文件系统，确保数据不丢失
2. **并发安全**: 支持多进程/多线程并发访问，避免数据竞争和损坏
3. **高性能**: 提供高效的读写操作，支持大规模对话数据
4. **易用性**: 提供简洁的 API 接口，方便开发者使用
5. **数据完整性**: 确保数据的一致性和完整性
6. **扩展性**: 支持未来功能扩展和数据格式演进

## 数据结构

### 对话消息格式

基于 `agentic_edit.py` 中的 conversations 结构：

```python
{
    "role": str,  # "system" | "user" | "assistant"
    "content": Union[str, dict, list],  # 消息内容，支持多种类型
    "timestamp": float,  # 消息创建时间戳
    "message_id": str,  # 消息唯一标识符
    "metadata": Optional[dict]  # 额外元数据
}
```

### 对话会话格式

```python
{
    "conversation_id": str,  # 对话唯一标识符
    "name": str,  # 对话名称
    "description": Optional[str],  # 对话描述
    "created_at": float,  # 创建时间戳
    "updated_at": float,  # 最后更新时间戳
    "messages": List[dict],  # 消息列表
    "metadata": Optional[dict],  # 对话元数据
    "version": int  # 数据格式版本号
}
```

## 存储架构

### 目录结构

```
conversations/
├── conversations/           # 对话数据目录
│   ├── {conversation_id}.json  # 对话文件
│   └── {conversation_id}.lock  # 文件锁
├── index/                   # 索引文件目录
│   ├── conversations.idx   # 对话索引
│   └── index.lock          # 索引锁
├── backups/                # 备份目录
│   └── {timestamp}/        # 按时间戳组织的备份
└── temp/                   # 临时文件目录
```

### 文件格式

- **对话文件**: JSON 格式，包含完整的对话数据
- **索引文件**: JSON 格式，包含对话元信息用于快速查询
- **锁文件**: 空文件，用于文件锁机制

## 核心功能

### 1. 对话管理

#### 1.1 创建对话
```python
def create_conversation(
    self, 
    name: str, 
    description: Optional[str] = None,
    initial_messages: Optional[List[dict]] = None,
    metadata: Optional[dict] = None
) -> str:
    """创建新对话并返回对话ID"""
```

#### 1.2 获取对话
```python
def get_conversation(self, conversation_id: str) -> Optional[dict]:
    """根据ID获取对话数据"""

def list_conversations(
    self, 
    limit: Optional[int] = None,
    offset: int = 0,
    filters: Optional[dict] = None
) -> List[dict]:
    """获取对话列表"""
```

#### 1.3 更新对话
```python
def update_conversation(
    self, 
    conversation_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    metadata: Optional[dict] = None
) -> bool:
    """更新对话基本信息"""
```

#### 1.4 删除对话
```python
def delete_conversation(self, conversation_id: str) -> bool:
    """删除指定对话"""
```

### 2. 消息管理

#### 2.1 添加消息
```python
def append_message(
    self, 
    conversation_id: str,
    role: str,
    content: Union[str, dict, list],
    metadata: Optional[dict] = None
) -> str:
    """向对话追加新消息，返回消息ID"""

def append_messages(
    self, 
    conversation_id: str,
    messages: List[dict]
) -> List[str]:
    """批量追加消息"""
```

#### 2.2 获取消息
```python
def get_messages(
    self, 
    conversation_id: str,
    limit: Optional[int] = None,
    offset: int = 0,
    message_ids: Optional[List[str]] = None
) -> List[dict]:
    """获取对话中的消息"""

def get_message(
    self, 
    conversation_id: str, 
    message_id: str
) -> Optional[dict]:
    """获取特定消息"""
```

#### 2.3 编辑消息
```python
def update_message(
    self, 
    conversation_id: str,
    message_id: str,
    content: Optional[Union[str, dict, list]] = None,
    metadata: Optional[dict] = None
) -> bool:
    """编辑指定消息"""
```

#### 2.4 删除消息
```python
def delete_message(
    self, 
    conversation_id: str, 
    message_id: str
) -> bool:
    """删除指定消息"""

def delete_message_pair(
    self, 
    conversation_id: str,
    user_message_id: str
) -> bool:
    """删除用户消息及其对应的助手回复"""
```

### 3. 搜索和过滤

```python
def search_conversations(
    self, 
    query: str,
    search_in_messages: bool = True,
    filters: Optional[dict] = None
) -> List[dict]:
    """搜索对话"""

def search_messages(
    self, 
    conversation_id: str,
    query: str,
    filters: Optional[dict] = None
) -> List[dict]:
    """在对话中搜索消息"""
```

## 并发控制

### 文件锁机制

1. **读取锁**: 多个读取操作可以同时进行
2. **写入锁**: 写入操作互斥，确保数据一致性
3. **超时机制**: 避免死锁，设置合理的锁超时时间

### 锁的实现

支持 Windows/Mac/Linux 所有操作系统的跨平台锁机制：

```python
import os
import sys
import time
import contextlib
from typing import Generator

# 跨平台文件锁实现
if sys.platform == "win32":
    import msvcrt
    
    class FileLocker:
        def __init__(self, lock_file: str, timeout: float = 10.0):
            self.lock_file = lock_file
            self.timeout = timeout
            self.lock_fd = None
        
        @contextlib.contextmanager
        def acquire_read_lock(self) -> Generator[None, None, None]:
            """获取读锁（共享锁）- Windows 实现"""
            self._acquire_lock(shared=True)
            try:
                yield
            finally:
                self._release_lock()
        
        @contextlib.contextmanager
        def acquire_write_lock(self) -> Generator[None, None, None]:
            """获取写锁（排他锁）- Windows 实现"""
            self._acquire_lock(shared=False)
            try:
                yield
            finally:
                self._release_lock()
        
        def _acquire_lock(self, shared: bool = False):
            """Windows 文件锁实现"""
            start_time = time.time()
            while True:
                try:
                    # 确保锁文件目录存在
                    os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
                    
                    # 打开文件用于锁定
                    self.lock_fd = open(self.lock_file, 'w+')
                    
                    # Windows 下使用 msvcrt.locking
                    if shared:
                        # Windows 不直接支持共享锁，使用文件存在性检查
                        msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
                    else:
                        msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
                    return
                    
                except (IOError, OSError):
                    if self.lock_fd:
                        self.lock_fd.close()
                        self.lock_fd = None
                    
                    if time.time() - start_time > self.timeout:
                        raise LockTimeoutError(f"Failed to acquire lock on {self.lock_file} within {self.timeout}s")
                    
                    time.sleep(0.1)
        
        def _release_lock(self):
            """释放锁"""
            if self.lock_fd:
                try:
                    msvcrt.locking(self.lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
                    self.lock_fd.close()
                finally:
                    self.lock_fd = None

else:
    # Unix/Linux/Mac 系统使用 fcntl
    import fcntl
    
    class FileLocker:
        def __init__(self, lock_file: str, timeout: float = 10.0):
            self.lock_file = lock_file
            self.timeout = timeout
            self.lock_fd = None
        
        @contextlib.contextmanager
        def acquire_read_lock(self) -> Generator[None, None, None]:
            """获取读锁（共享锁）- Unix/Linux/Mac 实现"""
            self._acquire_lock(fcntl.LOCK_SH)
            try:
                yield
            finally:
                self._release_lock()
        
        @contextlib.contextmanager
        def acquire_write_lock(self) -> Generator[None, None, None]:
            """获取写锁（排他锁）- Unix/Linux/Mac 实现"""
            self._acquire_lock(fcntl.LOCK_EX)
            try:
                yield
            finally:
                self._release_lock()
        
        def _acquire_lock(self, lock_type: int):
            """Unix/Linux/Mac 文件锁实现"""
            start_time = time.time()
            
            # 确保锁文件目录存在
            os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
            
            # 打开锁文件
            self.lock_fd = open(self.lock_file, 'w+')
            
            while True:
                try:
                    # 尝试获取非阻塞锁
                    fcntl.flock(self.lock_fd.fileno(), lock_type | fcntl.LOCK_NB)
                    return
                    
                except (IOError, OSError):
                    if time.time() - start_time > self.timeout:
                        self.lock_fd.close()
                        self.lock_fd = None
                        raise LockTimeoutError(f"Failed to acquire lock on {self.lock_file} within {self.timeout}s")
                    
                    time.sleep(0.1)
        
        def _release_lock(self):
            """释放锁"""
            if self.lock_fd:
                try:
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                    self.lock_fd.close()
                finally:
                    self.lock_fd = None

# 或者使用第三方库实现跨平台锁（推荐方案）
# 可以使用 portalocker 或 filelock 库来简化实现

# 使用 portalocker 的示例实现：
"""
import portalocker
import contextlib
from typing import Generator

class FileLocker:
    def __init__(self, lock_file: str, timeout: float = 10.0):
        self.lock_file = lock_file
        self.timeout = timeout
        self.lock_fd = None
    
    @contextlib.contextmanager
    def acquire_read_lock(self) -> Generator[None, None, None]:
        \"\"\"获取读锁（共享锁）\"\"\"
        self._acquire_lock(portalocker.LOCK_SH)
        try:
            yield
        finally:
            self._release_lock()
    
    @contextlib.contextmanager
    def acquire_write_lock(self) -> Generator[None, None, None]:
        \"\"\"获取写锁（排他锁）\"\"\"
        self._acquire_lock(portalocker.LOCK_EX)
        try:
            yield
        finally:
            self._release_lock()
    
    def _acquire_lock(self, lock_type: int):
        \"\"\"跨平台文件锁实现\"\"\"
        import os
        os.makedirs(os.path.dirname(self.lock_file), exist_ok=True)
        
        self.lock_fd = open(self.lock_file, 'w+')
        portalocker.lock(self.lock_fd, lock_type | portalocker.LOCK_NB, timeout=self.timeout)
    
    def _release_lock(self):
        \"\"\"释放锁\"\"\"
        if self.lock_fd:
            try:
                portalocker.unlock(self.lock_fd)
                self.lock_fd.close()
            finally:
                self.lock_fd = None
"""
```

### 锁机制的优势

1. **跨平台兼容**: 支持 Windows、Mac、Linux 三大主流操作系统
2. **性能优化**: Unix/Linux/Mac 系统支持真正的读写锁，Windows 系统使用文件锁机制
3. **超时控制**: 避免死锁，提供可配置的超时时间
4. **异常安全**: 使用上下文管理器确保锁的正确释放
5. **第三方库选项**: 提供 portalocker 等成熟库的集成方案

### 事务性操作

```python
@contextlib.contextmanager
def transaction(self, conversation_id: str) -> Generator[None, None, None]:
    """事务上下文管理器，确保操作的原子性"""
```

## 错误处理

### 异常类型

```python
class ConversationManagerError(Exception):
    """基础异常类"""

class ConversationNotFoundError(ConversationManagerError):
    """对话不存在异常"""

class MessageNotFoundError(ConversationManagerError):
    """消息不存在异常"""

class ConcurrencyError(ConversationManagerError):
    """并发访问异常"""

class DataIntegrityError(ConversationManagerError):
    """数据完整性异常"""

class LockTimeoutError(ConversationManagerError):
    """锁超时异常"""
```

### 错误恢复

1. **数据校验**: 读取时验证数据格式和完整性
2. **自动修复**: 检测并修复轻微的数据损坏
3. **备份恢复**: 严重损坏时从备份恢复
4. **优雅降级**: 部分功能不可用时的降级策略

## 性能优化

### 缓存机制

```python
from typing import Optional
import time

class ConversationCache:
    def __init__(self, max_size: int = 100, ttl: float = 300.0):
        self.max_size = max_size
        self.ttl = ttl
        self.cache = {}
        self.access_times = {}
    
    def get(self, key: str) -> Optional[dict]:
        """从缓存获取数据"""
        
    def set(self, key: str, value: dict) -> None:
        """设置缓存数据"""
        
    def invalidate(self, key: str) -> None:
        """使缓存失效"""
```

### 懒加载

- 索引信息优先加载
- 消息内容按需加载
- 大对话分页加载

### 批量操作

- 批量读取多个对话
- 批量写入多条消息
- 批量索引更新

## 数据备份和恢复

### 备份策略

1. **增量备份**: 定期备份变更的对话
2. **全量备份**: 定期完整备份所有数据
3. **版本控制**: 保留多个版本的备份

### 恢复机制

```python
def backup_conversation(self, conversation_id: str) -> str:
    """备份指定对话"""

def restore_conversation(self, conversation_id: str, backup_id: str) -> bool:
    """从备份恢复对话"""

def list_backups(self, conversation_id: Optional[str] = None) -> List[dict]:
    """列出可用备份"""
```

## 监控和日志

### 操作日志

- 所有CRUD操作记录
- 并发访问情况监控
- 性能指标收集

### 健康检查

```python
def health_check(self) -> dict:
    """检查系统健康状态"""
    return {
        "status": "healthy",
        "conversations_count": self.get_conversations_count(),
        "total_messages": self.get_total_messages_count(),
        "disk_usage": self.get_disk_usage(),
        "last_backup": self.get_last_backup_time(),
        "locks_status": self.get_locks_status()
    }
```

## 配置和初始化

### 配置选项

```python
@dataclass
class ConversationManagerConfig:
    storage_path: str = "./.auto-coder/conversations"
    max_cache_size: int = 100
    cache_ttl: float = 300.0
    lock_timeout: float = 10.0
    backup_enabled: bool = True
    backup_interval: float = 3600.0  # 1小时
    max_backups: int = 10
    enable_compression: bool = False
    log_level: str = "INFO"
```

### 初始化

```python
class PersistConversationManager:
    def __init__(self, config: Optional[ConversationManagerConfig] = None):
        self.config = config or ConversationManagerConfig()
        self._init_storage()
        self._init_cache()
        self._init_locks()
        self._start_background_tasks()
    
    def _init_storage(self):
        """初始化存储目录和文件"""
        
    def _init_cache(self):
        """初始化缓存系统"""
        
    def _init_locks(self):
        """初始化锁管理器"""
        
    def _start_background_tasks(self):
        """启动后台任务（备份、清理等）"""
```

## 使用示例

```python
# 初始化管理器
config = ConversationManagerConfig(
    storage_path="./.auto-coder/conversations",
    max_cache_size=200
)
manager = PersistConversationManager(config)

# 创建对话
conv_id = manager.create_conversation(
    name="代码重构讨论",
    description="关于 AutoCoder 架构重构的讨论"
)

# 添加消息
manager.append_message(
    conv_id, 
    role="user", 
    content="请帮我重构这段代码"
)

msg_id = manager.append_message(
    conv_id,
    role="assistant", 
    content={
        "type": "code_suggestion",
        "language": "python",
        "code": "# 重构后的代码...",
        "explanation": "这样重构的原因是..."
    }
)

# 获取对话
conversation = manager.get_conversation(conv_id)
messages = manager.get_messages(conv_id, limit=10)

# 编辑消息
manager.update_message(
    conv_id, 
    msg_id, 
    content="更新后的回复内容"
)

# 搜索对话
results = manager.search_conversations("重构", search_in_messages=True)

# 删除消息对
manager.delete_message_pair(conv_id, user_msg_id)

# 删除整个对话
manager.delete_conversation(conv_id)
```

## 代码实现目录结构

### 目录组织

```
src/autocoder/common/conversations/
├── __init__.py                     # 包初始化，导出主要类
├── exceptions.py                   # 异常类定义
├── models.py                      # 数据模型定义
├── config.py                      # 配置类定义
├── file_locker.py                 # 跨平台文件锁实现
├── storage/                       # 存储层
│   ├── __init__.py
│   ├── base_storage.py           # 存储基类
│   ├── file_storage.py           # 文件存储实现
│   └── index_manager.py          # 索引管理
├── cache/                         # 缓存层
│   ├── __init__.py
│   ├── base_cache.py             # 缓存基类
│   ├── memory_cache.py           # 内存缓存实现
│   └── cache_manager.py          # 缓存管理器
├── backup/                        # 备份模块
│   ├── __init__.py
│   ├── backup_manager.py         # 备份管理器
│   └── restore_manager.py        # 恢复管理器
├── search/                        # 搜索模块
│   ├── __init__.py
│   ├── text_searcher.py          # 文本搜索实现
│   └── filter_manager.py         # 过滤管理器
├── manager.py                     # 主要的 PersistConversationManager
└── utils.py                       # 工具函数

tests/autocoder/common/conversations/
├── __init__.py
├── conftest.py                    # pytest 配置和共享fixture
├── test_exceptions.py             # 异常测试
├── test_models.py                 # 数据模型测试
├── test_config.py                 # 配置测试
├── test_file_locker.py           # 文件锁测试
├── storage/
│   ├── __init__.py
│   ├── test_base_storage.py      # 存储基类测试
│   ├── test_file_storage.py      # 文件存储测试
│   └── test_index_manager.py     # 索引管理测试
├── cache/
│   ├── __init__.py
│   ├── test_memory_cache.py      # 内存缓存测试
│   └── test_cache_manager.py     # 缓存管理器测试
├── backup/
│   ├── __init__.py
│   ├── test_backup_manager.py    # 备份管理器测试
│   └── test_restore_manager.py   # 恢复管理器测试
├── search/
│   ├── __init__.py
│   ├── test_text_searcher.py     # 文本搜索测试
│   └── test_filter_manager.py    # 过滤管理器测试
├── test_manager.py               # 主管理器测试
├── test_utils.py                 # 工具函数测试
├── test_integration.py           # 集成测试
└── test_concurrency.py           # 并发测试
```

## 具体实现步骤

### 第一阶段：基础设施（可独立测试）

#### 步骤 1.1：异常类定义
**文件**: `src/autocoder/common/conversations/exceptions.py`

**实现内容**:
- 定义所有异常类的继承层次
- 每个异常类包含错误码和详细信息

**测试验证**:
```python
# test_exceptions.py
def test_exception_hierarchy():
    """测试异常类继承关系"""
    
def test_conversation_not_found_error():
    """测试对话不存在异常"""
    
def test_lock_timeout_error():
    """测试锁超时异常"""
```

#### 步骤 1.2：数据模型定义
**文件**: `src/autocoder/common/conversations/models.py`

**实现内容**:
- `ConversationMessage` 数据类
- `Conversation` 数据类
- 数据验证和序列化方法

**测试验证**:
```python
# test_models.py
def test_conversation_message_creation():
    """测试消息创建和验证"""
    
def test_conversation_message_serialization():
    """测试消息序列化/反序列化"""
    
def test_conversation_creation():
    """测试对话创建和验证"""
    
def test_conversation_validation():
    """测试数据验证规则"""
```

#### 步骤 1.3：配置类定义
**文件**: `src/autocoder/common/conversations/config.py`

**实现内容**:
- `ConversationManagerConfig` 数据类
- 配置验证和默认值处理

**测试验证**:
```python
# test_config.py
def test_config_defaults():
    """测试默认配置值"""
    
def test_config_validation():
    """测试配置验证"""
    
def test_config_from_dict():
    """测试从字典创建配置"""
```

#### 步骤 1.4：跨平台文件锁实现
**文件**: `src/autocoder/common/conversations/file_locker.py`

**实现内容**:
- 跨平台 `FileLocker` 类
- Windows/Unix 系统适配
- 超时和异常处理

**测试验证**:
```python
# test_file_locker.py
def test_file_locker_creation():
    """测试文件锁创建"""
    
def test_read_lock_acquisition():
    """测试读锁获取和释放"""
    
def test_write_lock_acquisition():
    """测试写锁获取和释放"""
    
def test_lock_timeout():
    """测试锁超时机制"""
    
def test_concurrent_read_locks():
    """测试并发读锁"""
    
def test_exclusive_write_lock():
    """测试排他写锁"""
```

### 第二阶段：存储层（依赖第一阶段）

#### 步骤 2.1：存储基类定义
**文件**: `src/autocoder/common/conversations/storage/base_storage.py`

**实现内容**:
- `BaseStorage` 抽象基类
- 定义存储接口规范

**测试验证**:
```python
# test_base_storage.py
def test_base_storage_interface():
    """测试基础存储接口定义"""
    
def test_abstract_methods():
    """测试抽象方法定义"""
```

#### 步骤 2.2：文件存储实现
**文件**: `src/autocoder/common/conversations/storage/file_storage.py`

**实现内容**:
- `FileStorage` 类实现
- JSON 文件读写操作
- 原子写入机制

**测试验证**:
```python
# test_file_storage.py
def test_file_storage_creation():
    """测试文件存储创建"""
    
def test_save_conversation():
    """测试保存对话"""
    
def test_load_conversation():
    """测试加载对话"""
    
def test_delete_conversation():
    """测试删除对话"""
    
def test_atomic_write():
    """测试原子写入机制"""
    
def test_file_corruption_handling():
    """测试文件损坏处理"""
```

#### 步骤 2.3：索引管理实现
**文件**: `src/autocoder/common/conversations/storage/index_manager.py`

**实现内容**:
- `IndexManager` 类
- 对话索引维护
- 快速查询支持

**测试验证**:
```python
# test_index_manager.py
def test_index_creation():
    """测试索引创建"""
    
def test_index_update():
    """测试索引更新"""
    
def test_index_query():
    """测试索引查询"""
    
def test_index_consistency():
    """测试索引一致性"""
```

### 第三阶段：缓存层（依赖前两阶段）

#### 步骤 3.1：缓存基类定义
**文件**: `src/autocoder/common/conversations/cache/base_cache.py`

**实现内容**:
- `BaseCache` 抽象基类
- 缓存接口规范

**测试验证**:
```python
# test_base_cache.py
def test_cache_interface():
    """测试缓存接口定义"""
```

#### 步骤 3.2：内存缓存实现
**文件**: `src/autocoder/common/conversations/cache/memory_cache.py`

**实现内容**:
- `MemoryCache` 类
- LRU 缓存策略
- TTL 支持

**测试验证**:
```python
# test_memory_cache.py
def test_cache_get_set():
    """测试缓存读写"""
    
def test_cache_lru_eviction():
    """测试LRU淘汰策略"""
    
def test_cache_ttl_expiration():
    """测试TTL过期机制"""
    
def test_cache_size_limit():
    """测试缓存大小限制"""
```

#### 步骤 3.3：缓存管理器实现
**文件**: `src/autocoder/common/conversations/cache/cache_manager.py`

**实现内容**:
- `CacheManager` 类
- 缓存策略管理
- 缓存失效处理

**测试验证**:
```python
# test_cache_manager.py
def test_cache_manager_creation():
    """测试缓存管理器创建"""
    
def test_cache_invalidation():
    """测试缓存失效处理"""
    
def test_cache_warming():
    """测试缓存预热"""
```

### 第四阶段：搜索和过滤（依赖前三阶段）

#### 步骤 4.1：文本搜索实现
**文件**: `src/autocoder/common/conversations/search/text_searcher.py`

**实现内容**:
- `TextSearcher` 类
- 全文搜索功能
- 关键词匹配

**测试验证**:
```python
# test_text_searcher.py
def test_text_search():
    """测试文本搜索功能"""
    
def test_keyword_matching():
    """测试关键词匹配"""
    
def test_search_ranking():
    """测试搜索结果排序"""
```

#### 步骤 4.2：过滤管理器实现
**文件**: `src/autocoder/common/conversations/search/filter_manager.py`

**实现内容**:
- `FilterManager` 类
- 多条件过滤
- 复合查询支持

**测试验证**:
```python
# test_filter_manager.py
def test_filter_creation():
    """测试过滤器创建"""
    
def test_multiple_filters():
    """测试多条件过滤"""
    
def test_complex_queries():
    """测试复合查询"""
```

### 第五阶段：主管理器（集成所有组件）

#### 步骤 5.1：主管理器实现
**文件**: `src/autocoder/common/conversations/manager.py`

**实现内容**:
- `PersistConversationManager` 类
- 集成所有子系统
- 提供统一API

**测试验证**:
```python
# test_manager.py
def test_manager_initialization():
    """测试管理器初始化"""
    
def test_create_conversation():
    """测试创建对话"""
    
def test_append_message():
    """测试追加消息"""
    
def test_get_conversation():
    """测试获取对话"""
    
def test_update_message():
    """测试更新消息"""
    
def test_delete_message():
    """测试删除消息"""
    
def test_delete_conversation():
    """测试删除对话"""
    
def test_search_conversations():
    """测试搜索对话"""
```

### 第六阶段：高级功能（依赖主管理器）

#### 步骤 6.1：备份管理器实现
**文件**: `src/autocoder/common/conversations/backup/backup_manager.py`

**实现内容**:
- `BackupManager` 类
- 增量和全量备份
- 备份调度

**测试验证**:
```python
# test_backup_manager.py
def test_backup_creation():
    """测试备份创建"""
    
def test_incremental_backup():
    """测试增量备份"""
    
def test_full_backup():
    """测试全量备份"""
    
def test_backup_scheduling():
    """测试备份调度"""
```

#### 步骤 6.2：恢复管理器实现
**文件**: `src/autocoder/common/conversations/backup/restore_manager.py`

**实现内容**:
- `RestoreManager` 类
- 数据恢复功能
- 版本管理

**测试验证**:
```python
# test_restore_manager.py
def test_data_restore():
    """测试数据恢复"""
    
def test_version_management():
    """测试版本管理"""
    
def test_restore_validation():
    """测试恢复验证"""
```

### 第七阶段：集成和并发测试

#### 步骤 7.1：集成测试
**文件**: `tests/autocoder/common/conversations/test_integration.py`

**测试内容**:
```python
def test_end_to_end_workflow():
    """测试端到端工作流"""
    
def test_component_integration():
    """测试组件集成"""
    
def test_error_propagation():
    """测试错误传播"""
    
def test_performance_benchmarks():
    """测试性能基准"""
```

#### 步骤 7.2：并发测试
**文件**: `tests/autocoder/common/conversations/test_concurrency.py`

**测试内容**:
```python
def test_concurrent_reads():
    """测试并发读取"""
    
def test_concurrent_writes():
    """测试并发写入"""
    
def test_read_write_contention():
    """测试读写竞争"""
    
def test_deadlock_prevention():
    """测试死锁预防"""
    
def test_high_concurrency_stress():
    """测试高并发压力"""
```

## 实施计划时间表

### 第1周：基础设施
- 异常类定义 (1天)
- 数据模型定义 (2天)  
- 配置类定义 (1天)
- 文件锁实现 (3天)

### 第2周：存储层
- 存储基类定义 (1天)
- 文件存储实现 (3天)
- 索引管理实现 (3天)

### 第3周：缓存层
- 缓存基类定义 (1天)
- 内存缓存实现 (2天)
- 缓存管理器实现 (2天)
- 单元测试补充 (2天)

### 第4周：搜索和主管理器
- 文本搜索实现 (2天)
- 过滤管理器实现 (1天)
- 主管理器实现 (4天)

### 第5周：高级功能
- 备份管理器实现 (3天)
- 恢复管理器实现 (2天)
- 文档和示例 (2天)

### 第6周：测试和优化
- 集成测试 (2天)
- 并发测试 (2天)
- 性能优化 (2天)
- 代码审查和文档完善 (1天)

## 测试运行方法

### 运行所有测试
```bash
# 在项目根目录运行
python -m pytest tests/autocoder/common/conversations/ -v

# 运行特定模块测试
python -m pytest tests/autocoder/common/conversations/test_manager.py -v

# 运行并发测试
python -m pytest tests/autocoder/common/conversations/test_concurrency.py -v --timeout=60

# 运行性能测试
python -m pytest tests/autocoder/common/conversations/test_integration.py::test_performance_benchmarks -v -s
```

### 测试覆盖率
```bash
# 安装覆盖率工具
pip install pytest-cov

# 运行覆盖率测试
python -m pytest tests/autocoder/common/conversations/ --cov=src/autocoder/common/conversations --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html
```

### 持续集成配置
每个步骤的实现都应该能够通过自动化测试验证，确保：
1. 单元测试覆盖率 > 90%
2. 所有测试都能在 CI 环境中运行
3. 每个提交都通过完整的测试套件
4. 性能回归测试自动运行

这样的实现步骤确保了每个阶段都是可测试和可验证的，降低了开发风险，提高了代码质量。

