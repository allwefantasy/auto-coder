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
        self.project = TSProject(self.args,llm=None)

    def tearDown(self):
        shutil.rmtree(self.temp_dir)
   

    @patch("autocoder.tsproject.TSProject.get_source_codes")
    def test_get_simple_directory_structure(self, mock_get_source_codes):
        mock_get_source_codes.return_value = [
            SourceCode(module_name=os.path.join(self.temp_dir, "src/index.ts"), source_code=""),
            SourceCode(module_name=os.path.join(self.temp_dir, "src/utils/helper.ts"), source_code="")
        ]
        structure = self.project.get_simple_directory_structure.prompt() 
        print(structure)       

    @patch("autocoder.tsproject.TSProject.get_source_codes")
    def test_get_tree_like_directory_structure(self, mock_get_source_codes):
        mock_get_source_codes.return_value = [
            SourceCode(module_name=os.path.join(self.temp_dir, "src/index.ts"), source_code=""),
            SourceCode(module_name=os.path.join(self.temp_dir, "src/utils/helper.ts"), source_code=""),
            SourceCode(module_name=os.path.join(self.temp_dir, "src/utils/helper2.ts"), source_code="")
        ]
        structure = self.project.get_tree_like_directory_structure.prompt()
        print(structure)

if __name__ == "__main__":
    unittest.main()