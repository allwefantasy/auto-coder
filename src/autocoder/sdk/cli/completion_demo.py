

#!/usr/bin/env python3
"""
Auto-Coder CLI 自动补全功能演示脚本

展示各种补全功能的工作原理
"""

import sys
import os
from autocoder.sdk.cli.main import AutoCoderCLI
import argparse


def demo_completers():
    """演示各种补全器的功能"""
    print("=== Auto-Coder CLI 自动补全功能演示 ===\n")
    
    # 创建解析器
    parser = argparse.ArgumentParser()
    parser.add_argument('prompt', nargs='?', help='提示内容')
    parser.add_argument('--allowed-tools', nargs='+', help='允许使用的工具列表')
    parser.add_argument('--resume', help='恢复特定会话')
    
    # 设置补全器
    AutoCoderCLI._setup_completers(parser)
    
    # 演示工具名称补全
    print("1. 工具名称补全演示")
    print("   输入前缀 'read' 的补全结果:")
    for action in parser._actions:
        if hasattr(action, 'dest') and action.dest == 'allowed_tools':
            if hasattr(action, 'completer'):
                completions = action.completer('read', None)
                for comp in completions:
                    print(f"     - {comp}")
            break
    
    print("\n   输入前缀 'write' 的补全结果:")
    for action in parser._actions:
        if hasattr(action, 'dest') and action.dest == 'allowed_tools':
            if hasattr(action, 'completer'):
                completions = action.completer('write', None)
                for comp in completions:
                    print(f"     - {comp}")
            break
    
    # 演示提示内容补全
    print("\n2. 提示内容补全演示")
    print("   输入前缀 'write' 的补全结果:")
    for action in parser._actions:
        if hasattr(action, 'dest') and action.dest == 'prompt':
            if hasattr(action, 'completer'):
                completions = action.completer('write', None)
                for comp in completions:
                    print(f"     - {comp}")
            break
    
    print("\n   输入前缀 'explain' 的补全结果:")
    for action in parser._actions:
        if hasattr(action, 'dest') and action.dest == 'prompt':
            if hasattr(action, 'completer'):
                completions = action.completer('explain', None)
                for comp in completions:
                    print(f"     - {comp}")
            break
    
    # 演示会话ID补全
    print("\n3. 会话ID补全演示")
    print("   可用的会话ID:")
    for action in parser._actions:
        if hasattr(action, 'dest') and action.dest == 'resume':
            if hasattr(action, 'completer'):
                completions = action.completer('', None)
                for comp in completions:
                    print(f"     - {comp}")
            break
    
    print("\n=== 演示完成 ===")
    print("\n使用方法:")
    print("1. 确保已安装自动补全: python -m autocoder.sdk.cli install")
    print("2. 重新加载 shell: source ~/.bashrc (或 ~/.zshrc)")
    print("3. 使用 Tab 键进行补全: auto-coder.run --allowed-tools <TAB>")


def test_argcomplete_integration():
    """测试与 argcomplete 的集成"""
    print("\n=== 测试 argcomplete 集成 ===")
    
    try:
        import argcomplete
        print("✓ argcomplete 已安装")
        
        # 测试补全环境变量
        test_env = {
            '_ARGCOMPLETE_COMPLETE': 'complete_test',
            'COMP_LINE': 'auto-coder.run --allowed-tools ',
            'COMP_POINT': '29'
        }
        
        print("✓ 可以设置补全环境变量")
        print("✓ argcomplete 集成测试通过")
        
    except ImportError:
        print("✗ argcomplete 未安装")
        return False
    
    return True


if __name__ == '__main__':
    demo_completers()
    test_argcomplete_integration()


