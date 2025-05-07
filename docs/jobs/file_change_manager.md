# 文件变更管理模块设计

## 1. 概述

文件变更管理模块是一个专门用于管理代码变更的组件，它提供了一种可靠的机制来应用、记录和撤销对项目文件的修改。该模块主要解决以下问题：

1. 将影子系统中的文件变更安全地应用到用户的实际项目中
2. 记录每次变更的历史，支持多版本撤销功能
3. 提供简单直观的API，便于集成到现有的编辑流程中

## 2. 核心功能

### 2.1 变更应用功能

- 将影子系统中的文件变更应用到用户项目
- 支持批量应用多个文件的变更
- 确保文件写入前目录结构已创建
- 提供变更前后的差异预览

### 2.2 变更记录功能

- 记录每次变更的详细信息（时间、文件路径、内容差异等）
- 支持变更分组，将相关变更归为一个逻辑单元
- 提供变更历史的查询接口

### 2.3 变更撤销功能

- 支持单个文件的变更撤销
- 支持批量撤销一组相关变更
- 支持多版本撤销，可以回退到任意历史版本
- 提供撤销预览功能，展示撤销后的文件状态

## 3. 架构设计

### 3.1 核心组件

#### 3.1.1 FileChangeManager

整个模块的主入口，提供高层次的API接口。

```python
class FileChangeManager:
    def __init__(self, project_dir, backup_dir=None, max_history=50):
        """
        初始化文件变更管理器
        
        Args:
            project_dir: 用户项目的根目录
            backup_dir: 备份文件存储目录，默认为项目目录下的.file_change_backups
            max_history: 最大保存的历史版本数量
        """
        pass
        
    def apply_changes(self, changes, change_group_id=None):
        """
        应用一组文件变更
        
        Args:
            changes: 文件变更字典，格式为 {file_path: FileChange}
            change_group_id: 变更组ID，用于将相关变更归为一组
            
        Returns:
            ApplyResult: 应用结果对象
        """
        pass
        
    def preview_changes(self, changes):
        """
        预览变更的差异
        
        Args:
            changes: 文件变更字典
            
        Returns:
            Dict[str, DiffResult]: 每个文件的差异结果
        """
        pass
        
    def undo_last_change(self):
        """
        撤销最近的一次变更
        
        Returns:
            UndoResult: 撤销结果对象
        """
        pass
        
    def undo_to_version(self, version_id):
        """
        撤销到指定的历史版本
        
        Args:
            version_id: 目标版本ID
            
        Returns:
            UndoResult: 撤销结果对象
        """
        pass
        
    def get_change_history(self, limit=10):
        """
        获取变更历史记录
        
        Args:
            limit: 返回的历史记录数量限制
            
        Returns:
            List[ChangeRecord]: 变更记录列表
        """
        pass
```

#### 3.1.2 FileChangeStore

负责存储和管理文件变更历史记录。

```python
class FileChangeStore:
    def __init__(self, backup_dir, max_history=50):
        """
        初始化变更存储
        
        Args:
            backup_dir: 备份文件存储目录
            max_history: 最大保存的历史版本数量
        """
        pass
        
    def save_change(self, change_record):
        """
        保存一条变更记录
        
        Args:
            change_record: 变更记录对象
            
        Returns:
            str: 变更记录ID
        """
        pass
        
    def get_change(self, change_id):
        """
        获取指定ID的变更记录
        
        Args:
            change_id: 变更记录ID
            
        Returns:
            ChangeRecord: 变更记录对象
        """
        pass
        
    def get_changes_by_group(self, group_id):
        """
        获取指定组的所有变更记录
        
        Args:
            group_id: 变更组ID
            
        Returns:
            List[ChangeRecord]: 变更记录列表
        """
        pass
        
    def get_latest_changes(self, limit=10):
        """
        获取最近的变更记录
        
        Args:
            limit: 返回的记录数量限制
            
        Returns:
            List[ChangeRecord]: 变更记录列表
        """
        pass
```

#### 3.1.3 FileBackupManager

负责文件的备份和恢复操作。

```python
class FileBackupManager:
    def __init__(self, backup_dir):
        """
        初始化备份管理器
        
        Args:
            backup_dir: 备份文件存储目录
        """
        pass
        
    def backup_file(self, file_path):
        """
        备份指定文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            str: 备份文件ID
        """
        pass
        
    def restore_file(self, file_path, backup_id):
        """
        从备份恢复文件
        
        Args:
            file_path: 目标文件路径
            backup_id: 备份文件ID
            
        Returns:
            bool: 恢复是否成功
        """
        pass
        
    def get_backup_content(self, backup_id):
        """
        获取备份文件的内容
        
        Args:
            backup_id: 备份文件ID
            
        Returns:
            str: 备份文件内容
        """
        pass
```

### 3.2 数据模型

#### 3.2.1 FileChange

表示单个文件的变更信息。

```python
class FileChange:
    def __init__(self, file_path, content, is_new=False, is_deletion=False):
        """
        初始化文件变更对象
        
        Args:
            file_path: 文件路径
            content: 文件新内容
            is_new: 是否是新文件
            is_deletion: 是否是删除操作
        """
        self.file_path = file_path
        self.content = content
        self.is_new = is_new
        self.is_deletion = is_deletion
```

#### 3.2.2 ChangeRecord

表示一条变更记录，包含变更的元数据和详细信息。

```python
class ChangeRecord:
    def __init__(self, change_id, timestamp, file_path, backup_id, 
                 is_new=False, is_deletion=False, group_id=None):
        """
        初始化变更记录对象
        
        Args:
            change_id: 变更记录ID
            timestamp: 变更时间戳
            file_path: 文件路径
            backup_id: 对应的备份文件ID
            is_new: 是否是新文件
            is_deletion: 是否是删除操作
            group_id: 变更组ID
        """
        self.change_id = change_id
        self.timestamp = timestamp
        self.file_path = file_path
        self.backup_id = backup_id
        self.is_new = is_new
        self.is_deletion = is_deletion
        self.group_id = group_id
```

#### 3.2.3 ApplyResult

表示变更应用的结果。

```python
class ApplyResult:
    def __init__(self, success, change_ids=None, errors=None):
        """
        初始化应用结果对象
        
        Args:
            success: 是否全部成功
            change_ids: 成功应用的变更ID列表
            errors: 错误信息字典，格式为 {file_path: error_message}
        """
        self.success = success
        self.change_ids = change_ids or []
        self.errors = errors or {}
```

#### 3.2.4 UndoResult

表示变更撤销的结果。

```python
class UndoResult:
    def __init__(self, success, restored_files=None, errors=None):
        """
        初始化撤销结果对象
        
        Args:
            success: 是否全部成功
            restored_files: 成功恢复的文件路径列表
            errors: 错误信息字典，格式为 {file_path: error_message}
        """
        self.success = success
        self.restored_files = restored_files or []
        self.errors = errors or {}
```

## 4. 工作流程

### 4.1 变更应用流程

1. 用户通过 `FileChangeManager.apply_changes()` 提交一组文件变更
2. 对每个文件执行以下操作：
   - 检查文件是否存在，确定是新建还是修改
   - 通过 `FileBackupManager` 备份原文件（如果存在）
   - 创建必要的目录结构
   - 写入新的文件内容
   - 创建 `ChangeRecord` 并通过 `FileChangeStore` 保存
3. 返回 `ApplyResult` 对象，包含应用结果和可能的错误信息

### 4.2 变更撤销流程

1. 用户通过 `FileChangeManager.undo_last_change()` 或 `undo_to_version()` 请求撤销
2. 系统从 `FileChangeStore` 获取需要撤销的变更记录
3. 对每个变更记录执行以下操作：
   - 如果是新建文件的变更，则删除该文件
   - 如果是修改文件的变更，通过 `FileBackupManager` 恢复备份
   - 如果是删除文件的变更，通过 `FileBackupManager` 恢复备份
4. 返回 `UndoResult` 对象，包含撤销结果和可能的错误信息

## 5. 实现细节

### 5.1 文件备份策略

为了支持多版本撤销，系统需要保存文件的历史版本。我们采用以下策略：

1. 每次文件变更前，先备份原文件
2. 备份文件使用唯一ID命名，并记录在变更记录中
3. 定期清理过旧的备份文件，只保留最近的 `max_history` 个版本

### 5.2 变更记录存储

变更记录需要持久化存储，以支持跨会话的撤销功能。我们采用以下方案：

1. 使用 JSON 文件存储变更记录，每个变更组一个文件
2. 使用 SQLite 数据库建立索引，提高查询效率
3. 定期压缩和清理过旧的变更记录

### 5.3 并发控制

为了处理可能的并发操作，我们采用以下措施：

1. 使用文件锁防止多个进程同时修改同一个文件
2. 使用事务确保变更记录和备份操作的原子性
3. 实现乐观锁机制，检测并处理冲突

### 5.4 错误处理

系统需要妥善处理各种可能的错误情况：

1. 文件系统错误（权限不足、磁盘空间不足等）
2. 并发冲突（文件被其他进程修改）
3. 数据一致性错误（变更记录与实际文件不一致）

对于每种错误，系统都应该提供清晰的错误信息和恢复建议。

## 6. 与现有系统的集成

### 6.1 与 AgenticEdit 的集成

当前的 `AgenticEdit.apply_changes()` 方法可以修改为使用新的 `FileChangeManager`：

```python
def apply_changes(self):
    """
    Apply all tracked file changes to the original project directory.
    """
    from autocoder.common.file_change_manager import FileChangeManager
    
    # 创建文件变更管理器
    manager = FileChangeManager(self.args.source_dir)
    
    # 将影子系统的变更转换为 FileChange 对象
    changes = {}
    for file_path, change in self.get_all_file_changes().items():
        changes[file_path] = FileChange(
            file_path=file_path,
            content=change.content,
            is_new=not os.path.exists(file_path)
        )
    
    # 应用变更
    result = manager.apply_changes(changes)
    
    # 处理结果
    if result.success:
        # 继续执行原有的 Git 提交等逻辑
        if not self.args.skip_commit:
            try:
                # ... 原有的 Git 提交代码 ...
            except Exception as e:
                # ... 原有的错误处理 ...
    else:
        # 处理应用变更失败的情况
        error_messages = "\n".join([f"{path}: {error}" for path, error in result.errors.items()])
        self.printer.print_str_in_terminal(
            f"Failed to apply changes:\n{error_messages}",
            style="red"
        )
```

### 6.2 提供撤销命令

在命令行界面中添加新的撤销命令：

```python
@click.command()
@click.option('--steps', default=1, help='Number of change steps to undo')
@click.option('--version-id', help='Specific version ID to revert to')
def undo(steps, version_id):
    """Undo recent file changes."""
    from autocoder.common.file_change_manager import FileChangeManager
    
    manager = FileChangeManager(os.getcwd())
    
    if version_id:
        result = manager.undo_to_version(version_id)
    else:
        # 执行多步撤销
        result = None
        for _ in range(steps):
            step_result = manager.undo_last_change()
            if not step_result.success:
                result = step_result
                break
            result = step_result
    
    if result and result.success:
        click.echo(f"Successfully undid changes to {len(result.restored_files)} files.")
    else:
        click.echo(f"Failed to undo changes: {result.errors}")
```

## 7. 未来扩展

### 7.1 图形界面集成

为 VSCode 插件提供变更历史浏览和撤销功能：

1. 显示变更历史时间线
2. 提供文件差异对比视图
3. 支持通过图形界面选择要撤销的变更

### 7.2 增强的变更分析

添加更多变更分析功能：

1. 变更影响分析，评估变更可能影响的其他文件
2. 变更冲突检测，识别可能的合并冲突
3. 变更统计报告，提供变更的数量和类型统计

### 7.3 与版本控制系统的深度集成

增强与 Git 等版本控制系统的集成：

1. 支持基于 Git 提交的变更组管理
2. 提供与 Git 分支对应的变更视图
3. 支持将变更导出为 Git 补丁

## 8. 总结

文件变更管理模块通过提供可靠的变更应用和撤销机制，增强了代码编辑系统的稳定性和用户体验。该模块不仅支持基本的变更应用功能，还提供了多版本撤销能力，使用户能够更加灵活地管理代码变更。

通过与现有系统的无缝集成，该模块可以立即为用户提供价值，同时其模块化设计也为未来的功能扩展提供了良好的基础。
