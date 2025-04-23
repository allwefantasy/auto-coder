
---
description: 使用 .autocoderignore 规则忽略文件/目录
globs: ["*/*.py"]
alwaysApply: false
---

# 使用 .autocoderignore 规则过滤文件和目录

## 简要说明
提供一种基于项目根目录或 `.auto-coder/` 目录下的 `.autocoderignore` 文件规则，来判断是否应忽略指定文件或目录的机制。这在处理项目文件时非常有用，可以避免处理版本控制目录、构建产物、虚拟环境等不需要的文件。

## 典型用法

**1. 创建 `.autocoderignore` 文件**

在项目根目录或 `.auto-coder/` 子目录下创建 `.autocoderignore` 文件，并添加忽略规则 (类似 `.gitignore` 语法)。

**示例 `.autocoderignore` 文件:**
```gitignore
# 忽略所有日志文件
*.log

# 忽略 target 目录下的所有内容
target/

# 不要忽略 target 目录下的重要文件
!target/important.txt

# 忽略特定的配置文件
config.dev.json

# 忽略 build 目录
build/

# 忽略所有 .tmp 文件
**/*.tmp
```

**2. 在 Python 代码中使用 `should_ignore` 函数**

```python
# 导入必要的函数和模块
from autocoder.common.ignorefiles.ignore_file_utils import should_ignore
import os

# 假设项目根目录是当前工作目录
project_root = os.getcwd() # 或者指定你的项目根目录

# --- 准备要检查的文件/目录路径 ---
# 注意: should_ignore 可以处理绝对路径和相对路径
# 这里使用绝对路径作为示例
log_file = os.path.join(project_root, "logs/app.log")
config_file = os.path.join(project_root, "config.dev.json")
source_file = os.path.join(project_root, "src/main.py")
node_module_dir = os.path.join(project_root, "node_modules/some_package")
target_output = os.path.join(project_root, "target/output.bin")
important_target = os.path.join(project_root, "target/important.txt")
git_dir = os.path.join(project_root, ".git/config") # 默认会被忽略

# --- 调用 should_ignore 进行检查 ---

print(f"检查: {log_file}")
if should_ignore(log_file):
    print("结果: 忽略 (匹配 *.log)")
else:
    print("结果: 不忽略")

print(f"\n检查: {config_file}")
if should_ignore(config_file):
    print("结果: 忽略 (匹配 config.dev.json)")
else:
    print("结果: 不忽略")

print(f"\n检查: {source_file}")
if should_ignore(source_file):
    print("结果: 忽略")
else:
    print("结果: 不忽略 (源码文件，未匹配规则)")

print(f"\n检查: {node_module_dir}")
if should_ignore(node_module_dir):
    print("结果: 忽略 (匹配默认规则 node_modules)")
else:
    print("结果: 不忽略")

print(f"\n检查: {target_output}")
if should_ignore(target_output):
     print("结果: 忽略 (匹配 target/)")
else:
    print("结果: 不忽略")

print(f"\n检查: {important_target}")
if should_ignore(important_target):
     print("结果: 忽略")
else:
    print("结果: 不忽略 (被 !target/important.txt 排除)")

print(f"\n检查: {git_dir}")
if should_ignore(git_dir):
     print("结果: 忽略 (匹配默认规则 .git)")
else:
    print("结果: 不忽略")

# --- 默认排除规则 ---
# 以下是默认包含的排除模式列表 (示例):
# ['.git', '.auto-coder', 'node_modules', '.mvn', '.idea',
#  '__pycache__', '.venv', 'venv', 'dist', 'build', '.gradle', '.next']
# .autocoderignore 文件中的规则会与这些默认规则合并。
```

## 依赖说明
-   需要 `autocoder.common.ignorefiles.ignore_file_utils` 模块及其依赖（主要是 `pathspec` 库）。通常这些是 `auto-coder` 项目的一部分。
-   Python 标准库 `os`。
-   需要在项目根目录或 `.auto-coder/` 目录下存在一个可选的 `.autocoderignore` 文件来定义自定义规则。如果文件不存在，将仅使用默认规则。
-   `.autocoderignore` 文件应使用 UTF-8 编码。

## 学习来源
本文档本身记录了 `autocoder.common.ignorefiles.ignore_file_utils` 模块的核心功能和使用方法。该模块通过加载和合并默认及自定义的忽略规则，提供了文件过滤的能力。
