#!/usr/bin/env python
"""
命令解析器(CommandParser)演示脚本

本脚本演示如何使用 command_parser 模块来解析各种格式的命令字符串。
command_parser 可以处理以下格式的命令：
1. /command arg1 arg2
2. /command key1=value1 key2=value2
3. /command arg1 key1=value1
4. /command1 arg1 /command2 arg2
5. /command1 /command2 arg2
6. /command1 /command2 key=value

此演示将展示如何解析这些命令格式，并提供一些实际应用场景。
"""

import sys
import os

# 导入 command_parser 模块
from autocoder.common.ac_style_command_parser import (
    parse_query,
    has_command,
    get_command_args,
    get_command_kwargs
)


def print_section(title):
    """打印带有分隔线的部分标题"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def demo_basic_parsing():
    """演示基本的命令解析功能"""
    print_section("基本命令解析")
    
    # 示例 1: 单个命令带位置参数
    query = "/open file1.txt file2.txt"
    print(f"查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 命令 'open' 带有两个位置参数 'file1.txt' 和 'file2.txt'")
    
    # 示例 2: 单个命令带键值对参数
    query = "/search keyword=python recursive=true"
    print(f"\n查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 命令 'search' 带有两个键值对参数 'keyword=python' 和 'recursive=true'")
    
    # 示例 3: 单个命令带位置参数和键值对参数
    query = "/download https://example.com/file.zip output=./downloads/"
    print(f"\n查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 命令 'download' 带有一个位置参数 'https://example.com/file.zip' 和一个键值对参数 'output=./downloads/'")


def demo_multiple_commands():
    """演示多命令解析功能"""
    print_section("多命令解析")
    
    # 示例 1: 两个命令各带位置参数
    query = "/learn python java /commit 123456"
    print(f"查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 两个命令 'learn' 和 'commit' 各自带有位置参数")
    
    # 示例 2: 两个命令，第一个没有参数
    query = "/learn /commit 123456"
    print(f"\n查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 命令 'learn' 没有参数，命令 'commit' 带有一个位置参数 '123456'")
    
    # 示例 3: 两个命令，第二个带键值对参数
    query = "/learn python /commit commit_id=123456 message='Fixed bug'"
    print(f"\n查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 命令 'learn' 带有一个位置参数，命令 'commit' 带有两个键值对参数")
    
    # 示例 4: 多个命令混合参数类型
    query = "/fetch origin /merge branch=main /push force=true"
    print(f"\n查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 三个命令分别带有不同类型的参数")


def demo_command_extraction():
    """演示命令提取功能"""
    print_section("命令提取功能")
    
    query = "/learn python java /commit id=123456 message='Bug fix' /push"
    print(f"原始查询: {query}")
    
    # 检查是否包含特定命令
    for cmd in ['learn', 'commit', 'push', 'merge']:
        exists = has_command(query, cmd)
        print(f"查询中{'' if exists else '不'}包含命令 '{cmd}'")
    
    # 获取特定命令的位置参数
    learn_args = get_command_args(query, 'learn')
    print(f"\n'learn' 命令的位置参数: {learn_args}")
    
    # 获取特定命令的键值对参数
    commit_kwargs = get_command_kwargs(query, 'commit')
    print(f"'commit' 命令的键值对参数: {commit_kwargs}")
    
    # 尝试获取不存在的命令参数
    merge_args = get_command_args(query, 'merge')
    print(f"'merge' 命令的位置参数: {merge_args} (命令不存在，返回空列表)")


def demo_quoted_values():
    """演示带引号值的解析功能"""
    print_section("带引号值的解析")
    
    # 示例 1: 双引号包含空格的值
    query = '/search keyword="python programming" case=sensitive'
    print(f"查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 命令 'search' 带有键值对参数，其中 'keyword' 的值包含空格，用双引号包围")
    
    # 示例 2: 单引号包含空格的值
    query = "/commit message='Fixed bug in login module'"
    print(f"\n查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 命令 'commit' 带有键值对参数，其中 'message' 的值包含空格，用单引号包围")
    
    # 示例 3: 位置参数中使用引号
    query = '/copy "source file.txt" "destination file.txt"'
    print(f"\n查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 命令 'copy' 带有两个位置参数，都包含空格，用双引号包围")
    
    # 示例 4: 混合使用引号和普通参数
    query = '/generate type=report title="Monthly Sales" format=pdf pages=10'
    print(f"\n查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 命令 'generate' 带有多个键值对参数，其中 'title' 的值包含空格，用双引号包围")

    # 示例 5: 多命令混合使用引号
    query = '/find name="*.py" /count /save path="output files/report.txt"'
    print(f"\n查询: {query}")
    result = parse_query(query)
    print(f"解析结果: {result}")
    print("解析说明: 多个命令，部分参数值包含空格，用双引号包围")


def demo_practical_application():
    """演示实际应用场景"""
    print_section("实际应用场景")
    
    # 场景 1: Git 类操作
    query = "/fetch origin /merge branch=feature skip-ci=true /push force=true"
    print(f"Git 操作场景: {query}")
    
    commands = parse_query(query)
    
    # 处理 fetch 命令
    if 'fetch' in commands:
        fetch_args = get_command_args(query, 'fetch')
        remote = fetch_args[0] if fetch_args else 'origin'
        print(f"执行: git fetch {remote}")
    
    # 处理 merge 命令
    if 'merge' in commands:
        merge_kwargs = get_command_kwargs(query, 'merge')
        branch = merge_kwargs.get('branch', 'master')
        skip_ci = merge_kwargs.get('skip-ci', 'false')
        skip_ci_flag = '--no-verify' if skip_ci == 'true' else ''
        print(f"执行: git merge {branch} {skip_ci_flag}")
    
    # 处理 push 命令
    if 'push' in commands:
        push_kwargs = get_command_kwargs(query, 'push')
        force = '--force' if push_kwargs.get('force') == 'true' else ''
        print(f"执行: git push {force}")
    
    # 场景 2: 文件操作
    print("\n文件操作场景:")
    query = "/find name=*.py recursive=true /count lines=true /save output=report.txt"
    print(query)
    
    commands = parse_query(query)
    
    # 处理查找命令
    if 'find' in commands:
        find_kwargs = get_command_kwargs(query, 'find')
        pattern = find_kwargs.get('name', '*')
        recursive = 'true' == find_kwargs.get('recursive', 'false')
        print(f"查找文件: {pattern} {'(包含子目录)' if recursive else '(仅当前目录)'}")
        
        # 模拟查找结果
        files = ['file1.py', 'file2.py', 'subdir/file3.py']
        
        # 如果有计数命令
        if 'count' in commands:
            count_kwargs = get_command_kwargs(query, 'count')
            count_lines = 'true' == count_kwargs.get('lines', 'false')
            
            if count_lines:
                print(f"计算行数: 总共发现 {len(files)} 个文件，150 行代码")
                
            # 如果有保存命令
            if 'save' in commands:
                save_kwargs = get_command_kwargs(query, 'save')
                output = save_kwargs.get('output', 'output.txt')
                print(f"保存结果到: {output}")


def main():
    """主函数，运行所有演示"""
    print("命令解析器(CommandParser)演示")
    print("此脚本展示如何使用 command_parser 模块解析各种格式的命令")

    query = "/rag /wow file1.txt file2.txt"
    print(f"查询: {query}")
    commands_infos = parse_query(query)
    print(f"解析结果: {commands_infos}")

    temp_query = ""
    for (command,command_info) in commands_infos.items():
        if command_info["args"]:
            temp_query = " ".join(command_info["args"])
            # 删除break，使循环继续，这样最后一个有args的command会覆盖之前的            
    query = temp_query
    print(f"最终查询: {query}")

    query = "file1.txt file2.txt"
    print(f"查询: {query}")
    commands_infos = parse_query(query)
    print(f"解析结果: {commands_infos}")

    temp_query = ""
    for (command,command_info) in commands_infos.items():
        if command_info["args"]:
            temp_query = " ".join(command_info["args"])
            # 删除break，使循环继续，这样最后一个有args的command会覆盖之前的            
    query = temp_query
    print(f"最终查询: {query}")


    query = "/chat /rag"
    print(f"查询: {query}")
    commands_infos = parse_query(query)
    print(f"解析结果: {commands_infos}")

    temp_query = ""
    for (command,command_info) in commands_infos.items():
        if command_info["args"]:
            temp_query = " ".join(command_info["args"])
            # 删除break，使循环继续，这样最后一个有args的command会覆盖之前的            
    query = temp_query
    print(f"最终查询: {query}")
    # demo_basic_parsing()
    # demo_multiple_commands()
    # demo_command_extraction()
    # demo_quoted_values()
    # demo_practical_application()    
    # print("\n" + "=" * 80)
    print("演示结束！")

    print(parse_query('/save "/tmp/test.txt'))


if __name__ == "__main__":
    main() 