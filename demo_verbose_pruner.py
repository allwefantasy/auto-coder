#!/usr/bin/env python3
"""
演示 PruneContext 的 verbose 功能
"""

from autocoder.common.pruner.context_pruner import PruneContext
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.sdk import get_llm
from autocoder.common.tokens import count_string_tokens

def main():
    print("=" * 80)
    print("🔍 PruneContext Verbose 功能演示")
    print("=" * 80)
    
    # 创建测试数据
    file1_content = '''def add(a, b):
    """加法函数"""
    return a + b

def subtract(a, b):
    """减法函数"""
    return a - b

def multiply(a, b):
    """乘法函数"""
    return a * b
'''

    file2_content = '''def format_string(s):
    """格式化字符串"""
    return s.strip().lower()

def reverse_string(s):
    """反转字符串"""
    return s[::-1]
'''

    file_sources = [
        SourceCode(
            module_name="math_utils.py",
            source_code=file1_content,
            tokens=count_string_tokens(file1_content)
        ),
        SourceCode(
            module_name="string_utils.py", 
            source_code=file2_content,
            tokens=count_string_tokens(file2_content)
        )
    ]
    
    conversations = [
        {"role": "user", "content": "如何实现加法和减法运算？"}
    ]
    
    # 创建参数
    args = AutoCoderArgs(
        source_dir=".",
        context_prune=True,
        context_prune_strategy="extract",
        context_prune_sliding_window_size=10,
        context_prune_sliding_window_overlap=2,
        query="如何实现加法和减法运算？"
    )
    
    # 获取 LLM
    llm = get_llm("v3_chat", product_mode="lite")
    
    print("\n🔇 非 Verbose 模式:")
    print("-" * 40)
    
    # 创建非 verbose 的 pruner
    pruner_normal = PruneContext(max_tokens=50, args=args, llm=llm, verbose=False)
    result_normal = pruner_normal._extract_code_snippets(file_sources, conversations)
    
    print(f"处理完成，返回 {len(result_normal)} 个文件")
    
    print("\n🔊 Verbose 模式:")
    print("-" * 40)
    
    # 创建 verbose 的 pruner
    pruner_verbose = PruneContext(max_tokens=50, args=args, llm=llm, verbose=True)
    result_verbose = pruner_verbose._extract_code_snippets(file_sources, conversations)
    
    print(f"\n处理完成，返回 {len(result_verbose)} 个文件")
    
    print("\n" + "=" * 80)
    print("✅ 演示完成！")
    print("=" * 80)

if __name__ == "__main__":
    main()
