#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 openai_content.py 中的 process_conversations 函数
"""

import sys
import os
import pprint

# 添加项目根目录到 Python 路径，使得可以导入 src 目录下的模块
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.autocoder.common.openai_content import process_conversations, ContentType

# 用于美化输出的函数
def print_test_case(title, input_data, output_data):
    print("\n" + "=" * 80)
    print(f"测试用例: {title}")
    print("-" * 80)
    print("输入:")
    pprint.pprint(input_data)
    print("-" * 80)
    print("输出:")
    pprint.pprint(output_data)
    print("=" * 80)

def run_tests():
    # 测试用例 1: 基本字符串内容
    test_case_1 = [
        {"role": "user", "content": "Hello there"},
        {"role": "assistant", "content": "Hi, how can I help you?"}
    ]
    result_1 = process_conversations(test_case_1)
    print_test_case("基本字符串内容", test_case_1, result_1)
    
    # 测试用例 2: 结构化内容 - 仅文本
    test_case_2 = [
        {"role": "user", "content": [
            {"type": "text", "text": "First text message"},
            {"type": "text", "text": "Second text message"}
        ]}
    ]
    result_2 = process_conversations(test_case_2)
    print_test_case("结构化内容 - 仅文本", test_case_2, result_2)
    
    # 测试用例 3: 结构化内容 - 混合文本和图片
    test_case_3 = [
        {"role": "user", "content": [
            {"type": "text", "text": "What's in this image?"},
            {"type": "image_url", "image_url": "data:image/jpeg;base64,abc123"}
        ]}
    ]
    result_3 = process_conversations(test_case_3)
    print_test_case("结构化内容 - 混合文本和图片", test_case_3, result_3)
    
    # 测试用例 4: 复杂场景 - 混合普通文本和结构化内容的会话
    test_case_4 = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi, how can I help?"},
        {"role": "user", "content": [
            {"type": "text", "text": "Look at this image"},
            {"type": "image_url", "image_url": "data:image/jpeg;base64,abc123"},
            {"type": "text", "text": "What do you see?"}
        ]}
    ]
    result_4 = process_conversations(test_case_4)
    print_test_case("复杂场景 - 混合普通文本和结构化内容的会话", test_case_4, result_4)
    
    # 测试用例 5: 空内容
    test_case_5 = [
        {"role": "user", "content": ""},
        {"role": "assistant", "content": None}
    ]
    result_5 = process_conversations(test_case_5)
    print_test_case("空内容", test_case_5, result_5)
    
    # 测试用例 6: 没有content字段
    test_case_6 = [
        {"role": "user"}
    ]
    result_6 = process_conversations(test_case_6)
    print_test_case("没有content字段", test_case_6, result_6)
    
    # 测试用例 7: 带有name字段
    test_case_7 = [
        {"role": "user", "name": "Alice", "content": "Hello"},
        {"role": "assistant", "content": "Hi Alice!"}
    ]
    result_7 = process_conversations(test_case_7)
    print_test_case("带有name字段", test_case_7, result_7)
    
    # 测试用例 8: 非字符串非结构化内容
    test_case_8 = [
        {"role": "user", "content": 12345},
        {"role": "user", "content": True},
        {"role": "user", "content": ["item1", "item2"]},  # 不是有效的结构化内容
    ]
    result_8 = process_conversations(test_case_8)
    print_test_case("非字符串非结构化内容", test_case_8, result_8)
    
    # 测试用例 9: 复杂嵌套的结构化内容
    test_case_9 = [
        {"role": "user", "content": [
            {"type": "text", "text": "First paragraph"},
            {"type": "image_url", "image_url": "data:image/jpeg;base64,abc123"},
            {"type": "text", "text": "Second paragraph"},
            {"type": "text", "text": "Third paragraph"},
            {"type": "image_url", "image_url": "https://example.com/image.jpg"}
        ]}
    ]
    result_9 = process_conversations(test_case_9)
    print_test_case("复杂嵌套的结构化内容", test_case_9, result_9)

if __name__ == "__main__":
    print("开始测试 process_conversations 函数...\n")
    run_tests()
    print("\n测试完成!") 