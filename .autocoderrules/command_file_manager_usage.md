---
description: 使用 CommandManager 管理和分析命令文件
globs: ["*.py"]
alwaysApply: false
---

# 使用 CommandFileManager 管理和分析命令文件

## 简要说明
`CommandManager` 提供了一套完整的API，用于管理和分析 `.autocodercommands` 目录中的命令文件。它能够列出目录中的命令文件、读取指定文件内容，以及提取文件中的 Jinja2 变量及其元数据。特别适合需要处理模板文件和动态生成内容的场景。

## 典型用法
```python
from autocoder.common.command_file_manager import CommandManager, JinjaVariable

# 初始化命令管理器
# 方式1：使用默认目录（工作目录下的.autocodercommands目录）
manager = CommandManager()

# 方式2：指定自定义命令文件目录
manager = CommandManager("/path/to/commands")

# 列出所有命令文件（支持递归搜索）
result = manager.list_command_files(recursive=True)
if result.success:
    for file_path in result.command_files:
        print(f"找到命令文件: {file_path}")

# 读取特定命令文件
command_file = manager.read_command_file("example.autocodercommand")
if command_file:
    print(f"文件名: {command_file.file_name}")
    print(f"内容: {command_file.content}")

# 分析命令文件，提取Jinja2变量
analysis = manager.analyze_command_file("example.autocodercommand")
if analysis:
    print(f"文件: {analysis.file_name}")
    print(f"包含的变量:")
    for variable in analysis.variables:
        print(f"  - {variable.name}")
        if variable.default_value:
            print(f"    默认值: {variable.default_value}")
        if variable.description:
            print(f"    描述: {variable.description}")

# 获取所有命令文件中的变量
variables_map = manager.get_all_variables(recursive=True)
for file_path, variables in variables_map.items():
    print(f"文件 {file_path} 中的变量: {', '.join(variables)}")
```

## 高级用法

### 变量元数据提取
命令文件中可以使用特殊注释格式来定义变量的元数据：

```
{# @var: variable_name, default: default_value, description: 变量描述 #}
```

这些元数据会被 `extract_jinja2_variables_with_metadata` 函数提取并包含在分析结果中：

```python
from autocoder.common.command_file_manager import extract_jinja2_variables_with_metadata

content = """
{# @var: project_name, default: MyProject, description: 项目名称 #}
# {{ project_name }}

这是一个由 {{ author }} 创建的项目。
"""

variables = extract_jinja2_variables_with_metadata(content)
for var in variables:
    print(f"变量: {var.name}")
    print(f"默认值: {var.default_value}")
    print(f"描述: {var.description}")
```

### 自定义命令文件识别
默认情况下，模块会将扩展名为 `.md` 的文件识别为命令文件。您可以通过修改 `is_command_file` 函数来自定义识别规则：

```python
from autocoder.common.command_file_manager import is_command_file

# 原始函数
def is_command_file(file_name: str) -> bool:
    return file_name.endswith('.md')

# 扩展为支持更多类型
def custom_is_command_file(file_name: str) -> bool:
    return (file_name.endswith('.md') or 
            file_name.endswith('.j2') or
            file_name.endswith('.template'))
```

## 最佳实践

1. **组织命令文件**：将相关的命令文件组织在有意义的目录结构中，便于管理和查找。

2. **添加变量元数据**：为命令文件中的变量添加元数据注释，提供默认值和描述，增强可读性和可维护性。

3. **错误处理**：使用模块提供的结果对象的 `success` 和 `errors` 属性进行错误处理。

4. **递归搜索**：对于复杂的项目结构，使用递归搜索来确保找到所有命令文件。

5. **变量分析**：定期分析命令文件中的变量，确保模板一致性和完整性。

## 注意事项

- 命令文件应使用 UTF-8 编码，以确保正确处理各种字符。
- 变量名应遵循 Python 标识符命名规则（字母、数字和下划线，不以数字开头）。
- 大型项目中，递归搜索可能会影响性能，请根据需要选择是否使用。
