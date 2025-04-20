---
description: Git提交变更获取工具
globs: ["src/utils/git_analyzer.py", "src/tools/git_tools.py"]
alwaysApply: false
---

# 获取 Git 提交的文件变更内容

## 简要说明
提供一个函数，使用 GitPython 获取指定 Git commit ID 的详细文件变更内容（变更前、变更后），支持首次提交和普通提交。适用于代码分析、版本比较、审计和报告生成。

## 典型用法
```python
import git
from typing import Dict, Tuple, Optional

def get_commit_changes(repo_path: str, commit_id: str) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
    '''
    获取指定commit的文件变更内容

    Args:
        repo_path: Git仓库路径
        commit_id: 提交ID (可以是 commit hash, tag, branch name, HEAD, etc.)

    Returns:
        Dict[str, Tuple[Optional[str], Optional[str]]]: 文件路径到(变更前内容, 变更后内容)的映射。
                                                         对于新增文件，变更前内容为 None。
                                                         对于删除文件，变更后内容为 None。
                                                         返回空字典如果发生错误。
    '''
    changes: Dict[str, Tuple[Optional[str], Optional[str]]] = {}
    try:
        repo = git.Repo(repo_path, search_parent_directories=True) # search_parent_directories is useful
        commit = repo.commit(commit_id)

        # 检查是否是首次提交（没有父提交）
        if not commit.parents:
            # 首次提交，获取所有文件
            for item in commit.tree.traverse():
                if item.type == 'blob':  # 只处理文件，不处理目录
                    file_path = item.path
                    before_content: Optional[str] = None # 首次提交前没有内容
                    after_content: Optional[str] = None
                    try:
                        # Try decoding with utf-8 first
                        after_content = item.data_stream.read().decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                           # Fallback: read as bytes and let caller handle or try other encodings
                           # Or use git show which might handle encoding better sometimes
                           after_content = repo.git.show(f"{commit.hexsha}:{file_path}")
                        except Exception as e_show:
                           print(f"Warning: Could not decode/read content for {file_path} in initial commit {commit_id}: {e_show}")
                           after_content = f"Error reading content: {e_show}" # Mark as error
                    except Exception as e_read:
                        print(f"Warning: Could not read blob data for {file_path} in initial commit {commit_id}: {e_read}")
                        after_content = f"Error reading blob: {e_read}" # Mark as error

                    changes[file_path] = (before_content, after_content)
        else:
            # 获取parent commit (通常只有一个, 但处理多个以防万一, 这里简化取第一个)
            parent = commit.parents[0]
            # 获取变更的文件列表 (Diff)
            # create_patch=False is generally faster if you only need content, not the diff text
            diff_index = parent.diff(commit, create_patch=False)

            for diff_item in diff_index:
                # Determine the file path (handles renames, though content might be complex)
                # For simplicity, we use b_path if available (after change), else a_path (before change)
                file_path = diff_item.b_path if diff_item.b_path else diff_item.a_path
                if file_path is None: # Should not happen with standard diffs, but safety check
                    continue

                before_content: Optional[str] = None
                after_content: Optional[str] = None

                # 获取变更前内容 (if not a new file 'A')
                if diff_item.change_type != 'A' and diff_item.a_blob:
                    try:
                        before_content = diff_item.a_blob.data_stream.read().decode('utf-8')
                    except UnicodeDecodeError:
                         try:
                            before_content = repo.git.show(f"{parent.hexsha}:{diff_item.a_path}")
                         except Exception as e_show_before:
                             print(f"Warning: Could not decode/read 'before' content for {file_path} (commit {parent.hexsha}): {e_show_before}")
                             before_content = f"Error reading 'before' content: {e_show_before}"
                    except Exception as e_read_before:
                        print(f"Warning: Could not read 'before' blob data for {file_path} (commit {parent.hexsha}): {e_read_before}")
                        before_content = f"Error reading 'before' blob: {e_read_before}"


                # 获取变更后内容 (if not a deleted file 'D')
                if diff_item.change_type != 'D' and diff_item.b_blob:
                    try:
                        after_content = diff_item.b_blob.data_stream.read().decode('utf-8')
                    except UnicodeDecodeError:
                        try:
                            after_content = repo.git.show(f"{commit.hexsha}:{diff_item.b_path}")
                        except Exception as e_show_after:
                            print(f"Warning: Could not decode/read 'after' content for {file_path} (commit {commit.hexsha}): {e_show_after}")
                            after_content = f"Error reading 'after' content: {e_show_after}"
                    except Exception as e_read_after:
                        print(f"Warning: Could not read 'after' blob data for {file_path} (commit {commit.hexsha}): {e_read_after}")
                        after_content = f"Error reading 'after' blob: {e_read_after}"

                changes[file_path] = (before_content, after_content)

        return changes
    except git.exc.InvalidGitRepositoryError:
        print(f"Error: '{repo_path}' is not a valid Git repository or search upward failed.")
        return {}
    except git.exc.BadName as e:
        print(f"Error: Invalid commit ID or reference '{commit_id}': {e}")
        return {}
    except IndexError:
         print(f"Error: Commit '{commit_id}' seems to have no parents (initial commit?) but wasn't handled as such.")
         return {}
    except Exception as e:
        # Catch other potential GitPython or general errors
        print(f"An unexpected error occurred while getting commit changes for '{commit_id}': {str(e)}")
        return {}

# --- 示例调用 ---
if __name__ == '__main__':
    # 使用当前脚本所在的 Git 仓库
    repo_directory = "."
    # 获取最近一次提交的变更
    target_commit_id = "HEAD"

    print(f"Analyzing commit: {target_commit_id} in repository: {repo_directory}")
    commit_diffs = get_commit_changes(repo_directory, target_commit_id)

    if commit_diffs:
        print(f"\nFound {len(commit_diffs)} changed files in commit {target_commit_id}:")
        for file, (before, after) in commit_diffs.items():
            print(f"\n--- File: {file} ---")
            change_type = "Modified"
            if before is None and after is not None:
                change_type = "Added"
            elif before is not None and after is None:
                change_type = "Deleted"
            elif before == after: # Should not happen with diff but safety check
                change_type = "Unchanged?"

            print(f"  Type: {change_type}")

            # Optionally print snippets of content
            # if before:
            #     print("  Content Before (snippet):\n", before[:150] + ("..." if before and len(before) > 150 else ""))
            # if after:
            #     print("  Content After (snippet):\n", after[:150] + ("..." if after and len(after) > 150 else ""))
    else:
        print(f"No changes found or an error occurred while analyzing commit {target_commit_id}.")

    # 示例：分析特定 commit hash (替换成你仓库中的有效 hash)
    # specific_commit = "YOUR_COMMIT_HASH_HERE"
    # print(f"\nAnalyzing specific commit: {specific_commit}")
    # specific_diffs = get_commit_changes(repo_directory, specific_commit)
    # ... (处理 specific_diffs) ...
```

## 依赖说明
- **GitPython**: `>=3.1.0` (用于与 Git 仓库交互)
  ```bash
  pip install GitPython
  ```
- **Python**: `>=3.7` (建议)
- **Git**: 需要在系统环境中安装并配置好 Git 命令行工具。

## 学习来源
从 `src/autocoder/agent/auto_learn.py` 中的 `get_commit_changes` 方法提取 (基于 Commit: auto_coder_000000002528)。进行了一些健壮性改进（如错误处理、编码回退）。