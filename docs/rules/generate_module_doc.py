#!/usr/bin/env python3
"""
模块文档生成器

基于 AutoCoder 项目的标准模板，自动生成模块文档的基础结构。
使用方法：python generate_module_doc.py <模块路径>

示例：python generate_module_doc.py src/autocoder/common/v2/agent
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any
import argparse


def scan_directory_structure(module_path: str) -> Dict[str, Any]:
    """扫描模块目录结构"""
    structure = {
        "path": module_path,
        "files": [],
        "directories": [],
        "python_files": [],
        "test_files": [],
        "config_files": []
    }
    
    if not os.path.exists(module_path):
        print(f"错误：路径 {module_path} 不存在")
        return structure
    
    for root, dirs, files in os.walk(module_path):
        rel_root = os.path.relpath(root, module_path)
        
        for file in files:
            rel_path = os.path.join(rel_root, file) if rel_root != "." else file
            structure["files"].append(rel_path)
            
            if file.endswith('.py'):
                structure["python_files"].append(rel_path)
                if 'test' in file.lower():
                    structure["test_files"].append(rel_path)
            elif file.endswith(('.yml', '.yaml', '.json', '.toml', '.ini')):
                structure["config_files"].append(rel_path)
        
        for dir_name in dirs:
            rel_dir = os.path.join(rel_root, dir_name) if rel_root != "." else dir_name
            structure["directories"].append(rel_dir)
    
    return structure


def extract_python_info(file_path: str) -> Dict[str, Any]:
    """提取Python文件的基本信息"""
    info = {
        "classes": [],
        "functions": [],
        "imports": [],
        "docstring": ""
    }
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        lines = content.split('\n')
        in_docstring = False
        docstring_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # 提取类定义
            if stripped.startswith('class ') and ':' in stripped:
                class_name = stripped.split('class ')[1].split('(')[0].split(':')[0].strip()
                info["classes"].append(class_name)
            
            # 提取函数定义
            elif stripped.startswith('def ') and ':' in stripped:
                func_name = stripped.split('def ')[1].split('(')[0].strip()
                if not func_name.startswith('_'):  # 只记录公开函数
                    info["functions"].append(func_name)
            
            # 提取导入语句
            elif stripped.startswith(('import ', 'from ')):
                info["imports"].append(stripped)
            
            # 提取模块文档字符串
            elif '"""' in stripped and not in_docstring:
                if stripped.count('"""') == 2:
                    # 单行文档字符串
                    docstring = stripped.replace('"""', '').strip()
                    if not info["docstring"] and docstring:
                        info["docstring"] = docstring
                else:
                    # 多行文档字符串开始
                    in_docstring = True
                    docstring_lines.append(stripped.replace('"""', ''))
            elif in_docstring:
                if '"""' in stripped:
                    # 多行文档字符串结束
                    docstring_lines.append(stripped.replace('"""', ''))
                    info["docstring"] = '\n'.join(docstring_lines).strip()
                    in_docstring = False
                    docstring_lines = []
                else:
                    docstring_lines.append(stripped)
    
    except Exception as e:
        print(f"警告：无法解析文件 {file_path}: {e}")
    
    return info


def generate_directory_tree(structure: Dict[str, Any]) -> str:
    """生成目录树字符串"""
    tree_lines = []
    module_name = os.path.basename(structure["path"])
    tree_lines.append(f"{structure['path']}/")
    
    # 排序文件和目录
    all_items = []
    
    # 添加Python文件（排除测试文件）
    for file in sorted(structure["python_files"]):
        if 'test' not in file.lower():
            all_items.append((file, "file"))
    
    # 添加目录
    for directory in sorted(structure["directories"]):
        if not directory.startswith('.') and 'test' not in directory.lower():
            all_items.append((directory, "dir"))
    
    # 添加配置文件
    for file in sorted(structure["config_files"]):
        all_items.append((file, "file"))
    
    # 添加测试文件
    test_files = [f for f in structure["test_files"] if f not in structure["python_files"] or 'test' in f.lower()]
    for file in sorted(test_files):
        all_items.append((file, "file"))
    
    # 生成树结构
    for i, (item, item_type) in enumerate(all_items):
        is_last = i == len(all_items) - 1
        prefix = "└── " if is_last else "├── "
        
        if item_type == "dir":
            tree_lines.append(f"{prefix}{os.path.basename(item)}/                  # [子模块功能描述]")
        else:
            # 尝试获取文件描述
            file_path = os.path.join(structure["path"], item)
            description = get_file_description(file_path, item)
            tree_lines.append(f"{prefix}{os.path.basename(item):<30} # {description}")
    
    # 添加文档文件
    tree_lines.append("└── .meta.mod.md                   # 本文档")
    
    return "\n".join(tree_lines)


def get_file_description(file_path: str, relative_path: str) -> str:
    """获取文件功能描述"""
    filename = os.path.basename(relative_path)
    
    # 特殊文件的默认描述
    special_files = {
        "__init__.py": "模块初始化文件",
        "types.py": "类型定义",
        "constants.py": "常量定义",
        "exceptions.py": "异常定义",
        "utils.py": "工具函数",
        "config.py": "配置管理",
        "main.py": "主程序入口"
    }
    
    if filename in special_files:
        return special_files[filename]
    
    # 根据文件名推测功能
    if 'test' in filename.lower():
        return "测试文件"
    elif filename.endswith('_types.py'):
        return "类型定义"
    elif filename.endswith('_tool.py') or filename.endswith('_resolver.py'):
        return "工具解析器"
    elif filename.endswith('_manager.py'):
        return "管理器"
    elif filename.endswith('_handler.py'):
        return "处理器"
    elif filename.endswith('_client.py'):
        return "客户端"
    elif filename.endswith('_server.py'):
        return "服务器"
    
    # 尝试从文件中提取文档字符串
    if os.path.exists(file_path) and filename.endswith('.py'):
        info = extract_python_info(file_path)
        if info["docstring"]:
            # 取文档字符串的第一行作为描述
            first_line = info["docstring"].split('\n')[0].strip()
            if first_line and len(first_line) < 50:
                return first_line
    
    return "[功能描述]"


def generate_imports_section(structure: Dict[str, Any]) -> str:
    """生成导入语句示例"""
    module_path = structure["path"].replace('/', '.').replace('src.', '')
    main_files = [f for f in structure["python_files"] if not f.startswith('test') and f != "__init__.py"]
    
    if not main_files:
        return f"from {module_path} import [主要类名]"
    
    # 尝试找到主要的类
    main_classes = []
    for file in main_files[:3]:  # 只检查前3个文件
        file_path = os.path.join(structure["path"], file)
        info = extract_python_info(file_path)
        main_classes.extend(info["classes"][:2])  # 每个文件最多取2个类
    
    if main_classes:
        classes_str = ", ".join(main_classes[:3])  # 最多显示3个类
        return f"from {module_path} import {classes_str}"
    else:
        return f"from {module_path} import [主要类名]"


def generate_module_doc(module_path: str, module_name: str = None) -> str:
    """生成模块文档"""
    if not module_name:
        module_name = os.path.basename(module_path).replace('_', ' ').title()
    
    structure = scan_directory_structure(module_path)
    directory_tree = generate_directory_tree(structure)
    imports_example = generate_imports_section(structure)
    
    # 生成文档模板
    doc_template = f"""
# {module_name}

这是 AutoCoder 项目中的[模块功能描述]，提供[主要功能说明]。

## 目录结构

```
{directory_tree}
```

## 快速开始（对外API使用指南）

### 基本使用方式

参考相关文件中的使用方式：

```python
{imports_example}

# 1. 初始化配置
# [配置步骤和代码示例]

# 2. 创建实例
# [实例创建代码示例]

# 3. 基本使用
# [基本使用代码示例]
```

### 辅助函数说明

```python
# [函数名1]
def [函数名1]([参数]):
    \"\"\"[函数功能描述]\"\"\"
    # [实现说明]

# [函数名2]  
def [函数名2]([参数]):
    \"\"\"[函数功能描述]\"\"\"
    # [实现说明]
```

### 配置管理

```python
# [配置示例1]
# [配置代码]

# [配置示例2]
# [配置代码]
```

## 核心组件详解

### 1. [主要类名] 主类

**核心功能：**
- [功能1]：[详细描述]
- [功能2]：[详细描述]
- [功能3]：[详细描述]

**主要方法：**
- `[方法1]()`: [方法功能描述]
- `[方法2]()`: [方法功能描述]
- `[方法3]()`: [方法功能描述]

### 2. [子系统名称]架构

**设计模式：**
- [设计模式1]：[描述]
- [设计模式2]：[描述]

#### 2.1 [子系统组件]定义

**[组件类别1]：**

- **`[组件1]`**: [组件描述]
  - **类型**: `[类型名]`
  - **参数**: [参数列表和说明]
  - **功能**: [功能描述]
  - **返回**: [返回值说明]
  - **用途**: [使用场景]
  - **示例**: [使用示例]

#### 2.2 [处理流程]

**[流程名称]：**
```python
# [流程示例代码]
```

**[执行流程]：**
1. **[步骤1]**: [步骤描述]
2. **[步骤2]**: [步骤描述]
3. **[步骤3]**: [步骤描述]

## Mermaid 文件依赖图

```mermaid
graph TB
    %% 核心模块
    MainModule[{module_name.lower().replace(' ', '_')}.py<br/>核心功能]
    SubModule1[子模块1.py<br/>功能描述]
    
    %% 依赖关系
    MainModule --> SubModule1
    
    %% 样式定义
    classDef coreClass fill:#e1f5fe,stroke:#0277bd,stroke-width:2px
    classDef subClass fill:#f3e5f5,stroke:#7b1fa2,stroke-width:1px
    
    class MainModule coreClass
    class SubModule1 subClass
```

### 依赖关系说明

1. **[关系类型1]**：
   - [关系描述]

2. **[关系类型2]**：
   - [关系描述]

这个架构设计确保了模块的高内聚、低耦合，同时提供了良好的扩展性和可维护性。
"""

    return doc_template.strip()


def main():
    parser = argparse.ArgumentParser(description="生成模块文档")
    parser.add_argument("module_path", help="模块路径")
    parser.add_argument("-n", "--name", help="模块名称")
    parser.add_argument("-o", "--output", help="输出文件路径")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.module_path):
        print(f"错误：模块路径 {args.module_path} 不存在")
        sys.exit(1)
    
    # 生成文档
    doc_content = generate_module_doc(args.module_path, args.name)
    
    # 确定输出路径
    if args.output:
        output_path = args.output
    else:
        output_path = os.path.join(args.module_path, ".meta.mod.md")
    
    # 写入文件
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(doc_content)
        print(f"✅ 文档已生成：{output_path}")
        print(f"📝 请根据实际情况完善文档内容")
    except Exception as e:
        print(f"❌ 写入文件失败：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
