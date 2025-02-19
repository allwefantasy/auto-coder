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
    for i in range(3):
        file_path = f"test_file_{i}.py"
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"def test_function_{i}():\n    pass\n")
        files.append(os.path.abspath(file_path))
    return files

def main():
    args = AutoCoderArgs(source_dir=".")
    llm = get_single_llm("v3_chat", product_mode="lite")
    max_tokens = 50
    prune_context = PruneContext(max_tokens, args, llm)
    test_files = create_test_files()

    print("测试删除超出 token 限制的文件:")
    selected_files = prune_context.handle_overflow(test_files, [], strategy="delete")
    print(f"处理后的文件列表: {selected_files}")
    print("=" * 50)

    print("测试抽取关键代码片段策略:")
    conversations = [
        {"role": "user", "content": "如何实现 test_function_0?"}
    ]
    selected_files = prune_context.handle_overflow(test_files, conversations, strategy="extract")
    print(f"处理后的文件列表: {selected_files}")
    print("=" * 50)

    print("测试无效策略:")
    try:
        prune_context.handle_overflow(test_files, [], strategy="invalid")
    except ValueError as e:
        print(f"捕获到预期错误: {e}")
    print("=" * 50)

    # 清理测试文件
    for file in test_files:
        Path(file).unlink(missing_ok=True)

if __name__ == "__main__":
    main()
