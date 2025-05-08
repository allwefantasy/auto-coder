
---
description: 解释如何使用 FileChangeManager 模块进行文件变更的追踪、应用、预览和撤销。
globs:
  - "**/*.py"
alwaysApply: false
---

# FileChangeManager 使用指南

`FileChangeManager` 模块是 AutoCoder 项目中用于管理和追踪文件变更的核心组件。它提供了一套完整的机制来记录、应用、预览和撤销对文件的修改，确保在代码生成和重构过程中的可控性和可追溯性。

## 核心功能

1.  **变更追踪 (Tracking Changes)**:
    *   `FileChangeManager` 会记录所有通过其进行的写文件操作 (`write_file`) 或替换操作 (`replace_in_file`)。
    *   每次变更都会生成一个唯一的 `checkpoint_id`，并保存变更前后的文件状态快照。

2.  **应用变更 (Applying Changes)**:
    *   记录的变更可以被实际应用到文件系统，将修改持久化。

3.  **预览变更 (Previewing Changes)**:
    *   在实际应用变更前，可以预览将要发生的具体修改内容 (diff)。

4.  **撤销变更 (Reverting Changes)**:
    *   可以根据 `checkpoint_id` 将文件恢复到指定的变更点之前的状态。
    *   支持撤销到上一个检查点或任意指定的检查点。

## 主要使用场景

*   **安全的代码生成**: 在 LLM 生成代码后，先通过 `FileChangeManager` 记录变更，预览确认无误后再实际写入文件。
*   **迭代式重构**: 在进行多步重构时，每一步都可以创建一个检查点，方便回溯。
*   **风险控制**: 如果生成或修改的代码引入问题，可以快速恢复到稳定版本。
*   **调试与审计**: 追踪代码变更历史，帮助理解修改过程。

## 使用示例

以下是如何在代码中使用 `FileChangeManager` 的基本流程：

```python
from autocoder.common.file_checkpoint import FileChangeManager, FileOperation

# 1. 获取 FileChangeManager 实例 (通常是单例)
manager = FileChangeManager.get_instance(project_root="/path/to/your/project")

# 2. 准备文件操作
file_path = "src/example.py"
original_content = "print('Hello')"
new_content = "print('Hello, AutoCoder!')"

# 模拟读取文件原始内容 (在实际应用中，这通常是 manager 内部处理的)
# manager.add_original_file(file_path, original_content)

# 3. 执行写操作 (这会创建一个检查点)
# checkpoint_id_write = manager.write_file(file_path, new_content)
# print(f"Write operation checkpoint: {checkpoint_id_write}")

# 或者执行替换操作
search_pattern = "Hello"
replace_pattern = "Hello, AutoCoder!"
# diff_blocks = [f"<<<<<<< SEARCH\n{search_pattern}\n=======\n{replace_pattern}\n>>>>>>> REPLACE"]
# checkpoint_id_replace = manager.replace_in_file(file_path, "\n".join(diff_blocks))
# print(f"Replace operation checkpoint: {checkpoint_id_replace}")


# 4. 预览最近的变更
# preview = manager.preview_changes(checkpoint_id_replace)
# print(f"\nPreview of changes for {checkpoint_id_replace}:\n{preview}")

# 5. 应用所有待应用的变更到文件系统
# manager.apply_changes()
# print(f"\nChanges applied to {file_path}")

# with open(file_path, "r") as f:
#    print(f"Current content of {file_path}: {f.read()}")

# 6. 撤销到上一个检查点
# manager.revert_to_last_checkpoint()
# print(f"\nReverted to last checkpoint. Content of {file_path} should be original if only one change was made and applied.")
# manager.apply_changes() # Re-apply to see the revert effect if changes were already flushed
# with open(file_path, "r") as f:
#    print(f"Content after revert: {f.read()}")


# 7. 撤销到指定的检查点 (假设 checkpoint_id_write 是第一个检查点)
# 如果有多个操作，可以撤销到任意一个
# manager.revert_to_checkpoint(checkpoint_id_write) # This would revert the replace operation
# print(f"\nReverted to checkpoint {checkpoint_id_write}.")
# manager.apply_changes()
# with open(file_path, "r") as f:
#    print(f"Content after reverting to {checkpoint_id_write}: {f.read()}")

# 注意：示例中的 apply_changes() 和文件读取用于演示效果。
# FileChangeManager 通常在内部管理文件的虚拟状态，直到 apply_changes 被调用。
# 实际使用时，请参考 src/autocoder/common/file_checkpoint/examples.py 中的详细示例。
```

## 关键方法

*   `get_instance(project_root: str) -> FileChangeManager`: 获取 `FileChangeManager` 的单例。
*   `write_file(file_path: str, content: str) -> str`: 记录一个写文件操作，返回检查点 ID。
*   `replace_in_file(file_path: str, diff_content: str) -> str`: 记录一个替换文件内容的操作，返回检查点 ID。
*   `add_original_file(file_path: str, content: str)`: (主要供内部或测试使用) 添加文件的初始状态。
*   `preview_changes(checkpoint_id: str) -> str`: 预览指定检查点的变更。
*   `preview_all_changes() -> Dict[str, str]`: 预览所有待应用的变更。
*   `apply_changes()`: 将所有记录的变更应用到实际文件。
*   `revert_to_checkpoint(checkpoint_id: str)`: 撤销到指定的检查点。
*   `revert_to_last_checkpoint()`: 撤销最近一次的变更。
*   `get_file_content(file_path: str) -> Optional[str]`: 获取文件在当前检查点状态下的内容。

## 注意事项

*   `FileChangeManager` 依赖于项目根目录 (`project_root`) 来正确解析相对路径。
*   变更在调用 `apply_changes()`之前仅存在于内存中。
*   撤销操作也是基于内存中的检查点，如果变更已应用，撤销后需要再次调用 `apply_changes()` 来更新实际文件。
*   该模块是确保 AutoCoder 操作安全性和可控性的重要保障。

详细的实现和更复杂的使用场景可以参考 `src/autocoder/common/file_checkpoint/examples.py`。
