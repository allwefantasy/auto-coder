# PersistConversationManager API 文档

## 概述

`PersistConversationManager` 是一个功能完整的对话管理系统，提供对话和消息的持久化存储、缓存、搜索、备份和恢复功能。该系统支持并发访问，具有高性能和可靠性。

## 安装

```python
# 系统已经集成，直接导入使用
from autocoder.common.conversations import PersistConversationManager, ConversationManagerConfig
```

## 快速开始

### 全局获取管理器实例

```python
# 推荐方式：使用全局获取方法
from autocoder.common.conversations.get_conversation_manager import get_conversation_manager

# 使用默认配置（存储路径：当前工作目录/.auto-coder/conversations）
manager = get_conversation_manager()

# 使用自定义配置（仅在首次调用时生效）
from autocoder.common.conversations import ConversationManagerConfig

config = ConversationManagerConfig(
    storage_path="./my_conversations", 
    max_cache_size=200
)
manager = get_conversation_manager(config)

# 便捷别名
from autocoder.common.conversations.get_conversation_manager import get_manager
manager = get_manager()
```

### 基本配置

```python
from autocoder.common.conversations import (
    PersistConversationManager, 
    ConversationManagerConfig
)

# 创建配置
config = ConversationManagerConfig(
    storage_path="./my_conversations",  # 存储路径
    max_cache_size=100,                 # 缓存大小
    cache_ttl=300.0,                   # 缓存过期时间(秒)
    lock_timeout=10.0,                 # 文件锁超时时间(秒)
    backup_enabled=True,               # 启用备份
    backup_interval=3600.0,            # 备份间隔(秒)
    max_backups=10                     # 最大备份数量
)

# 创建管理器实例
manager = PersistConversationManager(config)
```

### 创建对话

```python
# 创建简单对话
conversation_id = manager.create_conversation(
    name="AI助手对话",
    description="与AI助手的日常对话"
)

# 创建带初始消息的对话
conversation_id = manager.create_conversation(
    name="代码审查",
    description="代码审查讨论",
    initial_messages=[
        {
            "role": "user",
            "content": "请帮我审查这段Python代码"
        }
    ],
    metadata={
        "project": "autocoder",
        "type": "code_review"
    }
)
```

### 消息管理

```python
# 添加消息
message_id = manager.append_message(
    conversation_id=conversation_id,
    role="assistant",
    content="我来帮您审查代码。请提供具体的代码片段。",
    metadata={"response_time": 1.2}
)

# 批量添加消息
message_ids = manager.append_messages(
    conversation_id=conversation_id,
    messages=[
        {
            "role": "user",
            "content": "def hello():\n    print('Hello World')"
        },
        {
            "role": "assistant", 
            "content": "这段代码看起来不错，建议添加文档字符串。"
        }
    ]
)

# 更新消息
success = manager.update_message(
    conversation_id=conversation_id,
    message_id=message_id,
    content="我来帮您详细审查代码。请提供具体的代码片段和上下文。"
)
```

## 核心API文档

### PersistConversationManager

#### 对话管理方法

##### `create_conversation(name, description=None, initial_messages=None, metadata=None)`
创建新对话。

**参数:**
- `name` (str): 对话名称
- `description` (str, 可选): 对话描述
- `initial_messages` (List[dict], 可选): 初始消息列表
- `metadata` (dict, 可选): 对话元数据

**返回:** `str` - 对话ID

**示例:**
```python
conv_id = manager.create_conversation(
    name="技术讨论",
    description="关于新技术的讨论", 
    metadata={"category": "tech"}
)
```

##### `get_conversation(conversation_id)`
获取对话详情。

**参数:**
- `conversation_id` (str): 对话ID

**返回:** `dict` - 对话数据，如果不存在返回None

##### `list_conversations(limit=None, offset=0, filters=None, sort_by="updated_at", sort_order="desc")`
获取对话列表。

**参数:**
- `limit` (int, 可选): 返回数量限制
- `offset` (int): 偏移量，默认0
- `filters` (dict, 可选): 过滤条件
- `sort_by` (str): 排序字段，默认"updated_at"
- `sort_order` (str): 排序方向，"asc"或"desc"

**返回:** `List[dict]` - 对话列表

**示例:**
```python
# 获取最近10个对话
conversations = manager.list_conversations(limit=10)

# 按名称过滤和排序
conversations = manager.list_conversations(
    filters={"name_contains": "代码"},
    sort_by="name",
    sort_order="asc"
)
```

##### `update_conversation(conversation_id, name=None, description=None, metadata=None)`
更新对话信息。

**参数:**
- `conversation_id` (str): 对话ID
- `name` (str, 可选): 新名称
- `description` (str, 可选): 新描述  
- `metadata` (dict, 可选): 新元数据

**返回:** `bool` - 是否成功

##### `delete_conversation(conversation_id)`
删除对话。

**参数:**
- `conversation_id` (str): 对话ID

**返回:** `bool` - 是否成功

#### 当前对话管理方法

##### `set_current_conversation(conversation_id)`
设置当前对话。

**参数:**
- `conversation_id` (str): 要设置为当前对话的ID

**返回:** `bool` - 是否成功

**异常:**
- `ConversationNotFoundError`: 如果对话不存在

**示例:**
```python
# 设置当前对话
success = manager.set_current_conversation(conv_id)
```

##### `get_current_conversation_id()`
获取当前对话ID。

**返回:** `Optional[str]` - 当前对话ID，未设置返回None

**示例:**
```python
current_id = manager.get_current_conversation_id()
if current_id:
    print(f"当前对话ID: {current_id}")
```

##### `get_current_conversation()`
获取当前对话的完整数据。

**返回:** `Optional[dict]` - 当前对话的数据字典，未设置或对话不存在返回None

**示例:**
```python
current_conv = manager.get_current_conversation()
if current_conv:
    print(f"当前对话: {current_conv['name']}")
```

##### `clear_current_conversation()`
清除当前对话设置。

**返回:** `bool` - 是否成功

**示例:**
```python
success = manager.clear_current_conversation()
```

##### `append_message_to_current(role, content, metadata=None)`
向当前对话添加消息。

**参数:**
- `role` (str): 消息角色
- `content` (str|dict|list): 消息内容
- `metadata` (dict, 可选): 消息元数据

**返回:** `str` - 消息ID

**异常:**
- `ConversationManagerError`: 如果没有设置当前对话

**示例:**
```python
# 向当前对话添加消息
message_id = manager.append_message_to_current(
    role="user",
    content="这是一条消息"
)
```

#### 消息管理方法

##### `append_message(conversation_id, role, content, metadata=None)`
向对话添加单条消息。

**参数:**
- `conversation_id` (str): 对话ID
- `role` (str): 消息角色 ("user", "assistant", "system")
- `content` (str|dict|list): 消息内容
- `metadata` (dict, 可选): 消息元数据

**返回:** `str` - 消息ID

##### `append_messages(conversation_id, messages)`
批量添加消息。

**参数:**
- `conversation_id` (str): 对话ID
- `messages` (List[dict]): 消息列表

**返回:** `List[str]` - 消息ID列表

##### `get_messages(conversation_id, limit=None, offset=0, message_ids=None)`
获取对话中的消息。

**参数:**
- `conversation_id` (str): 对话ID
- `limit` (int, 可选): 返回数量限制
- `offset` (int): 偏移量
- `message_ids` (List[str], 可选): 指定消息ID列表

**返回:** `List[dict]` - 消息列表

##### `get_message(conversation_id, message_id)`
获取特定消息。

**参数:**
- `conversation_id` (str): 对话ID
- `message_id` (str): 消息ID

**返回:** `dict` - 消息数据，如果不存在返回None

##### `update_message(conversation_id, message_id, content=None, metadata=None)`
更新消息内容。

**参数:**
- `conversation_id` (str): 对话ID
- `message_id` (str): 消息ID
- `content` (str|dict|list, 可选): 新内容
- `metadata` (dict, 可选): 新元数据

**返回:** `bool` - 是否成功

##### `delete_message(conversation_id, message_id)`
删除单条消息。

**参数:**
- `conversation_id` (str): 对话ID
- `message_id` (str): 消息ID

**返回:** `bool` - 是否成功

##### `delete_message_pair(conversation_id, user_message_id)`
删除用户消息及其对应的助手回复。

**参数:**
- `conversation_id` (str): 对话ID
- `user_message_id` (str): 用户消息ID

**返回:** `bool` - 是否成功

#### 搜索方法

##### `search_conversations(query, search_in_messages=True, filters=None)`
搜索对话。

**参数:**
- `query` (str): 搜索关键词
- `search_in_messages` (bool): 是否搜索消息内容
- `filters` (dict, 可选): 附加过滤条件

**返回:** `List[dict]` - 匹配的对话列表

**示例:**
```python
# 搜索包含"Python"的对话
results = manager.search_conversations("Python")

# 只搜索对话标题和描述
results = manager.search_conversations(
    "代码审查", 
    search_in_messages=False
)
```

##### `search_messages(conversation_id, query, filters=None)`
在对话中搜索消息。

**参数:**
- `conversation_id` (str): 对话ID
- `query` (str): 搜索关键词
- `filters` (dict, 可选): 过滤条件

**返回:** `List[dict]` - 匹配的消息列表

#### 统计和监控方法

##### `get_statistics()`
获取系统统计信息。

**返回:** `dict` - 统计数据

**示例:**
```python
stats = manager.get_statistics()
print(f"总对话数: {stats['total_conversations']}")
print(f"总消息数: {stats['total_messages']}")
print(f"缓存命中率: {stats['cache_hit_rate']:.2%}")
```

##### `health_check()`
检查系统健康状态。

**返回:** `dict` - 健康状态信息

##### `clear_cache()`
清空缓存。

**返回:** `bool` - 是否成功

##### `rebuild_index()`
重建搜索索引。

**返回:** `bool` - 是否成功

### 备份和恢复API

#### BackupManager

```python
from autocoder.common.conversations import BackupManager

backup_manager = BackupManager(config)
```

##### `create_full_backup(description=None)`
创建全量备份。

**参数:**
- `description` (str, 可选): 备份描述

**返回:** `str` - 备份ID

##### `create_incremental_backup(base_backup_id=None, description=None)`
创建增量备份。

**参数:**
- `base_backup_id` (str, 可选): 基础备份ID，默认为最新全量备份
- `description` (str, 可选): 备份描述

**返回:** `str` - 备份ID

##### `list_backups()`
列出所有备份。

**返回:** `List[BackupMetadata]` - 备份元数据列表

##### `delete_backup(backup_id)`
删除备份。

**参数:**
- `backup_id` (str): 备份ID

**返回:** `bool` - 是否成功

##### `verify_backup(backup_id)`
验证备份完整性。

**参数:**
- `backup_id` (str): 备份ID

**返回:** `bool` - 是否有效

#### RestoreManager

```python
from autocoder.common.conversations import RestoreManager

restore_manager = RestoreManager(config, backup_manager)
```

##### `restore_conversation(conversation_id, backup_id, target_directory=None)`
从备份恢复特定对话。

**参数:**
- `conversation_id` (str): 对话ID
- `backup_id` (str): 备份ID
- `target_directory` (str, 可选): 目标目录

**返回:** `bool` - 是否成功

##### `restore_full_backup(backup_id, target_directory=None, overwrite_existing=False)`
从备份恢复全部数据。

**参数:**
- `backup_id` (str): 备份ID
- `target_directory` (str, 可选): 目标目录
- `overwrite_existing` (bool): 是否覆盖现有文件

**返回:** `dict` - 恢复结果信息

##### `restore_point_in_time(target_timestamp, target_directory=None)`
恢复到指定时间点。

**参数:**
- `target_timestamp` (float): 目标时间戳
- `target_directory` (str, 可选): 目标目录

**返回:** `dict` - 恢复结果信息

## 完整使用示例

### 基本工作流

```python
from autocoder.common.conversations import (
    PersistConversationManager,
    ConversationManagerConfig,
    BackupManager
)

# 1. 初始化管理器 - 推荐使用全局获取方法
from autocoder.common.conversations.get_conversation_manager import get_conversation_manager

# 使用默认配置
manager = get_conversation_manager()

# 或使用自定义配置
config = ConversationManagerConfig(storage_path="./.auto-coder/conversations")
manager = get_conversation_manager(config)

# 2. 创建对话
conv_id = manager.create_conversation(
    name="AI编程助手",
    description="使用AI助手进行编程"
)

# 3. 添加对话消息
user_msg_id = manager.append_message(
    conversation_id=conv_id,
    role="user",
    content="请帮我写一个快速排序算法"
)

assistant_msg_id = manager.append_message(
    conversation_id=conv_id,
    role="assistant", 
    content={
        "type": "code",
        "language": "python",
        "code": '''
def quicksort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    left = [x for x in arr if x < pivot]
    middle = [x for x in arr if x == pivot]
    right = [x for x in arr if x > pivot]
    return quicksort(left) + middle + quicksort(right)
        ''',
        "explanation": "这是一个经典的快速排序实现"
    }
)

# 4. 搜索对话
results = manager.search_conversations("快速排序")
print(f"找到 {len(results)} 个相关对话")

# 5. 设置当前对话
manager.set_current_conversation(conv_id)
print(f"当前对话已设置: {conv_id}")

# 6. 向当前对话添加消息
current_msg_id = manager.append_message_to_current(
    role="user",
    content="继续讨论这个算法的时间复杂度"
)

# 7. 获取当前对话信息
current_conv = manager.get_current_conversation()
print(f"当前对话名称: {current_conv['name']}")
print(f"当前对话消息数: {len(current_conv['messages'])}")

# 8. 创建备份
backup_manager = BackupManager(config)
backup_id = backup_manager.create_full_backup("工作流示例备份")
print(f"备份创建成功: {backup_id}")
```

### 高级搜索和过滤

```python
# 按元数据过滤对话
tech_conversations = manager.list_conversations(
    filters={
        "metadata.category": "tech",
        "name_contains": "Python"
    }
)

# 复杂搜索
search_results = manager.search_conversations(
    query="Python 机器学习",
    filters={"metadata.project": "ml"}
)

# 在特定对话中搜索
code_messages = manager.search_messages(
    conversation_id=conv_id,
    query="def function",
    filters={"role": "assistant"}
)
```

## 配置选项

### ConversationManagerConfig

```python
config = ConversationManagerConfig(
    # 存储配置
    storage_path="./.auto-coder/conversations",  # 数据存储路径（默认）
    
    # 缓存配置
    max_cache_size=100,                   # 最大缓存条目数
    cache_ttl=300.0,                      # 缓存生存时间(秒)
    
    # 并发控制
    lock_timeout=10.0,                    # 文件锁超时时间(秒)
    
    # 备份配置
    backup_enabled=True,                  # 是否启用备份
    backup_interval=3600.0,               # 备份间隔(秒)
    max_backups=10,                       # 最大备份数量
    
    # 其他配置
    enable_compression=False,             # 是否启用压缩
    log_level="INFO"                      # 日志级别
)
```

## 错误处理

### 异常类型

```python
from autocoder.common.conversations import (
    ConversationManagerError,     # 基础异常
    ConversationNotFoundError,    # 对话不存在
    MessageNotFoundError,         # 消息不存在  
    ConcurrencyError,            # 并发冲突
    DataIntegrityError,          # 数据完整性错误
    LockTimeoutError,            # 锁超时
    BackupError,                 # 备份操作错误
    RestoreError                 # 恢复操作错误
)
```

### 错误处理示例

```python
try:
    conversation = manager.get_conversation("invalid_id")
except ConversationNotFoundError as e:
    print(f"对话不存在: {e}")
except ConcurrencyError as e:
    print(f"并发冲突: {e}")
    # 可以重试操作
except ConversationManagerError as e:
    print(f"系统错误: {e}")
    # 记录错误日志
```

## 最佳实践

### 1. 当前对话管理

```python
# 设置当前对话，便于后续操作
manager.set_current_conversation(conv_id)

# 使用便捷方法向当前对话添加消息
message_id = manager.append_message_to_current(
    role="user",
    content="用户输入"
)

# 获取当前对话信息
current_conv = manager.get_current_conversation()
if current_conv:
    print(f"当前对话: {current_conv['name']}")

# 在应用退出时清除当前对话（可选）
manager.clear_current_conversation()
```

### 2. 性能优化

```python
# 使用批量操作减少I/O
message_ids = manager.append_messages(conv_id, multiple_messages)

# 合理设置缓存大小
config = ConversationManagerConfig(max_cache_size=200)

# 定期清理缓存
manager.clear_cache()
```

### 2. 数据安全

```python
# 定期创建备份
backup_manager = BackupManager(config)
if backup_manager.should_create_backup()[0]:
    backup_id = backup_manager.create_full_backup()

# 验证备份完整性
for backup in backup_manager.list_backups():
    if not backup_manager.verify_backup(backup.backup_id):
        print(f"备份 {backup.backup_id} 损坏")
```

### 3. 监控和维护

```python
# 定期检查系统健康状态
health = manager.health_check()
if health["status"] != "healthy":
    print(f"系统状态异常: {health}")

# 监控统计信息
stats = manager.get_statistics()
if stats["cache_hit_rate"] < 0.8:
    print("缓存命中率较低，考虑调整缓存配置")
```

## 常见问题

### Q: 如何处理大量对话数据？

A: 使用分页查询和合理的缓存配置：
```python
# 分页获取对话
conversations = manager.list_conversations(limit=50, offset=0)

# 调整缓存大小
config = ConversationManagerConfig(max_cache_size=500)
```

### Q: 如何确保数据安全？

A: 启用备份和定期验证：
```python
# 启用自动备份
config = ConversationManagerConfig(
    backup_enabled=True,
    backup_interval=1800,  # 30分钟备份一次
    max_backups=20
)

# 定期验证备份
for backup in backup_manager.list_backups():
    backup_manager.verify_backup(backup.backup_id)
```

### Q: 如何优化搜索性能？

A: 定期重建索引和使用精确查询：
```python
# 重建索引
manager.rebuild_index()

# 使用精确查询
results = manager.search_conversations(
    "specific term",
    search_in_messages=False  # 只搜索标题和描述
)
```

### Q: 如何有效使用当前对话功能？

A: 当前对话功能可以简化频繁的对话操作：
```python
# 1. 设置当前对话
manager.set_current_conversation(conversation_id)

# 2. 直接向当前对话添加消息，无需每次指定对话ID
manager.append_message_to_current("user", "消息内容")

# 3. 检查当前对话状态
current_conv = manager.get_current_conversation()
if current_conv:
    print(f"当前对话有 {len(current_conv['messages'])} 条消息")

# 4. 应用关闭时可以保留当前对话设置，下次启动时自动恢复
current_id = manager.get_current_conversation_id()
```

### Q: 当前对话的持久化是如何工作的？

A: 当前对话ID会持久化保存在 `config.json` 文件中：
```python
# 系统会自动保存当前对话设置
manager.set_current_conversation("conv_123")

# 应用重启后，当前对话设置会自动恢复
manager = get_conversation_manager()
current_id = manager.get_current_conversation_id()  # 返回 "conv_123"
```

## 全局管理器API

### 使用 get_conversation_manager

为了简化使用，系统提供了全局获取管理器实例的方法：

```python
from autocoder.common.conversations.get_conversation_manager import (
    get_conversation_manager,
    reset_conversation_manager,
    get_conversation_manager_config
)

# 获取全局实例（使用默认配置）
manager = get_conversation_manager()

# 重置实例（用于测试或配置更改）
reset_conversation_manager()

# 获取当前配置
config = get_conversation_manager_config()
```

### 全局管理器特性

- **单例模式**：确保全局只有一个实例
- **线程安全**：支持多线程环境
- **默认配置**：存储路径为当前工作目录的 `.auto-coder/conversations`
- **配置灵活**：首次调用时可指定配置

### 便捷别名

```python
from autocoder.common.conversations.get_conversation_manager import (
    get_manager,      # = get_conversation_manager
    reset_manager,    # = reset_conversation_manager  
    get_manager_config # = get_conversation_manager_config
)
```

## 版本信息

- **当前版本**: 1.0.0
- **Python要求**: >= 3.8
- **依赖项**: 无外部依赖，使用Python标准库

## 技术特性

### 架构层次

```
PersistConversationManager (主管理器)
├── Storage Layer (存储层)
│   ├── FileStorage (文件存储)
│   └── IndexManager (索引管理)
├── Cache Layer (缓存层)
│   └── MemoryCache (内存缓存)
├── Search Layer (搜索层)
│   ├── TextSearcher (文本搜索)
│   └── FilterManager (过滤管理)
└── Backup Layer (备份层)
    ├── BackupManager (备份管理)
    └── RestoreManager (恢复管理)
```

### 并发安全

- 跨平台文件锁（Windows/Linux/Mac）
- 读写锁分离
- 超时控制避免死锁
- 原子操作保证数据一致性

### 性能特性

- LRU缓存策略
- 懒加载和分页支持
- 增量备份减少存储开销
- 索引优化提升搜索速度

---

*本文档涵盖了PersistConversationManager的主要API和使用方法。更多技术细节请参考源码和测试用例。* 