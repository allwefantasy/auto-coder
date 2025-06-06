#!/usr/bin/env python3
"""
UseRAGTool 和 UseRAGToolResolver 测试脚本

这个脚本用于测试新实现的 UseRAGTool 和 UseRAGToolResolver 类。
"""

import sys
import os

from autocoder.common.v2.agent.agentic_edit_types import UseRAGTool, ToolResult
from autocoder.common.v2.agent.agentic_edit_tools.use_rag_tool_resolver import UseRAGToolResolver
from autocoder.common import AutoCoderArgs

def test_use_rag_tool():
    """测试 UseRAGTool 和 UseRAGToolResolver"""
    
    print("=== UseRAGTool 测试 ===")
    
    # 创建测试用的 AutoCoderArgs
    args = AutoCoderArgs(
        source_dir=".",
        model="qwen-max",
        inference_model="qwen-max"
    )
    
    # 创建 UseRAGTool 实例
    rag_tool = UseRAGTool(
        server_name="http://localhost:8109/v1",
        query="moonbit 如何进行测试"
    )
    
    print(f"创建的 UseRAGTool: {rag_tool}")
    print(f"Server Name: {rag_tool.server_name}")
    print(f"Query: {rag_tool.query}")
    
    # 创建 UseRAGToolResolver 实例
    resolver = UseRAGToolResolver(
        agent=None,  # 在测试中可以传入 None
        tool=rag_tool,
        args=args
    )
    
    print(f"\n创建的 UseRAGToolResolver: {resolver}")
    print(f"Resolver tool type: {type(resolver.tool)}")        
    
    try:
        result = resolver.resolve()
        print(f"执行结果: {result.content}")
    except Exception as e:
        print(f"预期的错误 (没有真实 RAG server): {type(e).__name__}: {e}")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    test_use_rag_tool() 