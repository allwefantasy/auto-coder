import os
import unittest
from autocoder.utils.project_structure import EnhancedFileAnalyzer, AnalysisConfig
from autocoder.common import AutoCoderArgs
import byzerllm

class TestProjectStructure(unittest.TestCase):
    def setUp(self):
        self.args = AutoCoderArgs(source_dir=os.path.dirname(__file__))
        self.llm = byzerllm.ByzerLLM()
        self.config = AnalysisConfig()
        self.analyzer = EnhancedFileAnalyzer(self.args, self.llm, self.config)

    def test_get_tree_structure(self):
        structure = self.analyzer.get_tree_structure()
        self.assertIsInstance(structure, dict)
        self.assertGreater(len(structure), 0)

    def test_analyze_extensions(self):
        extensions = self.analyzer.analyze_extensions()
        self.assertIsInstance(extensions, dict)
        self.assertIn("code", extensions)
        self.assertIn("config", extensions)
        self.assertIn("data", extensions)
        self.assertIn("document", extensions)
        self.assertIn("other", extensions)

    def test_get_directory_stats(self):
        stats = self.analyzer.get_directory_stats()
        self.assertIsInstance(stats, dict)
        self.assertIn("total_files", stats)
        self.assertIn("total_dirs", stats)
        self.assertIn("by_extension", stats)
        self.assertIn("file_types", stats)

    def test_should_ignore(self):
        self.assertTrue(self.analyzer.file_filter.should_ignore(".git", True))
        self.assertTrue(self.analyzer.file_filter.should_ignore("temp.swp", False))
        self.assertFalse(self.analyzer.file_filter.should_ignore("test.py", False))

if __name__ == "__main__":
    unittest.main()
