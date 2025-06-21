
# Command File Manager 模块

该模块提供了一套完整的API，用于管理和分析 `.autocodercommands` 目录中的命令文件。它能够列出目录中的命令文件、读取指定文件内容，以及提取文件中的 Jinja2 变量及其元数据。特别适合需要处理模板文件和动态生成内容的场景。

## 快速开始

### 基本用法示例

```python
from autocoder.common.command_file_manager import CommandManager

# 1. 创建命令管理器实例
manager = CommandManager("/path/to/.autocodercommands")

# 2. 列出所有命令文件
result = manager.list_command_files(recursive=True)
if result.success:
    print(f"找到 {len(result.command_files)} 个命令文件:")
    for file_path in result.command_files:
        print(f"  - {file_path}")
else:
    print(f"列出文件失败: {result.errors}")

# 3. 读取指定命令文件
command_file = manager.read_command_file("example.md")
if command_file:
    print(f"文件名: {command_file.file_name}")
    print(f"文件路径: {command_file.file_path}")
    print(f"文件内容:\n{command_file.content}")
else:
    print("文件读取失败")

# 4. 分析文件中的 Jinja2 变量
analysis = manager.analyze_command_file("example.md")
if analysis:
    print(f"文件 {analysis.file_name} 包含的变量:")
    for var in analysis.variables:
        print(f"  - {var.name}")
        if var.default_value:
            print(f"    默认值: {var.default_value}")
        if var.description:
            print(f"    描述: {var.description}")
else:
    print("文件分析失败")

# 5. 获取所有文件中的变量映射
variables_map = manager.get_all_variables(recursive=True)
for file_path, variables in variables_map.items():
    print(f"文件 {file_path} 中的变量: {', '.join(variables)}")
```

## 核心 API 详解

### CommandManager 类

CommandManager 是模块的主要入口点，提供了所有核心功能的高层次接口。

#### 初始化

```python
from autocoder.common.command_file_manager import CommandManager

# 初始化管理器，指定命令文件目录
manager = CommandManager("/path/to/.autocodercommands")
```

#### 主要方法

##### 1. list_command_files(recursive=True)

列出目录中的所有命令文件。

**参数:**
- `recursive` (bool): 是否递归搜索子目录，默认为 True

**返回值:** `ListCommandsResult` 对象
- `success` (bool): 操作是否成功
- `command_files` (List[str]): 找到的命令文件路径列表
- `errors` (Dict[str, str]): 错误信息映射

**示例:**
```python
# 递归搜索所有命令文件
result = manager.list_command_files(recursive=True)
if result.success:
    for file_path in result.command_files:
        print(f"找到命令文件: {file_path}")
else:
    for path, error in result.errors.items():
        print(f"错误 {path}: {error}")

# 只搜索顶层目录
result = manager.list_command_files(recursive=False)
```

##### 2. read_command_file(file_name)

读取指定的命令文件内容。

**参数:**
- `file_name` (str): 要读取的文件名

**返回值:** `CommandFile` 对象或 None
- `file_path` (str): 文件的完整路径
- `file_name` (str): 文件名
- `content` (str): 文件内容

**示例:**
```python
command_file = manager.read_command_file("template.md")
if command_file:
    print(f"文件: {command_file.file_name}")
    print(f"路径: {command_file.file_path}")
    print(f"内容长度: {len(command_file.content)} 字符")
else:
    print("文件不存在或读取失败")
```

##### 3. analyze_command_file(file_name)

分析命令文件，提取其中的 Jinja2 变量及元数据。

**参数:**
- `file_name` (str): 要分析的文件名

**返回值:** `CommandFileAnalysisResult` 对象或 None
- `file_path` (str): 文件路径
- `file_name` (str): 文件名
- `variables` (List[JinjaVariable]): 提取的变量列表
- `raw_variables` (Set[str]): 原始变量名集合

**示例:**
```python
analysis = manager.analyze_command_file("template.md")
if analysis:
    print(f"分析文件: {analysis.file_name}")
    print(f"找到 {len(analysis.variables)} 个变量:")
    
    for var in analysis.variables:
        print(f"  变量名: {var.name}")
        if var.default_value:
            print(f"  默认值: {var.default_value}")
        if var.description:
            print(f"  描述: {var.description}")
        print("  ---")
else:
    print("文件分析失败")
```

##### 4. get_all_variables(recursive=False)

获取所有命令文件中的变量映射。

**参数:**
- `recursive` (bool): 是否递归搜索，默认为 False

**返回值:** `Dict[str, Set[str]]` - 文件路径到变量名集合的映射

**示例:**
```python
# 获取所有文件的变量映射
variables_map = manager.get_all_variables(recursive=True)

print("变量使用统计:")
all_variables = set()
for file_path, variables in variables_map.items():
    print(f"{file_path}: {len(variables)} 个变量")
    print(f"  变量: {', '.join(sorted(variables))}")
    all_variables.update(variables)

print(f"\n总计唯一变量: {len(all_variables)}")
print(f"所有变量: {', '.join(sorted(all_variables))}")
```

##### 5. get_command_file_path(file_name)

获取命令文件的完整路径。

**参数:**
- `file_name` (str): 文件名

**返回值:** `str` - 文件的完整路径

**示例:**
```python
file_path = manager.get_command_file_path("example.md")
print(f"文件完整路径: {file_path}")
```

### 数据模型

#### CommandFile - 命令文件模型

表示单个命令文件的信息，包含文件路径、名称和内容。

```python
from autocoder.common.command_file_manager import CommandFile

# 创建命令文件对象
command_file = CommandFile(
    file_path="/path/to/file.md",
    file_name="file.md",
    content="文件内容"
)

# 转换为字典
file_dict = command_file.to_dict()

# 从字典创建
command_file = CommandFile.from_dict(file_dict)
```

#### JinjaVariable - Jinja2变量模型

表示从命令文件中提取的 Jinja2 变量及其元数据。

```python
from autocoder.common.command_file_manager import JinjaVariable

# 创建变量对象
variable = JinjaVariable(
    name="project_name",
    default_value="MyProject",
    description="项目名称"
)
```

#### CommandFileAnalysisResult - 分析结果模型

表示命令文件分析的完整结果，包含文件信息和提取的变量。

```python
# 分析结果包含以下信息
analysis = manager.analyze_command_file("example.md")
print(f"文件路径: {analysis.file_path}")
print(f"文件名: {analysis.file_name}")
print(f"变量列表: {[var.name for var in analysis.variables]}")
print(f"原始变量集合: {analysis.raw_variables}")
```

#### ListCommandsResult - 列表结果模型

表示列出命令文件操作的结果，包含成功状态、文件列表和错误信息。

```python
# 检查列表操作结果
result = manager.list_command_files()
if result.success:
    print(f"找到 {len(result.command_files)} 个命令文件")
else:
    print(f"操作失败，错误: {result.errors}")
```

## 工具函数

### extract_jinja2_variables

从文本内容中提取所有 Jinja2 变量名。

```python
from autocoder.common.command_file_manager import extract_jinja2_variables

content = """
# {{ project_name }}
作者: {{ author }}
{% if include_license %}
许可证: {{ license_type }}
{% endif %}
"""

variables = extract_jinja2_variables(content)
print(variables)  # {'project_name', 'author', 'include_license', 'license_type'}
```

### extract_jinja2_variables_with_metadata

提取 Jinja2 变量及其元数据，支持特殊注释格式。

```python
from autocoder.common.command_file_manager import extract_jinja2_variables_with_metadata

content = """
{# @var: project_name, default: MyProject, description: 项目名称 #}
{# @var: author, default: User, description: 作者姓名 #}
# {{ project_name }}
作者: {{ author }}
"""

variables = extract_jinja2_variables_with_metadata(content)
for var in variables:
    print(f"变量: {var.name}, 默认值: {var.default_value}, 描述: {var.description}")
```

### analyze_command_file

完整分析命令文件，返回包含所有信息的分析结果。

```python
from autocoder.common.command_file_manager import analyze_command_file

# 直接分析文件内容
result = analyze_command_file("/path/to/file.md", file_content)
```

### is_command_file

检查文件是否为命令文件（默认检查 `.md` 扩展名）。

```python
from autocoder.common.command_file_manager import is_command_file

print(is_command_file("example.md"))     # True
print(is_command_file("example.txt"))    # False
```

## 实际应用场景

### 场景 1: 文档管理系统

在构建文档管理系统时，可以使用 CommandManager 来管理和分析文档模板：

```python
from autocoder.common.command_file_manager import CommandManager
import os
from pathlib import Path

class DocumentManager:
    def __init__(self, project_path: str):
        """初始化文档管理器"""
        self.documents_path = Path(project_path) / ".autocodercommands"
        self.manager = CommandManager(str(self.documents_path))
    
    def list_all_documents(self, recursive: bool = False):
        """列出所有文档文件"""
        result = self.manager.list_command_files(recursive=recursive)
        
        if not result.success:
            return {"success": False, "errors": result.errors}
        
        # 转换为文档对象
        documents = []
        for file_path in result.command_files:
            file_name = os.path.basename(file_path)
            documents.append({
                "file_name": file_name,
                "file_path": file_path
            })
        
        return {"success": True, "documents": documents}
    
    def get_document_content(self, file_name: str):
        """获取文档内容"""
        command_file = self.manager.read_command_file(file_name)
        
        if not command_file:
            return {"success": False, "error": f"文档 '{file_name}' 未找到"}
        
        return {
            "success": True,
            "document": {
                "file_name": command_file.file_name,
                "file_path": command_file.file_path
            },
            "content": command_file.content
        }
    
    def analyze_document_variables(self, file_name: str):
        """分析文档变量"""
        analysis = self.manager.analyze_command_file(file_name)
        
        if not analysis:
            return {"success": False, "error": f"无法分析文档 '{file_name}'"}
        
        # 转换变量格式
        variables = []
        for var in analysis.variables:
            variables.append({
                "name": var.name,
                "default_value": var.default_value,
                "description": var.description
            })
        
        return {
            "success": True,
            "analysis": {
                "file_name": analysis.file_name,
                "file_path": analysis.file_path,
                "variables": variables
            }
        }
    
    def get_all_variables_map(self, recursive: bool = False):
        """获取所有变量映射"""
        try:
            variables = self.manager.get_all_variables(recursive=recursive)
            return {"success": True, "variables": variables}
        except Exception as e:
            return {"success": False, "error": str(e)}

# 使用示例
doc_manager = DocumentManager("/path/to/project")

# 列出所有文档
result = doc_manager.list_all_documents(recursive=True)
if result["success"]:
    print(f"找到 {len(result['documents'])} 个文档")
    for doc in result["documents"]:
        print(f"  - {doc['file_name']}")

# 读取特定文档
content_result = doc_manager.get_document_content("example.md")
if content_result["success"]:
    print(f"文档内容: {content_result['content']}")

# 分析文档变量
analysis_result = doc_manager.analyze_document_variables("example.md")
if analysis_result["success"]:
    analysis = analysis_result["analysis"]
    print(f"文档 {analysis['file_name']} 包含变量:")
    for var in analysis["variables"]:
        print(f"  - {var['name']}: {var.get('description', '无描述')}")
```

### 场景 2: 模板渲染引擎

结合 Jinja2 模板引擎，创建一个完整的模板渲染系统：

```python
from jinja2 import Template, Environment
from autocoder.common.command_file_manager import CommandManager

class TemplateRenderer:
    def __init__(self, commands_dir: str):
        self.manager = CommandManager(commands_dir)
        self.env = Environment()
    
    def render_template(self, file_name: str, variables: dict):
        """渲染模板文件"""
        try:
            # 读取模板文件
            command_file = self.manager.read_command_file(file_name)
            if not command_file:
                return {"success": False, "error": f"模板文件 '{file_name}' 未找到"}
            
            # 分析模板变量
            analysis = self.manager.analyze_command_file(file_name)
            if analysis:
                # 检查必需变量
                required_vars = {var.name for var in analysis.variables 
                               if var.default_value is None}
                missing_vars = required_vars - set(variables.keys())
                if missing_vars:
                    return {"success": False, "error": f"缺少必需变量: {missing_vars}"}
                
                # 应用默认值
                final_vars = variables.copy()
                for var in analysis.variables:
                    if var.name not in final_vars and var.default_value:
                        final_vars[var.name] = var.default_value
            else:
                final_vars = variables
            
            # 创建并渲染模板
            template = self.env.from_string(command_file.content)
            rendered_content = template.render(**final_vars)
            
            return {"success": True, "rendered_content": rendered_content}
            
        except Exception as e:
            return {"success": False, "error": f"渲染错误: {str(e)}"}
    
    def get_template_variables(self, file_name: str):
        """获取模板所需变量"""
        analysis = self.manager.analyze_command_file(file_name)
        if not analysis:
            return {"success": False, "error": f"无法分析模板 '{file_name}'"}
        
        variables_info = []
        for var in analysis.variables:
            variables_info.append({
                "name": var.name,
                "required": var.default_value is None,
                "default_value": var.default_value,
                "description": var.description
            })
        
        return {"success": True, "variables": variables_info}

# 使用示例
renderer = TemplateRenderer(".autocodercommands")

# 获取模板变量信息
vars_result = renderer.get_template_variables("project_template.md")
if vars_result["success"]:
    print("模板变量:")
    for var in vars_result["variables"]:
        status = "必需" if var["required"] else "可选"
        print(f"  - {var['name']} ({status})")
        if var["description"]:
            print(f"    描述: {var['description']}")
        if var["default_value"]:
            print(f"    默认值: {var['default_value']}")

# 渲染模板
template_vars = {
    "project_name": "MyAwesomeProject",
    "author": "John Doe",
    "version": "1.0.0"
}

render_result = renderer.render_template("project_template.md", template_vars)
if render_result["success"]:
    print("渲染结果:")
    print(render_result["rendered_content"])
else:
    print(f"渲染失败: {render_result['error']}")
```

### 场景 3: 命令行工具集成

创建一个命令行工具来管理命令文件：

```python
import argparse
import json
from autocoder.common.command_file_manager import CommandManager

class CommandLineTool:
    def __init__(self):
        self.manager = None
    
    def set_directory(self, directory: str):
        """设置命令文件目录"""
        self.manager = CommandManager(directory)
        print(f"已设置命令文件目录: {directory}")
    
    def list_files(self, recursive: bool = False):
        """列出命令文件"""
        if not self.manager:
            print("错误: 请先设置命令文件目录")
            return
        
        result = self.manager.list_command_files(recursive=recursive)
        if result.success:
            print(f"找到 {len(result.command_files)} 个命令文件:")
            for file_path in result.command_files:
                print(f"  {file_path}")
        else:
            print("列出文件失败:")
            for path, error in result.errors.items():
                print(f"  {path}: {error}")
    
    def show_file_info(self, file_name: str):
        """显示文件信息"""
        if not self.manager:
            print("错误: 请先设置命令文件目录")
            return
        
        # 读取文件
        command_file = self.manager.read_command_file(file_name)
        if not command_file:
            print(f"错误: 文件 '{file_name}' 未找到")
            return
        
        print(f"文件名: {command_file.file_name}")
        print(f"路径: {command_file.file_path}")
        print(f"内容长度: {len(command_file.content)} 字符")
        
        # 分析变量
        analysis = self.manager.analyze_command_file(file_name)
        if analysis:
            print(f"变量数量: {len(analysis.variables)}")
            if analysis.variables:
                print("变量列表:")
                for var in analysis.variables:
                    print(f"  - {var.name}")
                    if var.default_value:
                        print(f"    默认值: {var.default_value}")
                    if var.description:
                        print(f"    描述: {var.description}")
    
    def export_variables(self, output_file: str, recursive: bool = False):
        """导出所有变量到 JSON 文件"""
        if not self.manager:
            print("错误: 请先设置命令文件目录")
            return
        
        try:
            variables_map = self.manager.get_all_variables(recursive=recursive)
            
            # 转换 set 为 list 以便 JSON 序列化
            json_data = {path: list(variables) for path, variables in variables_map.items()}
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(json_data, f, ensure_ascii=False, indent=2)
            
            print(f"变量已导出到: {output_file}")
            
        except Exception as e:
            print(f"导出失败: {e}")
    
    def validate_template(self, file_name: str, variables_file: str = None):
        """验证模板文件"""
        if not self.manager:
            print("错误: 请先设置命令文件目录")
            return
        
        analysis = self.manager.analyze_command_file(file_name)
        if not analysis:
            print(f"错误: 无法分析文件 '{file_name}'")
            return
        
        print(f"验证模板: {file_name}")
        print(f"发现 {len(analysis.variables)} 个变量")
        
        # 检查变量完整性
        required_vars = [var for var in analysis.variables if var.default_value is None]
        optional_vars = [var for var in analysis.variables if var.default_value is not None]
        
        if required_vars:
            print("必需变量:")
            for var in required_vars:
                print(f"  - {var.name}: {var.description or '无描述'}")
        
        if optional_vars:
            print("可选变量:")
            for var in optional_vars:
                print(f"  - {var.name} (默认: {var.default_value}): {var.description or '无描述'}")
        
        # 如果提供了变量文件，验证完整性
        if variables_file:
            try:
                with open(variables_file, 'r', encoding='utf-8') as f:
                    provided_vars = json.load(f)
                
                missing_vars = [var.name for var in required_vars if var.name not in provided_vars]
                if missing_vars:
                    print(f"警告: 缺少必需变量: {missing_vars}")
                else:
                    print("✓ 所有必需变量都已提供")
                    
            except Exception as e:
                print(f"读取变量文件失败: {e}")

def main():
    parser = argparse.ArgumentParser(description='命令文件管理工具')
    parser.add_argument('-d', '--directory', default='.autocodercommands', 
                       help='命令文件目录路径')
    
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # 列出文件命令
    list_parser = subparsers.add_parser('list', help='列出命令文件')
    list_parser.add_argument('-r', '--recursive', action='store_true', 
                           help='递归搜索子目录')
    
    # 显示文件信息命令
    info_parser = subparsers.add_parser('info', help='显示文件信息')
    info_parser.add_argument('file_name', help='文件名')
    
    # 导出变量命令
    export_parser = subparsers.add_parser('export', help='导出变量')
    export_parser.add_argument('output_file', help='输出文件路径')
    export_parser.add_argument('-r', '--recursive', action='store_true', 
                             help='递归搜索子目录')
    
    # 验证模板命令
    validate_parser = subparsers.add_parser('validate', help='验证模板文件')
    validate_parser.add_argument('file_name', help='模板文件名')
    validate_parser.add_argument('-v', '--variables', help='变量文件路径')
    
    args = parser.parse_args()
    
    tool = CommandLineTool()
    tool.set_directory(args.directory)
    
    if args.command == 'list':
        tool.list_files(args.recursive)
    elif args.command == 'info':
        tool.show_file_info(args.file_name)
    elif args.command == 'export':
        tool.export_variables(args.output_file, args.recursive)
    elif args.command == 'validate':
        tool.validate_template(args.file_name, args.variables)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
```

### 使用示例

```bash
# 列出所有命令文件
python cli_tool.py list -r

# 显示特定文件信息
python cli_tool.py info example.md

# 导出所有变量到 JSON 文件
python cli_tool.py export variables.json -r

# 验证模板文件
python cli_tool.py validate template.md -v variables.json
```

## 基础使用流程

```python
from autocoder.common.command_file_manager import CommandManager

# 1. 初始化管理器
manager = CommandManager(".autocodercommands")

# 2. 列出所有命令文件
files_result = manager.list_command_files(recursive=True)
if files_result.success:
    print(f"找到 {len(files_result.command_files)} 个命令文件")
    
    # 3. 逐个分析文件
    for file_name in files_result.command_files:
        analysis = manager.analyze_command_file(file_name)
        if analysis:
            print(f"\n文件: {analysis.file_name}")
            print(f"变量数量: {len(analysis.variables)}")
            
            # 4. 显示变量详情
            for var in analysis.variables:
                print(f"  - {var.name}")
                if var.default_value:
                    print(f"    默认值: {var.default_value}")
                if var.description:
                    print(f"    描述: {var.description}")
```

### 变量元数据格式

在命令文件中使用特殊注释格式定义变量元数据：

```markdown
{# @var: variable_name, default: default_value, description: 变量描述 #}
{# @var: project_name, default: MyProject, description: 项目名称 #}
{# @var: author, default: User, description: 作者姓名 #}
{# @var: version, description: 项目版本号 #}

# {{ project_name }}

这是一个由 {{ author }} 创建的项目，版本号为 {{ version }}。

{% if include_readme %}
## 说明
{{ readme_content }}
{% endif %}
```

### 批量变量分析

```python
# 获取所有文件中的变量映射
variables_map = manager.get_all_variables(recursive=True)

# 统计变量使用情况
all_variables = set()
file_count = {}

for file_path, variables in variables_map.items():
    print(f"文件: {file_path}")
    print(f"变量: {', '.join(sorted(variables))}")
    
    # 统计每个变量在多少个文件中使用
    for var in variables:
        all_variables.add(var)
        file_count[var] = file_count.get(var, 0) + 1

print(f"\n总计变量: {len(all_variables)}")
print("变量使用频率:")
for var, count in sorted(file_count.items(), key=lambda x: x[1], reverse=True):
    print(f"  {var}: {count} 个文件")
```

### 错误处理示例

```python
# 完善的错误处理
try:
    manager = CommandManager(".autocodercommands")
    
    # 列出文件时的错误处理
    result = manager.list_command_files()
    if not result.success:
        print("列出文件失败:")
        for path, error in result.errors.items():
            print(f"  {path}: {error}")
        return
    
    # 读取文件时的错误处理
    for file_name in result.command_files:
        command_file = manager.read_command_file(file_name)
        if command_file is None:
            print(f"无法读取文件: {file_name}")
            continue
            
        # 分析文件时的错误处理
        analysis = manager.analyze_command_file(file_name)
        if analysis is None:
            print(f"无法分析文件: {file_name}")
            continue
            
        print(f"成功分析文件: {file_name}")
        
except Exception as e:
    print(f"操作过程中发生错误: {e}")
```

## 配置和扩展

### 自定义命令文件识别

```python
# 扩展支持的文件类型
def custom_is_command_file(file_name: str) -> bool:
    """自定义命令文件识别逻辑"""
    supported_extensions = ['.md', '.j2', '.template', '.jinja', '.txt']
    return any(file_name.endswith(ext) for ext in supported_extensions)

# 替换默认的识别函数
import autocoder.common.command_file_manager.utils as utils
utils.is_command_file = custom_is_command_file
```

### 扩展变量提取规则

```python
import re
from autocoder.common.command_file_manager import extract_jinja2_variables

def extract_custom_variables(content: str) -> set:
    """扩展变量提取，支持自定义格式"""
    # 原有的 Jinja2 变量
    jinja_vars = extract_jinja2_variables(content)
    
    # 添加自定义格式支持，如 ${variable}
    custom_pattern = r'\$\{([a-zA-Z0-9_]+)\}'
    custom_vars = set(re.findall(custom_pattern, content))
    
    return jinja_vars.union(custom_vars)
```

## 性能优化

### 大量文件处理

```python
import os
from concurrent.futures import ThreadPoolExecutor

def process_files_parallel(manager: CommandManager, max_workers: int = 4):
    """并行处理大量命令文件"""
    files_result = manager.list_command_files(recursive=True)
    if not files_result.success:
        return {}
    
    def analyze_single_file(file_name):
        return file_name, manager.analyze_command_file(file_name)
    
    results = {}
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_file = {
            executor.submit(analyze_single_file, file_name): file_name 
            for file_name in files_result.command_files
        }
        
        for future in future_to_file:
            file_name, analysis = future.result()
            if analysis:
                results[file_name] = analysis
    
    return results
```

### 缓存机制

```python
import hashlib
import json
from typing import Dict, Optional

class CachedCommandManager(CommandManager):
    """带缓存功能的命令管理器"""
    
    def __init__(self, commands_dir: str):
        super().__init__(commands_dir)
        self._cache: Dict[str, any] = {}
    
    def _get_file_hash(self, file_path: str) -> str:
        """计算文件内容哈希值"""
        try:
            with open(file_path, 'rb') as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return ""
    
    def analyze_command_file(self, file_name: str) -> Optional[CommandFileAnalysisResult]:
        """带缓存的文件分析"""
        file_path = self.get_command_file_path(file_name)
        file_hash = self._get_file_hash(file_path)
        cache_key = f"{file_name}:{file_hash}"
        
        # 检查缓存
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        # 执行分析
        result = super().analyze_command_file(file_name)
        
        # 存储到缓存
        if result:
            self._cache[cache_key] = result
        
        return result
```

## 集成示例

### 与模板引擎集成

```python
from jinja2 import Environment, FileSystemLoader
from autocoder.common.command_file_manager import CommandManager

def render_command_template(template_name: str, variables: dict) -> str:
    """使用提取的变量渲染模板"""
    manager = CommandManager(".autocodercommands")
    
    # 分析模板文件
    analysis = manager.analyze_command_file(template_name)
    if not analysis:
        raise ValueError(f"无法分析模板文件: {template_name}")
    
    # 检查必需的变量
    required_vars = {var.name for var in analysis.variables if var.default_value is None}
    missing_vars = required_vars - set(variables.keys())
    if missing_vars:
        raise ValueError(f"缺少必需的变量: {missing_vars}")
    
    # 应用默认值
    final_vars = {}
    for var in analysis.variables:
        if var.name in variables:
            final_vars[var.name] = variables[var.name]
        elif var.default_value:
            final_vars[var.name] = var.default_value
    
    # 渲染模板
    command_file = manager.read_command_file(template_name)
    if not command_file:
        raise ValueError(f"无法读取模板文件: {template_name}")
    
    env = Environment()
    template = env.from_string(command_file.content)
    return template.render(**final_vars)
```

### 与配置管理集成

```python
import yaml
from pathlib import Path

class ConfigurableCommandManager(CommandManager):
    """支持配置文件的命令管理器"""
    
    def __init__(self, commands_dir: str, config_file: str = None):
        super().__init__(commands_dir)
        self.config = self._load_config(config_file)
    
    def _load_config(self, config_file: str) -> dict:
        """加载配置文件"""
        if not config_file:
            return {}
        
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except:
            return {}
    
    def get_variable_defaults(self, file_name: str) -> dict:
        """获取变量的配置默认值"""
        analysis = self.analyze_command_file(file_name)
        if not analysis:
            return {}
        
        defaults = {}
        file_config = self.config.get('files', {}).get(file_name, {})
        
        for var in analysis.variables:
            # 优先级: 配置文件 > 模板默认值
            if var.name in file_config:
                defaults[var.name] = file_config[var.name]
            elif var.default_value:
                defaults[var.name] = var.default_value
        
        return defaults
```

## 最佳实践

1. **目录组织**: 将相关的命令文件组织在有意义的目录结构中，便于管理和查找
2. **变量命名**: 使用清晰、一致的变量命名规范，避免冲突
3. **元数据注释**: 为所有变量添加描述和合适的默认值
4. **错误处理**: 始终检查操作结果的 `success` 状态和 `errors` 信息
5. **性能考虑**: 对于大型项目，考虑使用缓存和并行处理
6. **版本控制**: 将命令文件纳入版本控制，跟踪模板变更
7. **文档维护**: 保持 README 和注释的及时更新

## 依赖关系

该模块依赖以下核心组件：

- `os`: 文件系统操作
- `re`: 正则表达式匹配
- `logging`: 日志记录
- `dataclasses`: 数据类定义
- `typing`: 类型注解支持

## 错误处理

模块会处理以下常见错误情况：

- 目录不存在或无权访问
- 文件读取失败（编码、权限等）
- 正则表达式匹配错误
- 变量解析异常
- 内存不足（大文件处理）

## 性能特性

- **懒加载**: 只在需要时读取和分析文件
- **内存优化**: 使用生成器和迭代器减少内存占用
- **缓存友好**: 支持结果缓存和增量更新
- **并发安全**: 支持多线程并发访问

## 扩展指南

### 添加新的变量格式支持

1. **扩展正则表达式**: 在 `utils.py` 中添加新的匹配模式
2. **更新提取函数**: 修改 `extract_jinja2_variables` 函数
3. **测试验证**: 确保新格式能正确识别和提取

### 添加新的文件类型支持

1. **修改识别函数**: 更新 `is_command_file` 函数
2. **扩展分析逻辑**: 根据文件类型调整变量提取策略
3. **添加示例**: 提供新文件类型的使用示例

## 版本历史

- v1.0.0: 初始版本，基础文件管理和变量提取功能
- v1.1.0: 添加变量元数据支持和批量处理功能
- v1.2.0: 性能优化和错误处理改进
- 未来版本将继续添加更多文件格式支持和高级分析功能

