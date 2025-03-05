from pathlib import Path
from typing import List, Dict, Any
from autocoder.common.context_pruner import PruneContext
from autocoder.common import AutoCoderArgs
import byzerllm
from autocoder.utils.llms import get_single_llm
from autocoder.rag.variable_holder import VariableHolder
from tokenizers import Tokenizer    
import pkg_resources
import os
from autocoder.common import SourceCode
from autocoder.rag.token_counter import count_tokens

try:
    tokenizer_path = pkg_resources.resource_filename(
        "autocoder", "data/tokenizer.json"
    )
    VariableHolder.TOKENIZER_PATH = tokenizer_path
    VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(tokenizer_path)
except FileNotFoundError:
    tokenizer_path = None

def create_large_test_file() -> str:
    """创建一个包含多个函数的大文件用于测试"""
    file_path = "large_file.py"
    content = """
class Calculator:
    def __init__(self):
        self.history = []
        
    def add(self, a: int, b: int) -> int:
        '''加法函数'''
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
        
    def subtract(self, a: int, b: int) -> int:
        '''减法函数'''
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        return result
        
    def multiply(self, a: int, b: int) -> int:
        '''乘法函数'''
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
        
    def divide(self, a: int, b: int) -> float:
        '''除法函数'''
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result
        
    def get_history(self) -> List[str]:
        '''获取计算历史'''
        return self.history
        
    def clear_history(self):
        '''清除历史记录'''
        self.history = []
        
    def power(self, a: int, b: int) -> int:
        '''幂运算'''
        result = a ** b
        self.history.append(f"{a} ** {b} = {result}")
        return result
        
    def factorial(self, n: int) -> int:
        '''阶乘计算'''
        if n < 0:
            raise ValueError("Factorial not defined for negative numbers")
        if n == 0:
            return 1
        result = 1
        for i in range(1, n + 1):
            result *= i
        self.history.append(f"{n}! = {result}")
        return result
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return os.path.abspath(file_path)

def file_path_to_source_code(file_path: str) -> SourceCode:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return SourceCode(module_name=file_path, source_code=content, tokens=count_tokens(content))

def test_extract_large_file():
    """测试从大文件中抽取相关代码片段的功能"""
    # 创建测试文件
    large_file_path = create_large_test_file()
    
    # 配置参数
    args = AutoCoderArgs(
        source_dir=".",
        context_prune=True,
        context_prune_strategy="extract",
        conversation_prune_safe_zone_tokens=400,  # 设置较小的token限制以触发抽取逻辑
        context_prune_sliding_window_size=10,
        context_prune_sliding_window_overlap=2,
        query="如何实现加法和减法运算？"
    )

    # 获取LLM实例
    llm = get_single_llm("v3_chat", product_mode="lite")

    # 创建PruneContext实例
    context_pruner = PruneContext(
        max_tokens=args.conversation_prune_safe_zone_tokens, 
        args=args, 
        llm=llm
    )

    # 模拟对话历史
    conversations = [
        {"role": "user", "content": "这个计算器怎么用？"},
        {"role": "assistant", "content": "这是一个基本的计算器类，提供了各种数学运算功能。"},
        {"role": "user", "content": "如何实现加法和减法运算？"}
    ]

    # 处理文件
    pruned_files = context_pruner.handle_overflow(
        [file_path_to_source_code(large_file_path)],
        conversations,
        args.context_prune_strategy
    )

    # 打印结果
    print("\n=== 测试结果 ===")
    print(f"原始文件路径: {large_file_path}")
    print("\n提取后的代码片段:")
    for file in pruned_files:
        print(f"\n文件: {file.module_name}")
        print(f"Token数量: {file.tokens}")
        print("代码内容:")
        print(file.source_code)

    # 清理测试文件
    os.remove(large_file_path)

def test_extract_with_sliding_window():
    """测试使用滑动窗口处理超大文件的功能"""
    # 创建一个更大的测试文件
    file_path = "very_large_file.py"
    
    # 生成大量重复的代码来模拟超大文件
    content = "class VeryLargeCalculator:\n"
    for i in range(100):  # 生成100个方法来创建一个大文件
        content += f"""
    def operation_{i}(self, a: int, b: int) -> int:
        '''Operation {i}'''
        result = a + b * {i}
        return result
            
"""
    content += """
    def add(self, a: int, b: int) -> int:
            '''加法'''
            return a + b
"""
    
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    file_path = os.path.abspath(file_path)
    file_source = file_path_to_source_code(file_path)
    # 配置参数
    args = AutoCoderArgs(
        source_dir=".",
        context_prune=True,
        context_prune_strategy="extract",
        conversation_prune_safe_zone_tokens=200,  # 设置较小的token限制
        query="找到所有包含加法的操作"
    )

    # 获取LLM实例
    llm = get_single_llm("v3_chat", product_mode="lite")

    # 创建PruneContext实例
    context_pruner = PruneContext(
        max_tokens=args.conversation_prune_safe_zone_tokens, 
        args=args, 
        llm=llm
    )

    # 模拟对话历史
    conversations = [
        {"role": "user", "content": "这个计算器里有哪些操作？"},
        {"role": "assistant", "content": "这是一个包含多个数学运算的大型计算器类。"},
        {"role": "user", "content": "找到所有包含加法的操作"}
    ]

    # 处理文件
    pruned_files = context_pruner.handle_overflow(
        [file_source],
        conversations,
        args.context_prune_strategy
    )

    # 打印结果
    print("\n=== 滑动窗口测试结果 ===")
    print(f"原始文件路径: {file_path}")
    print("\n提取后的代码片段:")
    for file in pruned_files:
        print(f"\n文件: {file.module_name}")
        print(f"Token数量: {file.tokens}")
        print("代码内容:")
        print(file.source_code)

    # 清理测试文件
    os.remove(file_path)

if __name__ == "__main__":
    print("测试1: 提取相关代码片段")
    test_extract_large_file()
    
    print("\n测试2: 滑动窗口处理超大文件")
    test_extract_with_sliding_window()