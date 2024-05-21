import os
import shutil
import tempfile
import unittest
from unittest.mock import patch, MagicMock

from autocoder.tsproject import TSProject
from autocoder.common import AutoCoderArgs, SourceCode

class TestTSProject(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.args = AutoCoderArgs(source_dir=self.temp_dir)
        self.project = TSProject(self.args)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)

    def create_test_file(self, file_path, content):
        full_path = os.path.join(self.temp_dir, file_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w") as f:
            f.write(content)

    def test_is_likely_useful_file(self):
        self.assertTrue(self.project.is_likely_useful_file("src/index.ts"))
        self.assertTrue(self.project.is_likely_useful_file("components/Button.tsx"))
        self.assertFalse(self.project.is_likely_useful_file("node_modules/lib/index.js"))
        self.assertFalse(self.project.is_likely_useful_file("public/index.html"))
        self.assertFalse(self.project.is_likely_useful_file("docs/README.md"))

    def test_convert_to_source_code(self):
        self.create_test_file("src/index.ts", "console.log('Hello world')")
        source_code = self.project.convert_to_source_code(os.path.join(self.temp_dir, "src/index.ts"))
        self.assertIsInstance(source_code, SourceCode)
        self.assertEqual(source_code.module_name, os.path.join(self.temp_dir, "src/index.ts"))
        self.assertEqual(source_code.source_code, "console.log('Hello world')")

        self.create_test_file("README.md", "# Project README")
        source_code = self.project.convert_to_source_code(os.path.join(self.temp_dir, "README.md"))
        self.assertIsNone(source_code)

    @patch("autocoder.tsproject.TSProject.get_source_codes")
    def test_get_simple_directory_structure(self, mock_get_source_codes):
        mock_get_source_codes.return_value = [
            SourceCode(module_name=os.path.join(self.temp_dir, "src/index.ts"), source_code=""),
            SourceCode(module_name=os.path.join(self.temp_dir, "src/utils/helper.ts"), source_code="")
        ]
        structure = self.project.get_simple_directory_structure()
        self.assertIn(self.temp_dir, structure)
        self.assertIn("src/index.ts", structure)
        self.assertIn("src/utils/helper.ts", structure)

    # TODO: 添加更多测试用例

if __name__ == "__main__":
    unittest.main()