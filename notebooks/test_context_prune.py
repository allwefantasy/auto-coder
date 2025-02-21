import os
import sys
import json
from typing import List, Dict, Any
from unittest import TestCase, mock
from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.index.entry import build_index_and_filter_files
from autocoder.common.context_pruner import PruneContext
from byzerllm import ByzerLLM

class TestContextPrune(TestCase):
    def setUp(self):
        self.llm = ByzerLLM()
        self.args = AutoCoderArgs(
            context_prune=True,
            conversation_prune_safe_zone_tokens=1000,
            context_prune_strategy="extract",
            query="Test query",
            request_id="test_request_id",
            skip_events=True
        )
        self.sources = [
            SourceCode(module_name="file1.py", source_code="def foo():\n    pass", tag="PY"),
            SourceCode(module_name="file2.py", source_code="def bar():\n    pass", tag="PY"),
            SourceCode(module_name="file3.py", source_code="def baz():\n    pass", tag="PY"),
        ]

    def test_context_prune_with_file_positions(self):
        file_positions = {
            "file1.py": 1,
            "file2.py": 2,
            "file3.py": 3
        }

        with mock.patch("autocoder.index.entry.PruneContext") as mock_prune_context:
            mock_prune_context.return_value.handle_overflow.return_value = [
                SourceCode(module_name="file1.py", source_code="def foo():\n    pass", tag="PY"),
                SourceCode(module_name="file2.py", source_code="def bar():\n    pass", tag="PY"),
            ]

            result = build_index_and_filter_files(self.llm, self.args, self.sources)

            # Assert that the files are sorted based on file_positions
            self.assertEqual(len(result.sources), 2)
            self.assertEqual(result.sources[0].module_name, "file1.py")
            self.assertEqual(result.sources[1].module_name, "file2.py")

    def test_context_prune_without_file_positions(self):
        with mock.patch("autocoder.index.entry.PruneContext") as mock_prune_context:
            mock_prune_context.return_value.handle_overflow.return_value = [
                SourceCode(module_name="file1.py", source_code="def foo():\n    pass", tag="PY"),
                SourceCode(module_name="file2.py", source_code="def bar():\n    pass", tag="PY"),
            ]

            result = build_index_and_filter_files(self.llm, self.args, self.sources)

            # Assert that the files are not sorted based on file_positions
            self.assertEqual(len(result.sources), 2)
            self.assertEqual(result.sources[0].module_name, "file1.py")
            self.assertEqual(result.sources[1].module_name, "file2.py")

if __name__ == "__main__":
    import unittest
    unittest.main()
