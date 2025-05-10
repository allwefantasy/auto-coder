# 对话回滚功能设计

## 1. 功能概述

当前 AgenticEdit 类已经支持文件变更的回滚功能，但缺少对应的对话状态回滚能力。本设计旨在增强现有的文件回滚机制，使其能够同时保存和恢复对话状态（`current_conversations` 属性），实现完整的会话回滚功能。

## 2. 现状分析

### 2.1 现有文件变更管理机制

目前系统使用 `FileChangeManager` 类管理文件变更，主要功能包括：
- 文件变更的记录与跟踪
- 变更的分组管理（通过 `change_group_id`）
- 变更的撤销（单个变更、变更组、回滚到特定版本）
- 文件备份与恢复

当 `WriteToFileToolResolver` 和 `ReplaceInFileToolResolver` 中的 `resolve` 方法被调用时，会通过 `FileChangeManager` 记录文件变更。而 AgenticEdit 中的 `apply_changes` 方法主要负责触发 git commit 提交操作。

### 2.2 当前对话管理机制

AgenticEdit 类中的 `current_conversations` 属性用于存储当前会话的对话历史，但目前没有与文件变更同步保存和恢复的机制。

## 3. 设计方案

### 3.1 核心思路

将对话状态（`current_conversations`）与文件变更绑定，在每次文件变更时同时保存对话状态，并在回滚文件变更时恢复对应的对话状态。

### 3.2 数据模型扩展

#### 3.2.1 创建 ConversationCheckpoint 类

```python
class ConversationCheckpoint(BaseModel):
    """对话检查点，用于保存特定时刻的对话状态"""
    
    checkpoint_id: str  # 检查点ID，与变更组ID对应
    timestamp: float  # 创建时间戳
    conversations: List[Dict[str, Any]]  # 对话历史
    metadata: Optional[Dict[str, Any]] = None  # 元数据，可包含额外信息
```

#### 3.2.2 创建 ConversationCheckpointStore 类

```python
class ConversationCheckpointStore:
    """对话检查点存储管理器"""
    
    def __init__(self, store_dir: Optional[str] = None, max_history: int = 50):
        """
        初始化对话检查点存储
        
        Args:
            store_dir: 存储目录，默认为用户主目录下的.autocoder/conversation_checkpoints
            max_history: 最大保存的历史版本数量
        """
        # 实现初始化逻辑...
    
    def save_checkpoint(self, checkpoint: ConversationCheckpoint) -> str:
        """保存对话检查点"""
        # 实现保存逻辑...
    
    def get_checkpoint(self, checkpoint_id: str) -> Optional[ConversationCheckpoint]:
        """获取指定ID的对话检查点"""
        # 实现获取逻辑...
    
    def get_latest_checkpoint(self) -> Optional[ConversationCheckpoint]:
        """获取最新的对话检查点"""
        # 实现获取最新检查点逻辑...
    
    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """删除指定的对话检查点"""
        # 实现删除逻辑...
```

### 3.3 FileChangeManager 扩展

扩展现有的 `FileChangeManager` 类，增加对话检查点的管理功能：

```python
class FileChangeManager:
    # 现有代码...
    
    def __init__(self, project_dir: str, backup_dir: Optional[str] = None, 
                 store_dir: Optional[str] = None, max_history: int = 50,
                 conversation_store_dir: Optional[str] = None):
        """
        初始化文件变更管理器
        
        Args:
            # 现有参数...
            conversation_store_dir: 对话检查点存储目录
        """
        # 现有初始化代码...
        self.conversation_store = ConversationCheckpointStore(conversation_store_dir, max_history)
    
    def apply_changes_with_conversation(self, changes: Dict[str, FileChange], 
                                       conversations: List[Dict[str, Any]],
                                       change_group_id: Optional[str] = None,
                                       metadata: Optional[Dict[str, Any]] = None) -> ApplyResult:
        """
        应用文件变更并保存对话状态
        
        Args:
            changes: 文件变更字典
            conversations: 当前对话历史
            change_group_id: 变更组ID
            metadata: 元数据
            
        Returns:
            ApplyResult: 应用结果对象
        """
        # 应用文件变更
        result = self.apply_changes(changes, change_group_id)
        
        if result.success:
            # 创建并保存对话检查点
            checkpoint = ConversationCheckpoint(
                checkpoint_id=change_group_id or result.change_ids[0],
                timestamp=time.time(),
                conversations=conversations,
                metadata=metadata
            )
            self.conversation_store.save_checkpoint(checkpoint)
        
        return result
    
    def undo_change_with_conversation(self, change_id: str) -> Tuple[UndoResult, Optional[ConversationCheckpoint]]:
        """
        撤销指定的变更并恢复对话状态
        
        Args:
            change_id: 变更记录ID
            
        Returns:
            Tuple[UndoResult, Optional[ConversationCheckpoint]]: 撤销结果和恢复的对话检查点
        """
        # 获取变更记录
        change_record = self.change_store.get_change(change_id)
        if change_record is None:
            return UndoResult(success=False, errors={"general": f"变更记录 {change_id} 不存在"}), None
        
        # 获取关联的对话检查点
        checkpoint_id = change_record.group_id or change_id
        checkpoint = self.conversation_store.get_checkpoint(checkpoint_id)
        
        # 撤销文件变更
        undo_result = self.undo_change(change_id)
        
        return undo_result, checkpoint
    
    # 类似地扩展其他撤销方法...
```

### 3.5 工具解析器修改

修改 `ReplaceInFileToolResolver` 和 `WriteToFileToolResolver` 类，使其在调用 `apply_changes` 后立即调用 `apply_changes_with_conversation` 方法来保存对话状态：

```python
class ReplaceInFileToolResolver(BaseToolResolver):
    # 现有代码...
    
    def resolve(self) -> ToolResult:
        # 现有代码...
        
        # 现有的文件变更记录逻辑
        if self.agent and self.agent.checkpoint_manager:
            changes = {
                file_path: CheckpointFileChange(
                    file_path=file_path,
                    content=current_content,
                    is_deletion=False,
                    is_new=True
                )
            }
            change_group_id = self.args.event_file
            
            # 首先应用文件变更
            self.agent.checkpoint_manager.apply_changes(changes, change_group_id)
            
            # 然后保存对话状态
            self.agent.checkpoint_manager.apply_changes_with_conversation(
                changes=changes,
                conversations=self.agent.current_conversations,
                change_group_id=change_group_id,
                metadata={"event_file": self.args.event_file}
            )
        
        # 变更跟踪，回调AgenticEdit
        if self.agent:
            rel_path = os.path.relpath(abs_file_path, abs_project_dir)
            self.agent.record_file_change(rel_path, "modified", diff=diff_content, content=current_content)
        
        # 其余代码...
```

```python
class WriteToFileToolResolver(BaseToolResolver):
    # 现有代码...
    
    def resolve(self) -> ToolResult:
        # 现有代码...
        
        # 现有的文件变更记录逻辑
        if self.agent and self.agent.checkpoint_manager:
            changes = {
                file_path: CheckpointFileChange(
                    file_path=file_path,
                    content=content,
                    is_deletion=False,
                    is_new=True
                )
            }
            change_group_id = self.args.event_file
            
            # 首先应用文件变更
            self.agent.checkpoint_manager.apply_changes(changes, change_group_id)
            
            # 然后保存对话状态
            self.agent.checkpoint_manager.apply_changes_with_conversation(
                changes=changes,
                conversations=self.agent.current_conversations,
                change_group_id=change_group_id,
                metadata={"event_file": self.args.event_file}
            )
        
        # 变更跟踪，回调AgenticEdit
        if self.agent:
            rel_path = os.path.relpath(abs_file_path, abs_project_dir)
            self.agent.record_file_change(rel_path, "added", diff=None, content=content)
        
        # 其余代码...
```

## 4. 用户界面设计

为了让用户能够方便地使用对话回滚功能，需要设计相应的命令或界面：

### 4.1 命令行接口

```python
# 在AgenticEdit类中添加命令处理方法
def handle_rollback_command(self, command: str) -> str:
    """
    处理回滚相关的命令
    
    Args:
        command: 命令字符串，如 "rollback list", "rollback to <id>", "rollback info <id>"
        
    Returns:
        str: 命令执行结果
    """
    if command == "rollback list":
        # 列出可用的检查点
        checkpoints = self.get_available_checkpoints()
        if not checkpoints:
            return "没有可用的检查点。"
        
        result = "可用的检查点列表：\n"
        for i, cp in enumerate(checkpoints):
            time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(cp["timestamp"]))
            result += f"{i+1}. ID: {cp['id'][:8]}... | 时间: {time_str} | 变更文件数: {cp['changes_count']}"
            result += f" | {'包含对话状态' if cp['has_conversation'] else '不包含对话状态'}\n"
        
        return result
    
    elif command.startswith("rollback info "):
        # 显示检查点详情
        cp_id = command[len("rollback info "):].strip()
        
        # 查找检查点
        checkpoints = self.get_available_checkpoints()
        target_cp = None
        
        # 支持通过序号或ID查询
        if cp_id.isdigit() and 1 <= int(cp_id) <= len(checkpoints):
            target_cp = checkpoints[int(cp_id) - 1]
        else:
            for cp in checkpoints:
                if cp["id"].startswith(cp_id):
                    target_cp = cp
                    break
        
        if not target_cp:
            return f"未找到ID为 {cp_id} 的检查点。"
        
        # 获取检查点详细信息
        time_str = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(target_cp["timestamp"]))
        
        # 获取变更文件列表
        changes = self.checkpoint_manager.get_changes_by_group(target_cp["id"])
        changed_files = [change.file_path for change in changes]
        
        # 获取对话状态信息
        conversation_info = "无对话状态信息"
        if target_cp["has_conversation"] and hasattr(self.checkpoint_manager, 'conversation_store'):
            checkpoint = self.checkpoint_manager.conversation_store.get_checkpoint(target_cp["id"])
            if checkpoint and checkpoint.conversations:
                conversation_info = f"包含 {len(checkpoint.conversations)} 条对话消息"
        
        result = f"检查点详情：\n"
        result += f"ID: {target_cp['id']}\n"
        result += f"创建时间: {time_str}\n"
        result += f"变更文件数: {target_cp['changes_count']}\n"
        result += f"对话状态: {conversation_info}\n\n"
        
        if changed_files:
            result += "变更文件列表：\n"
            for i, file_path in enumerate(changed_files):
                result += f"{i+1}. {file_path}\n"
        
        return result
    
    elif command.startswith("rollback to "):
        # 回滚到指定检查点
        cp_id = command[len("rollback to "):].strip()
        
        # 查找检查点
        checkpoints = self.get_available_checkpoints()
        target_cp = None
        
        # 支持通过序号或ID回滚
        if cp_id.isdigit() and 1 <= int(cp_id) <= len(checkpoints):
            target_cp = checkpoints[int(cp_id) - 1]
        else:
            for cp in checkpoints:
                if cp["id"].startswith(cp_id):
                    target_cp = cp
                    break
        
        if not target_cp:
            return f"未找到ID为 {cp_id} 的检查点。"
        
        # 执行回滚
        success = self.rollback_to_checkpoint(target_cp["id"])
        
        if success:
            # 获取变更文件列表
            changes = self.checkpoint_manager.get_changes_by_group(target_cp["id"])
            changed_files = [change.file_path for change in changes]
            
            result = f"成功回滚到检查点 {target_cp['id'][:8]}...\n"
            result += f"恢复了 {len(changed_files)} 个文件的状态"
            
            if target_cp["has_conversation"]:
                result += f"\n同时恢复了对话状态"
            
            return result
        else:
            return f"回滚到检查点 {target_cp['id'][:8]}... 失败。"
    
    return "未知命令。可用命令：rollback list, rollback info <id>, rollback to <id>"
```

### 4.2 图形界面设计

如果系统有图形界面，可以添加以下功能来支持对话回滚：

#### 4.2.1 检查点列表视图

在主界面添加一个“历史检查点”按钮，点击后显示检查点列表视图：

```
+------------------------------------------+
|            历史检查点列表            |
+------------------------------------------+
| 序号 | 时间              | 文件数 | 状态     |
+------------------------------------------+
| 1    | 2025-05-10 14:30:25 | 3      | 包含对话   |
| 2    | 2025-05-10 14:45:18 | 1      | 包含对话   |
| 3    | 2025-05-10 15:10:02 | 5      | 包含对话   |
+------------------------------------------+
|  [详情]  [回滚]  [对比]  [关闭]  |
+------------------------------------------+
```

#### 4.2.2 检查点详情视图

点击“详情”按钮后，显示检查点的详细信息：

```
+------------------------------------------+
|            检查点详细信息            |
+------------------------------------------+
| ID: 7a8b9c0d-1e2f-3g4h-5i6j-7k8l9m0n1o2p |
| 创建时间: 2025-05-10 14:30:25       |
| 变更文件数: 3                    |
| 对话状态: 包含 12 条对话消息      |
+------------------------------------------+
| 变更文件列表:                      |
| 1. src/models/user.py                  |
| 2. src/controllers/auth.py             |
| 3. tests/test_auth.py                  |
+------------------------------------------+
| 对话内容预览:                        |
| User: 添加用户认证功能              |
| Assistant: 我将实现用户认证功能...   |
+------------------------------------------+
|  [回滚]  [对比]  [返回]  [关闭]  |
+------------------------------------------+
```

#### 4.2.3 文件对比视图

点击“对比”按钮后，显示检查点与当前状态的文件对比：

```
+------------------------------------------+
|              文件对比视图              |
+------------------------------------------+
| 文件: src/models/user.py                |
+------------------------------------------+
| 检查点版本                | 当前版本        |
+------------------------------------------+
| class User:             | class User:         |
|   def __init__(self,    |   def __init__(self,|
|     name,               |     name,           |
|     email               |     email,          |
|   ):                    |     password        |
|     self.name = name    |   ):                |
|     self.email = email  |     self.name = name|
|                         |     self.email = ...|
+------------------------------------------+
|  [上一个文件]  [下一个文件]  [返回]  |
+------------------------------------------+
```

#### 4.2.4 回滚确认对话框

点击“回滚”按钮后，显示确认对话框：

```
+------------------------------------------+
|              回滚确认              |
+------------------------------------------+
| 您确定要回滚到以下检查点吗？        |
| 创建时间: 2025-05-10 14:30:25       |
| 变更文件数: 3                    |
|                                        |
| 此操作将恢复所有文件到检查点状态，  |
| 并恢复对话历史。                  |
| 此操作不可撤销！                    |
+------------------------------------------+
|    [确认回滚]    [取消]    |
+------------------------------------------+
```

#### 4.2.5 集成到主界面

在主界面的工具栏或菜单中添加“历史检查点”按钮，并在状态栏显示当前检查点信息：

```
+------------------------------------------+
| 文件 | 编辑 | 视图 | 工具 | 帮助       |
+------------------------------------------+
|                                        |
|              代码编辑区域              |
|                                        |
+------------------------------------------+
| 状态: 当前检查点 #3 (2025-05-10 15:10) |
+------------------------------------------+
```

### 4.3 快捷命令集成

在编辑器的命令面板中添加快捷命令，支持直接调用回滚相关功能：

1. `Ctrl+Shift+H`: 显示历史检查点列表
2. `Ctrl+Shift+R`: 快速回滚到上一个检查点
3. `Ctrl+Shift+C`: 对比当前文件与上一个检查点版本
```

## 5. 存储设计

### 5.1 文件结构

对话检查点将存储在项目目录下的 `.auto-coder/conversation_checkpoints` 目录中，每个检查点保存为一个独立的 JSON 文件：

```
.auto-coder/
  ├── checkpoint/               # 现有的文件备份目录
  ├── checkpoint_store/         # 现有的变更记录存储目录
  └── conversation_checkpoints/ # 新增的对话检查点存储目录
      ├── <checkpoint_id_1>.json
      ├── <checkpoint_id_2>.json
      └── ...
```

### 5.2 检查点文件格式

```json
{
  "checkpoint_id": "uuid-or-event-file-id",
  "timestamp": 1620000000.0,
  "conversations": [
    {
      "role": "user",
      "content": "用户消息内容"
    },
    {
      "role": "assistant",
      "content": "助手回复内容"
    },
    // 更多对话消息...
  ],
  "metadata": {
    "event_file": "event-file-id",
    "additional_info": "其他信息"
  }
}
```

## 6. 实现步骤

1. 创建 `ConversationCheckpoint` 和 `ConversationCheckpointStore` 类
2. 扩展 `FileChangeManager` 类，添加对话检查点管理功能
3. 修改 `AgenticEdit` 类，增加对话回滚相关方法
4. 更新 `ReplaceInFileToolResolver` 和 `WriteToFileToolResolver` 类，使用新的记录方法
5. 实现命令行接口和/或图形界面集成
6. 添加单元测试和集成测试
7. 更新文档

## 7. 兼容性考虑

1. 对于已有的变更记录，可能没有对应的对话检查点，需要处理这种情况
2. 确保新功能不影响现有的文件变更管理功能
3. 考虑对话历史可能很大，需要进行适当的压缩或裁剪

## 8. 测试计划

1. 单元测试：测试各个类和方法的功能
2. 集成测试：测试整个回滚流程
3. 边缘情况测试：
   - 没有对话历史的回滚
   - 对话历史很大的情况
   - 回滚后继续编辑
   - 多次回滚

## 9. 未来扩展

1. 增加对话历史的差异比较功能
2. 支持部分回滚（只回滚特定文件或特定对话）
3. 支持对话历史的编辑和修改
4. 添加对话检查点的标签和描述
