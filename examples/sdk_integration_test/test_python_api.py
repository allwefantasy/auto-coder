#!/usr/bin/env python3
"""
Python API 测试脚本

测试 Auto-Coder SDK 的 Python API 功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from autocoder.sdk import query, query_sync, modify_code, modify_code_stream, AutoCodeOptions

def test_sync_query():
    """测试同步查询"""
    print("=== 测试同步查询 ===")
    
    options = AutoCodeOptions(
        cwd=str(Path(__file__).parent),
        max_turns=3,
        model="gpt-4",
        verbose=True
    )
    
    try:
        response = query_sync("Write a docstring for the hello_world function", options)
        print(f"响应: {response}")
        print("✅ 同步查询测试通过")
    except Exception as e:
        print(f"❌ 同步查询测试失败: {e}")

async def test_async_query():
    """测试异步查询"""
    print("\n=== 测试异步查询 ===")
    
    options = AutoCodeOptions(
        cwd=str(Path(__file__).parent),
        max_turns=2,
        temperature=0.7
    )
    
    try:
        async for message in query("Explain how the fibonacci function works", options):
            print(f"[{message.role}] {message.content[:100]}...")
        print("✅ 异步查询测试通过")
    except Exception as e:
        print(f"❌ 异步查询测试失败: {e}")

def test_modify_code():
    """测试代码修改"""
    print("\n=== 测试代码修改 ===")
    
    options = AutoCodeOptions(
        cwd=str(Path(__file__).parent),
        max_turns=3
    )
    
    try:
        result = modify_code(
            "Add error handling to the calculate_sum function",
            pre_commit=False,
            options=options
        )
        
        print(f"修改成功: {result.success}")
        print(f"消息: {result.message}")
        print(f"修改的文件: {result.modified_files}")
        
        if result.success:
            print("✅ 代码修改测试通过")
        else:
            print(f"❌ 代码修改测试失败: {result.error_details}")
    except Exception as e:
        print(f"❌ 代码修改测试失败: {e}")

async def test_modify_code_stream():
    """测试流式代码修改"""
    print("\n=== 测试流式代码修改 ===")
    
    options = AutoCodeOptions(
        cwd=str(Path(__file__).parent),
        max_turns=2
    )
    
    try:
        async for event in modify_code_stream(
            "Add type hints to all functions",
            pre_commit=False,
            options=options
        ):
            print(f"[{event.event_type}] {event.data}")
        print("✅ 流式代码修改测试通过")
    except Exception as e:
        print(f"❌ 流式代码修改测试失败: {e}")

async def main():
    """主测试函数"""
    print("开始 Auto-Coder SDK Python API 测试\n")
    
    # 测试同步API
    test_sync_query()
    
    # 测试异步API
    await test_async_query()
    
    # 测试代码修改
    test_modify_code()
    
    # 测试流式代码修改
    await test_modify_code_stream()
    
    print("\n测试完成!")

if __name__ == "__main__":
    asyncio.run(main()) 