
# Command File Manager 模块

该模块提供了一套完整的API，用于管理和分析 `.autocodercommands` 目录中的命令文件。它能够列出目录中的命令文件、读取指定文件内容，以及提取文件中的 Jinja2 变量及其元数据。特别适合需要处理模板文件和动态生成内容的场景。

## 模块概览

```
command_file_manager/
├── __init__.py              # 模块导入接口
├── models.py               # 数据模型定义
├── manager.py              # 命令管理器核心实现
├── utils.py                # 工具函数
├── examples.py             # 使用示例
└── README.md               # 本文档
```

## 核心组件

### CommandManager - 命令管理器

提供高层次的API接口，用于管理和分析命令文件。是整个模块的主要入口点。

#### 基本用法

```python
from autocoder.common.command_file_manager import CommandManager

# 创建命令管理器实例
manager = CommandManager("/path/to/.autocodercommands")

# 列出所有命令文件
result = manager.list_command_files(recursive=True)
if result.success:
    for file_path in result.command_files:
        print(f"找到命令文件: {file_path}")
```

#### 主要功能

1. **文件管理**: 列出命令文件、读取文件内容、获取文件路径
2. **变量提取**: 分析 Jinja2 变量、提取变量元数据、获取所有变量
3. **目录操作**: 支持递归搜索、自动创建目录、相对路径处理
4. **错误处理**: 完善的异常处理机制、详细的错误信息记录

#### 核心方法

- `list_command_files(recursive=True)`: 列出命令文件
- `read_command_file(file_name)`: 读取指定文件
- `analyze_command_file(file_name)`: 分析文件中的变量
- `get_all_variables(recursive=False)`: 获取所有文件的变量

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

## 使用示例

### 基础使用流程

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

