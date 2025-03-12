# AutoCommandTools 功能演示

这个目录包含 `demo_auto_command_tools.py` 演示脚本，用于展示如何使用 AutoCoderTools 进行代码分析和处理。

## 功能概述

AutoCommandTools 提供了一系列便捷的工具方法，帮助用户：

1. 读取和分析代码文件
2. 搜索代码库中的内容
3. 运行终端命令
4. 查找和定位文件
5. 分析代码结构
6. 辅助代码生成

## 如何运行演示脚本

```bash
cd notebooks
python demo_auto_command_tools.py
```

## 演示内容

该脚本展示了以下功能：

### 1. 读取文件内容

通过 `read_files` 方法读取指定文件的内容，可以指定行范围：

```python
file_content = tools.read_files(paths=file_path, line_ranges="1-50")
```

### 2. 读取多个文件

同时读取多个文件，为每个文件指定不同的行范围：

```python
multiple_files = tools.read_files(
    paths=[file_path1, file_path2],
    line_ranges=["1-10", "1-10"]
)
```

### 3. 搜索代码库

使用语义搜索在代码库中查找相关内容：

```python
search_results = tools.search_code(
    query="AutoCommandTools class definition",
    num_results=5
)
```

### 4. 执行终端命令

运行系统命令并获取结果：

```python
cmd_result = tools.run_command(
    command="ls -la " + command_path,
    working_dir=project_root
)
```

### 5. 查找文件

根据文件名模式查找文件：

```python
files = tools.find_files(
    query="tools.py",
    num_results=5
)
```

### 6. 分析文件内容与结构

分析代码文件的结构和内容（需要确认具体实现）：

```python
analysis = tools.analyze_code(
    file_path=file_to_analyze
)
```

### 7. 组合多个工具

将多个工具方法组合使用，构建复杂的代码处理流程：

1. 先搜索代码库中的特定功能
2. 读取相关文件内容
3. 使用命令行工具获取文件信息

### 8. 辅助代码生成

使用工具提供的上下文信息，辅助生成符合要求的代码。

## 自定义使用

如果您想在自己的项目中使用 AutoCommandTools，可以参考以下步骤：

1. 初始化 LLM 和参数：

```python
from autocoder.commands.tools import AutoCommandTools
from autocoder.common import AutoCoderArgs
from autocoder.utils.llms import get_single_llm

llm = get_single_llm("v3_chat", product_mode="lite")
args = AutoCoderArgs(model="v3_chat", source_dir=your_project_path)
```

2. 创建 AutoCommandTools 实例：

```python
tools = AutoCommandTools(args, llm)
```

3. 使用各种工具方法：

```python
# 读取文件
content = tools.read_files(paths=file_path, line_ranges="1-100")

# 搜索代码
results = tools.search_code(query="your search query", num_results=5)

# 运行命令
output = tools.run_command(command="your command", working_dir=working_directory)
```

## 主要方法参数说明

### read_files

- `paths`: 字符串或字符串列表，指定要读取的文件路径
- `line_ranges`: 字符串或字符串列表，指定要读取的行范围，格式为 "start-end"

### search_code

- `query`: 字符串，搜索查询
- `num_results`: 整数，返回的结果数量

### run_command

- `command`: 字符串，要执行的命令
- `working_dir`: 字符串，命令执行的工作目录

### find_files

- `query`: 字符串，文件查询模式
- `num_results`: 整数，返回的结果数量

## 注意事项

- 确保传递给工具的文件路径是有效的
- 命令执行功能应谨慎使用，避免运行不安全的命令
- 在大型代码库中，搜索可能需要一些时间 