#!/usr/bin/env python
"""
测试 tokens 模块的功能
"""

import os
import sys
from pathlib import Path

# 确保能够导入 autocoder 模块
sys.path.append(os.path.abspath(os.path.dirname(__file__)))

# 导入 load_tokenizer 函数并初始化 tokenizer
from autocoder.auto_coder_runner import load_tokenizer
load_tokenizer()

# 导入 tokens 模块
from autocoder.common.tokens import (
    TokenCounter,
    count_file_tokens,
    count_directory_tokens
)


def test_single_file():
    """测试单个文件的 token 统计"""
    print("\n=== 测试单个文件 token 统计 ===")
    # 使用当前脚本作为测试文件
    file_path = __file__
    result = count_file_tokens(file_path)
    
    print(f"文件: {result.file_path}")
    print(f"Token 数量: {result.token_count}")
    print(f"字符数: {result.char_count}")
    print(f"行数: {result.line_count}")
    print(f"成功: {result.success}")
    
    assert result.success, f"文件统计失败: {result.error}"
    assert result.token_count > 0, "Token 数量应该大于 0"
    assert result.char_count > 0, "字符数应该大于 0"
    assert result.line_count > 0, "行数应该大于 0"
    
    return result


def test_directory():
    """测试目录的 token 统计"""
    print("\n=== 测试目录 token 统计 ===")
    # 使用 tokens 模块目录作为测试目录
    dir_path = os.path.join("src", "autocoder", "common", "tokens")
    result = count_directory_tokens(
        dir_path,
        pattern=r".*\.py$"  # 只统计 Python 文件
    )
    
    print(f"目录: {result.directory_path}")
    print(f"总 Token 数: {result.total_tokens}")
    print(f"文件数量: {result.file_count}")
    print(f"跳过文件数: {result.skipped_count}")
    
    if result.errors:
        print("\n错误:")
        for error in result.errors:
            print(f"- {error}")
    
    assert result.file_count > 0, "应该至少找到一个文件"
    assert result.total_tokens > 0, "总 Token 数应该大于 0"
    
    return result


def test_token_counter():
    """测试 TokenCounter 类"""
    print("\n=== 测试 TokenCounter 类 ===")
    counter = TokenCounter(parallel=True, max_workers=2)
    
    # 测试批量处理
    files = [
        __file__,
        os.path.join("src", "autocoder", "common", "tokens", "__init__.py"),
        os.path.join("src", "autocoder", "common", "tokens", "counter.py"),
        "non_existent_file.txt"  # 测试不存在的文件
    ]
    
    results = counter.count_files(files)
    
    print(f"处理文件数: {len(results)}")
    for result in results:
        if result.success:
            print(f"{result.file_path}: {result.token_count} tokens, {result.line_count} 行")
        else:
            print(f"{result.file_path}: 失败 - {result.error}")
    
    return results


if __name__ == "__main__":
    print("开始测试 tokens 模块...")
    
    try:
        file_result = test_single_file()
        dir_result = test_directory()
        counter_results = test_token_counter()
        
        print("\n✅ 所有测试通过!")
        print(f"总计统计了 {len(counter_results)} 个文件，共 {sum(r.token_count for r in counter_results if r.success)} tokens")
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
        sys.exit(1)
