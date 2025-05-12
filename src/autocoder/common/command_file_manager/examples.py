"""
命令管理模块的使用示例

展示如何使用命令管理模块的主要功能。
"""

import os
import sys
import json
from typing import Dict, Set, List

from autocoder.common.command_manager import (
    CommandManager, CommandFile, JinjaVariable, CommandFileAnalysisResult
)


def setup_test_environment():
    """设置测试环境，创建示例命令文件"""
    # 创建临时命令目录
    test_dir = os.path.join(os.path.dirname(__file__), "test_commands")
    os.makedirs(test_dir, exist_ok=True)
    
    # 创建示例命令文件
    example1 = os.path.join(test_dir, "example1.autocodercommand")
    with open(example1, "w") as f:
        f.write("""
{# @var: project_name, default: MyProject, description: 项目名称 #}
{# @var: author, default: User, description: 作者姓名 #}
# {{ project_name }}

这是一个由 {{ author }} 创建的项目。

{% if include_license %}
## 许可证
本项目使用 {{ license_type }} 许可证。
{% endif %}
        """)
    
    # 创建子目录和另一个示例文件
    sub_dir = os.path.join(test_dir, "subdir")
    os.makedirs(sub_dir, exist_ok=True)
    
    example2 = os.path.join(sub_dir, "example2.j2")
    with open(example2, "w") as f:
        f.write("""
# {{ project_name }} 配置

version: {{ version }}
environment: {{ env }}
        """)
    
    return test_dir


def list_command_files_example(manager: CommandManager):
    """列出命令文件示例"""
    print("\n=== 列出命令文件 ===")
    
    # 不递归列出
    print("不递归列出:")
    result = manager.list_command_files(recursive=False)
    if result.success:
        for file in result.command_files:
            print(f"- {file}")
    else:
        print(f"错误: {result.errors}")
    
    # 递归列出
    print("\n递归列出:")
    result = manager.list_command_files(recursive=True)
    if result.success:
        for file in result.command_files:
            print(f"- {file}")
    else:
        print(f"错误: {result.errors}")


def read_command_file_example(manager: CommandManager):
    """读取命令文件示例"""
    print("\n=== 读取命令文件 ===")
    
    # 读取第一个示例文件
    command_file = manager.read_command_file("example1.autocodercommand")
    if command_file:
        print(f"文件名: {command_file.file_name}")
        print(f"文件路径: {command_file.file_path}")
        print("文件内容:")
        print(command_file.content)
    else:
        print("文件不存在或读取失败")


def analyze_command_file_example(manager: CommandManager):
    """分析命令文件示例"""
    print("\n=== 分析命令文件 ===")
    
    # 分析第一个示例文件
    analysis = manager.analyze_command_file("example1.autocodercommand")
    if analysis:
        print(f"文件名: {analysis.file_name}")
        print(f"原始变量: {', '.join(analysis.raw_variables)}")
        print("变量详情:")
        for var in analysis.variables:
            print(f"  - {var.name}")
            if var.default_value:
                print(f"    默认值: {var.default_value}")
            if var.description:
                print(f"    描述: {var.description}")
    else:
        print("文件分析失败")


def get_all_variables_example(manager: CommandManager):
    """获取所有变量示例"""
    print("\n=== 获取所有变量 ===")
    
    # 获取所有命令文件中的变量
    variables_map = manager.get_all_variables(recursive=True)
    for file, variables in variables_map.items():
        print(f"文件: {file}")
        print(f"变量: {', '.join(variables)}")
        print()


def main():
    """主函数"""
    # 设置测试环境
    test_dir = setup_test_environment()
    print(f"测试目录: {test_dir}")
    
    # 创建命令管理器
    manager = CommandManager(test_dir)
    
    # 运行示例
    list_command_files_example(manager)
    read_command_file_example(manager)
    analyze_command_file_example(manager)
    get_all_variables_example(manager)


if __name__ == "__main__":
    main()
