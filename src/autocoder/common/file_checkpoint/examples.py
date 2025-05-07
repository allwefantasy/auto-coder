"""
文件变更管理模块的使用示例

展示如何使用文件变更管理模块进行文件变更的应用和撤销。
"""

import os
import sys
import json
from typing import Dict, Any

from autocoder.common.file_checkpoint.models import FileChange
from autocoder.common.file_checkpoint.manager import FileChangeManager


def example_apply_changes(project_dir: str):
    """
    示例：应用文件变更
    
    Args:
        project_dir: 项目目录
    """
    print(f"示例：应用文件变更到项目 {project_dir}")
    
    # 创建文件变更管理器
    manager = FileChangeManager(project_dir)
    
    # 准备文件变更
    changes = {
        "example.txt": FileChange(
            file_path="example.txt",
            content="这是一个示例文件\n用于演示文件变更管理模块的功能\n",
            is_new=True
        ),
        "README.md": FileChange(
            file_path="README.md",
            content="# 示例项目\n\n这是一个用于演示文件变更管理模块的示例项目。\n",
            is_new=True
        )
    }
    
    # 应用变更
    result = manager.apply_changes(changes)
    
    # 输出结果
    if result.success:
        print(f"成功应用了 {len(result.change_ids)} 个文件变更")
        for change_id in result.change_ids:
            print(f"  - 变更ID: {change_id}")
    else:
        print("应用变更失败")
        for file_path, error in result.errors.items():
            print(f"  - {file_path}: {error}")


def example_preview_changes(project_dir: str):
    """
    示例：预览文件变更
    
    Args:
        project_dir: 项目目录
    """
    print(f"示例：预览文件变更")
    
    # 创建文件变更管理器
    manager = FileChangeManager(project_dir)
    
    # 准备文件变更
    changes = {
        "example.txt": FileChange(
            file_path="example.txt",
            content="这是一个修改后的示例文件\n用于演示文件变更管理模块的功能\n新增的一行\n",
            is_new=False
        )
    }
    
    # 预览变更
    diff_results = manager.preview_changes(changes)
    
    # 输出差异
    for file_path, diff_result in diff_results.items():
        print(f"\n文件: {file_path}")
        print(diff_result.get_diff_summary())
        if diff_result.old_content is not None and not diff_result.is_new and not diff_result.is_deletion:
            diff_text = manager.get_diff_text(diff_result.old_content, diff_result.new_content)
            print("\n差异:")
            print(diff_text)


def example_undo_changes(project_dir: str):
    """
    示例：撤销文件变更
    
    Args:
        project_dir: 项目目录
    """
    print(f"示例：撤销文件变更")
    
    # 创建文件变更管理器
    manager = FileChangeManager(project_dir)
    
    # 撤销最近的变更
    result = manager.undo_last_change()
    
    # 输出结果
    if result.success:
        print(f"成功撤销了变更，恢复了 {len(result.restored_files)} 个文件")
        for file_path in result.restored_files:
            print(f"  - {file_path}")
    else:
        print("撤销变更失败")
        for file_path, error in result.errors.items():
            print(f"  - {file_path}: {error}")


def example_get_history(project_dir: str):
    """
    示例：获取变更历史
    
    Args:
        project_dir: 项目目录
    """
    print(f"示例：获取变更历史")
    
    # 创建文件变更管理器
    manager = FileChangeManager(project_dir)
    
    # 获取变更历史
    changes = manager.get_change_history(limit=5)
    
    # 输出历史记录
    print(f"最近 {len(changes)} 条变更记录:")
    for change in changes:
        timestamp = change.timestamp
        file_path = change.file_path
        change_type = "新建" if change.is_new else "删除" if change.is_deletion else "修改"
        print(f"  - [{timestamp}] {change_type} {file_path} (ID: {change.change_id})")


def example_integration_with_agentic_edit():
    """
    示例：与 AgenticEdit 集成
    
    展示如何将文件变更管理模块集成到 AgenticEdit 中
    """
    print("示例：与 AgenticEdit 集成")
    
    # 这是一个伪代码示例，展示如何修改 AgenticEdit.apply_changes 方法
    code = """
def apply_changes(self):
    \"\"\"
    Apply all tracked file changes to the original project directory.
    \"\"\"
    from autocoder.common.file_checkpoint.models import FileChange
    from autocoder.common.file_checkpoint.manager import FileChangeManager
    
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
        error_messages = "\\n".join([f"{path}: {error}" for path, error in result.errors.items()])
        self.printer.print_str_in_terminal(
            f"Failed to apply changes:\\n{error_messages}",
            style="red"
        )
    """
    
    print(code)


def main():
    """主函数"""
    if len(sys.argv) < 2:
        print("用法: python examples.py <项目目录>")
        return
    
    project_dir = sys.argv[1]
    
    # 运行示例
    example_apply_changes(project_dir)
    print("\n" + "-" * 50 + "\n")
    
    example_preview_changes(project_dir)
    print("\n" + "-" * 50 + "\n")
    
    example_get_history(project_dir)
    print("\n" + "-" * 50 + "\n")
    
    example_undo_changes(project_dir)
    print("\n" + "-" * 50 + "\n")
    
    example_integration_with_agentic_edit()


if __name__ == "__main__":
    main()
