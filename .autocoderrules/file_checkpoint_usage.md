
# File Checkpoint 使用方法

## 简要说明
本文档介绍了如何在项目中使用 `FileChangeManager`（文件变更管理模块），以实现对文件变更的追踪、应用、预览和撤销功能。这对于需要精细控制文件修改过程的场景非常有用，例如在自动化代码生成或重构任务中。

## 基本用法

`FileChangeManager` 是核心类，用于管理项目目录中的文件变更。

```python
from autocoder.common.file_checkpoint.manager import FileChangeManager
from autocoder.common.file_checkpoint.models import FileChange

# 初始化 FileChangeManager，需要提供项目根目录
project_directory = "/path/to/your/project"
manager = FileChangeManager(project_dir=project_directory)
```

## 主要功能

### 1. 应用文件变更 (`apply_changes`)

此功能用于将一组定义好的文件变更实际应用到项目文件中。变更可以是创建新文件、修改现有文件或删除文件（通过特定的标记）。

```python
# 准备文件变更
# FileChange 对象包含文件路径、新内容以及是否为新文件的标记
changes_to_apply = {
    "src/new_module.py": FileChange(
        file_path="src/new_module.py",
        content="print('Hello, new module!')\n",
        is_new=True  # 标记为新文件
    ),
    "README.md": FileChange(
        file_path="README.md",
        content="# Project Title\nUpdated README content.\n",
        is_new=False # 标记为修改现有文件
    )
}

# 应用变更
apply_result = manager.apply_changes(changes_to_apply)

if apply_result.success:
    print(f"成功应用了 {len(apply_result.change_ids)} 个文件变更:")
    for change_id in apply_result.change_ids:
        print(f"  - 变更ID: {change_id}")
else:
    print("应用变更失败:")
    for file_path, error_message in apply_result.errors.items():
        print(f"  - {file_path}: {error_message}")
```
**注意**: `apply_changes` 会将变更记录到历史中，以便后续可以撤销。

### 2. 预览文件变更 (`preview_changes`)

在实际应用变更之前，可以预览这些变更与当前文件内容的差异。

```python
# 准备要预览的变更
changes_to_preview = {
    "src/existing_file.py": FileChange(
        file_path="src/existing_file.py",
        content="def updated_function():\n    return 'new logic'\n",
        is_new=False
    )
}

# 预览变更
diff_results = manager.preview_changes(changes_to_preview)

for file_path, diff_info in diff_results.items():
    print(f"\n文件预览: {file_path}")
    print(diff_info.get_diff_summary()) # 获取差异摘要，例如 "+2 lines, -1 line"
    
    # 如果文件存在且不是新创建或删除，可以获取详细的文本差异
    if diff_info.old_content is not None and not diff_info.is_new and not diff_info.is_deletion:
        # get_diff_text 方法需要自行实现或使用类似 difflib 的库
        # 以下为示例，实际 manager 中可能包含此方法
        # diff_text = manager.get_diff_text(diff_info.old_content, diff_info.new_content)
        # print("\n详细差异:")
        # print(diff_text)
        # 假设 FileChangeManager 提供了 get_diff_text 方法
        if hasattr(manager, 'get_diff_text'):
            diff_text = manager.get_diff_text(diff_info.old_content, diff_info.new_content)
            print("\n详细差异:")
            print(diff_text)
        else:
            print("(详细文本差异的生成需要 get_diff_text 方法)")

```

### 3. 撤销文件变更 (`undo_last_change`)

此功能允许撤销最近一次通过 `apply_changes` 应用的变更。

```python
# 撤销最近一次的变更
undo_result = manager.undo_last_change()

if undo_result.success:
    print(f"成功撤销变更，恢复了 {len(undo_result.restored_files)} 个文件:")
    for restored_file_path in undo_result.restored_files:
        print(f"  - {restored_file_path}")
else:
    print("撤销变更失败:")
    if undo_result.errors:
        for file_path, error_message in undo_result.errors.items():
            print(f"  - {file_path}: {error_message}")
    else:
        print("  没有可撤销的变更，或撤销过程中发生未知错误。")

```
**注意**: `undo_last_change` 会从历史记录中移除被撤销的变更，并将文件恢复到变更前的状态。

### 4. 获取变更历史 (`get_change_history`)

可以获取项目的文件变更历史记录。

```python
# 获取最近的5条变更历史
change_history = manager.get_change_history(limit=5)

print(f"最近 {len(change_history)} 条变更记录:")
for record in change_history:
    timestamp = record.timestamp
    file_path = record.file_path
    # 根据 is_new, is_deletion (假设存在) 判断变更类型
    change_type_str = "新建" if record.is_new else "删除" if getattr(record, 'is_deletion', False) else "修改"
    print(f"  - [{timestamp}] {change_type_str} {file_path} (ID: {record.change_id})")
```

## 与 AgenticEdit 集成

`FileChangeManager` 可以集成到像 `AgenticEdit` 这样的工具中，以提供更稳健的文件操作和版本控制能力。当 `AgenticEdit` 在影子系统中计算出文件变更后，可以使用 `FileChangeManager` 来应用这些变更到实际项目目录，并自动记录变更历史。

以下是一个概念性的集成示例，展示如何在 `AgenticEdit` 的 `apply_changes` 方法中使用 `FileChangeManager`：

```python
# 伪代码示例：修改 AgenticEdit.apply_changes 方法
# class AgenticEdit:
#     def __init__(self, source_dir, args):
#         self.args = args
#         self.args.source_dir = source_dir # 确保 source_dir 可用
#         # ... 其他初始化 ...

#     def get_all_file_changes(self) -> Dict[str, Any]: # 假设返回字典 {file_path: change_object_with_content}
#         # ... 实现获取影子系统变更的逻辑 ...
#         # 返回示例: {"file1.py": {"content": "new content for file1"}}
#         pass

#     def apply_changes_with_checkpoint(self): # 新的方法名以区分
#         from autocoder.common.file_checkpoint.models import FileChange
#         from autocoder.common.file_checkpoint.manager import FileChangeManager
#         import os # 需要 os 模块

#         # 创建文件变更管理器
#         manager = FileChangeManager(self.args.source_dir)

#         # 将影子系统的变更转换为 FileChange 对象
#         changes_for_checkpoint = {}
#         # 假设 self.get_all_file_changes() 返回 { "path/to/file": ShadowFileChange }
#         # ShadowFileChange 有 content 属性
#         all_shadow_changes = self.get_all_file_changes() # 获取所有变更

#         for file_path_in_project, shadow_change in all_shadow_changes.items():
#             # 确定文件的完整路径
#             full_file_path_original = os.path.join(self.args.source_dir, file_path_in_project)
            
#             changes_for_checkpoint[file_path_in_project] = FileChange(
#                 file_path=file_path_in_project, # 相对于项目目录的路径
#                 content=shadow_change.content, # 假设 shadow_change 对象有 content 属性
#                 is_new=not os.path.exists(full_file_path_original) # 判断是否为新文件
#             )

#         # 应用变更
#         result = manager.apply_changes(changes_for_checkpoint)

#         # 处理结果
#         if result.success:
#             print("文件变更已通过 FileChangeManager成功应用。")
#             # 可以继续执行原有的 Git 提交等逻辑
#             # if not self.args.skip_commit:
#             #     try:
#             #         # ... 原有的 Git 提交代码 ...
#             #     except Exception as e:
#             #         # ... 原有的错误处理 ...
#         else:
#             # 处理应用变更失败的情况
#             error_messages = "\n".join([f"{path}: {error}" for path, error in result.errors.items()])
#             # self.printer.print_str_in_terminal(
#             #     f"Failed to apply changes via FileChangeManager:\n{error_messages}",
#             #     style="red"
#             # )
#             print(f"通过 FileChangeManager 应用变更失败:\n{error_messages}")

```

## 实际示例代码

以下代码片段来自 `src/autocoder/common/file_checkpoint/examples.py`，展示了上述功能的实际应用：

### 应用变更示例
```python
from autocoder.common.file_checkpoint.models import FileChange
from autocoder.common.file_checkpoint.manager import FileChangeManager

def example_apply_changes(project_dir: str):
    manager = FileChangeManager(project_dir)
    changes = {
        "example.txt": FileChange(
            file_path="example.txt",
            content="这是一个示例文件\n用于演示文件变更管理模块的功能\n",
            is_new=True
        )
    }
    result = manager.apply_changes(changes)
    if result.success:
        print(f"成功应用了 {len(result.change_ids)} 个文件变更")
    else:
        print("应用变更失败")
```

### 预览变更示例
```python
def example_preview_changes(project_dir: str):
    manager = FileChangeManager(project_dir)
    changes = {
        "example.txt": FileChange(
            file_path="example.txt",
            content="这是一个修改后的示例文件\n用于演示文件变更管理模块的功能\n新增的一行\n",
            is_new=False # 假设 example.txt 已存在
        )
    }
    diff_results = manager.preview_changes(changes)
    for file_path, diff_result in diff_results.items():
        print(f"\n文件: {file_path}")
        print(diff_result.get_diff_summary())
        if hasattr(manager, 'get_diff_text') and diff_result.old_content is not None and \
           not diff_result.is_new and not diff_result.is_deletion:
            diff_text = manager.get_diff_text(diff_result.old_content, diff_result.new_content)
            print("\n差异:")
            print(diff_text)
```

### 撤销变更示例
```python
def example_undo_changes(project_dir: str):
    manager = FileChangeManager(project_dir)
    result = manager.undo_last_change()
    if result.success:
        print(f"成功撤销了变更，恢复了 {len(result.restored_files)} 个文件")
    else:
        print("撤销变更失败")
```

### 获取历史示例
```python
def example_get_history(project_dir: str):
    manager = FileChangeManager(project_dir)
    changes = manager.get_change_history(limit=5)
    print(f"最近 {len(changes)} 条变更记录:")
    for change in changes:
        timestamp = change.timestamp
        file_path = change.file_path
        change_type = "新建" if change.is_new else "删除" if getattr(change, 'is_deletion', False) else "修改"
        print(f"  - [{timestamp}] {change_type} {file_path} (ID: {change.change_id})")
```

通过这些功能，`FileChangeManager` 提供了一个强大的机制来管理和控制项目中的文件修改。
