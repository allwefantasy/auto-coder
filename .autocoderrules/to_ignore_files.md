# 如何使用 ignore_file_utils 排除文件

`autocoder.common.ignorefiles.ignore_file_utils` 模块提供了一种机制，用于根据 `.autocoderignore` 文件中的规则来判断是否应忽略某个文件或目录。这在处理项目文件时非常有用，可以避免处理版本控制目录、构建产物、虚拟环境等不需要的文件。

## 工作原理

1.  **加载规则**: 模块会自动查找项目根目录下的 `.autocoderignore` 文件，或者 `.auto-coder/.autocoderignore` 文件。如果找到，它会读取其中的规则。
2.  **默认规则**: 即使没有找到 `.autocoderignore` 文件，模块也会应用一组默认的排除规则，包括常见的目录如 `.git`, `node_modules`, `__pycache__`, `.venv`, `build`, `dist` 等。
3.  **规则合并**: `.autocoderignore` 文件中的规则会与默认规则合并。
4.  **匹配**: 使用 `pathspec` 库和 `gitwildmatch` 语法来匹配文件路径。

## 如何使用

### 1. 创建 `.autocoderignore` 文件

在你的项目根目录下，或者在项目的 `.auto-coder/` 子目录下，创建一个名为 `.autocoderignore` 的文本文件。

### 2. 添加忽略规则

在 `.autocoderignore` 文件中，每行添加一个忽略规则。语法遵循 Git 的 `.gitignore` 规则 (`gitwildmatch`)。

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

# 忽略 build 目录 (即使没有在默认规则中，也可以添加)
build/

# 忽略所有 .tmp 文件，无论在哪个目录下
**/*.tmp
```

### 3. 在代码中使用

导入 `should_ignore` 函数，并传入你想检查的文件或目录的路径。函数内部会处理相对路径和绝对路径。

```python
from autocoder.common.ignorefiles.ignore_file_utils import should_ignore
import os

# 假设项目根目录是当前工作目录
project_root = os.getcwd()

# 要检查的文件的绝对路径
file_path_absolute = os.path.join(project_root, "logs/app.log")
config_path_absolute = os.path.join(project_root, "config.dev.json")
source_file_absolute = os.path.join(project_root, "src/main.py")
ignored_dir_absolute = os.path.join(project_root, "node_modules/some_package")
target_file_absolute = os.path.join(project_root, "target/output.bin")
important_target_file = os.path.join(project_root, "target/important.txt")

# 获取相对于项目根目录的路径 (可选，should_ignore 内部会处理)
# file_path_relative = os.path.relpath(file_path_absolute, project_root)

# 检查是否应该忽略 (传入绝对路径)
print(f"Checking: {file_path_absolute}")
if should_ignore(file_path_absolute):
    print(f"Result: Ignored")
else:
    print(f"Result: Not Ignored")

print(f"\nChecking: {config_path_absolute}")
if should_ignore(config_path_absolute):
    print(f"Result: Ignored")
else:
    print(f"Result: Not Ignored")

print(f"\nChecking: {source_file_absolute}")
if should_ignore(source_file_absolute):
    print(f"Result: Ignored")
else:
    print(f"Result: Not Ignored")

print(f"\nChecking: {ignored_dir_absolute}")
if should_ignore(ignored_dir_absolute):
    print(f"Result: Ignored")
else:
    print(f"Result: Not Ignored")

print(f"\nChecking: {target_file_absolute}")
if should_ignore(target_file_absolute):
     print(f"Result: Ignored")
else:
    print(f"Result: Not Ignored")

print(f"\nChecking: {important_target_file}")
if should_ignore(important_target_file):
     print(f"Result: Ignored")
else:
    print(f"Result: Not Ignored")

# 也可以直接传入相对路径
# print(f"\nChecking relative path: logs/app.log")
# if should_ignore("logs/app.log"):
#      print(f"Result: Ignored")
# else:
#      print(f"Result: Not Ignored")

```

**输出 (基于上面的示例 `.autocoderignore`):**

```
Checking: /path/to/your/project/logs/app.log
Result: Ignored

Checking: /path/to/your/project/config.dev.json
Result: Ignored

Checking: /path/to/your/project/src/main.py
Result: Not Ignored

Checking: /path/to/your/project/node_modules/some_package
Result: Ignored

Checking: /path/to/your/project/target/output.bin
Result: Ignored

Checking: /path/to/your/project/target/important.txt
Result: Not Ignored
```

## 默认排除规则

以下是默认包含的排除模式列表 (`DEFAULT_EXCLUDES`):

```python
[
    '.git',
    '.auto-coder', # 通常包含内部状态或缓存
    'node_modules',
    '.mvn',
    '.idea',
    '__pycache__',
    '.venv',
    'venv',
    'dist',
    'build',
    '.gradle',
    '.next'
]
```

这些规则会自动生效，除非你在 `.autocoderignore` 文件中使用 `!` 规则显式地取消忽略它们（通常不建议这样做）。

## 注意事项

-   `should_ignore(path)` 函数接受文件或目录的路径字符串作为输入。它可以处理绝对路径和相对于当前工作目录（通常是项目根目录）的相对路径。
-   模块内部使用单例模式 (`IgnoreFileManager`)，确保规则只加载一次，并在 `.autocoderignore` 文件发生变化时（如果 `FileMonitor` 可用且已配置）自动重新加载。
-   确保你的 `.autocoderignore` 文件使用 UTF-8 编码。
-   空行和以 `#` 开头的行在 `.autocoderignore` 文件中会被忽略。