import unittest
from pathlib import Path
from typing import List, Dict, Any
from autocoder.common.context_pruner import PruneContext
from autocoder.common import AutoCoderArgs
import byzerllm
from autocoder.utils.llms import get_single_llm
from autocoder.rag.variable_holder import VariableHolder
from tokenizers import Tokenizer    
import pkg_resources
try:
    tokenizer_path = pkg_resources.resource_filename(
        "autocoder", "data/tokenizer.json"
    )
    VariableHolder.TOKENIZER_PATH = tokenizer_path
    VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(tokenizer_path)
except FileNotFoundError:
    tokenizer_path = None
class TestPruneContext(unittest.TestCase):
    def setUp(self):
        self.args = AutoCoderArgs(source_dir=".")
        self.llm = get_single_llm("v3_chat",product_mode="lite")
        self.max_tokens = 1000                
        self.prune_context = PruneContext(self.max_tokens, self.args, self.llm)
        self.test_files = self._create_test_files()

    def tearDown(self):
        for file in self.test_files:
            Path(file).unlink(missing_ok=True)

    def _create_test_files(self) -> List[str]:
        """创建测试文件并返回文件路径列表"""
        files = []
        for i in range(3):
            file_path = f"test_file_{i}.py"
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(f"def test_function_{i}():\n    pass\n")
            files.append(file_path)
        return files

    def test_delete_overflow_files(self):
        """测试删除超出 token 限制的文件"""
        selected_files = self.prune_context.handle_overflow(self.test_files, [], strategy="delete")
        self.assertLessEqual(len(selected_files), len(self.test_files))
        self.assertIsInstance(selected_files, list)
        for file in selected_files:
            self.assertIn(file, self.test_files)

    def test_extract_code_snippets(self):
        """测试抽取关键代码片段策略"""
        conversations = [
            {"role": "user", "content": "如何实现 test_function_0?"}
        ]
        selected_files = self.prune_context.handle_overflow(self.test_files, conversations, strategy="extract")
        self.assertLessEqual(len(selected_files), len(self.test_files))
        self.assertIsInstance(selected_files, list)
        for file in selected_files:
            self.assertIn(file, self.test_files)

    def test_invalid_strategy(self):
        """测试无效策略"""
        with self.assertRaises(ValueError):
            self.prune_context.handle_overflow(self.test_files, [], strategy="invalid")

if __name__ == "__main__":
    unittest.main()
