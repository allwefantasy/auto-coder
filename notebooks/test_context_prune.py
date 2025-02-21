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

try:
    tokenizer_path = pkg_resources.resource_filename(
        "autocoder", "data/tokenizer.json"
    )
    VariableHolder.TOKENIZER_PATH = tokenizer_path
    VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(tokenizer_path)
except FileNotFoundError:
    tokenizer_path = None


def create_test_files() -> List[str]:
    """创建测试文件并返回文件路径列表"""
    files = []
    for i in range(4):
        file_path = f"file{i}.py"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"def test_function_{i}():\n    pass\n")
        files.append(os.path.abspath(file_path))
    return files

def test_context_prune():
    create_test_files()
    # 模拟 AutoCoderArgs
    args = AutoCoderArgs(
        source_dir=".",
        context_prune=True,
        context_prune_strategy="extract",
        conversation_prune_safe_zone_tokens=30,
        query="Test query"
    )

    # 模拟 LLM    
    llm = get_single_llm("v3_chat", product_mode="lite")

    # 模拟文件内容和位置
    file_positions = {
        "file2.py": 2,
        "file1.py": 1,        
        "file3.py": 3
    }

    # 模拟 temp_sources
    temp_sources = [
        SourceCode(module_name="file3.py", source_code="def func3(): pass", tokens=300),
        SourceCode(module_name="file1.py", source_code="def func1(): pass", tokens=200),
        SourceCode(module_name="file2.py", source_code="def func2(): pass", tokens=500)
    ]

    # 创建 PruneContext 实例
    context_pruner = PruneContext(max_tokens=args.conversation_prune_safe_zone_tokens, args=args, llm=llm)

    # 如果 file_positions 不为空，则通过 file_positions 来获取文件
    if file_positions:
        # 将 file_positions 转换为 [(pos, file_path)] 的列表
        position_file_pairs = [(pos, file_path) for file_path, pos in file_positions.items()]
        # 按位置排序
        position_file_pairs.sort(key=lambda x: x[0])
        # 提取排序后的文件路径列表
        sorted_file_paths = [file_path for _, file_path in position_file_pairs]
        # 根据 sorted_file_paths 重新排序 temp_sources
        temp_sources.sort(key=lambda x: sorted_file_paths.index(x.module_name) if x.module_name in sorted_file_paths else len(sorted_file_paths))
    print(temp_sources)
    # 处理文件
    pruned_files = context_pruner.handle_overflow(
        [source.module_name for source in temp_sources],
        [{"role": "user", "content": args.query}],
        args.context_prune_strategy
    )

    # 打印结果
    print("Pruned files:")
    for file in pruned_files:
        print(f"File: {file.module_name}, Tokens: {file.tokens} , {file.source_code}")

if __name__ == "__main__":
    test_context_prune()
