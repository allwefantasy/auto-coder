import os
import unittest
from unittest.mock import MagicMock, patch
from autocoder.common import AutoCoderArgs
from autocoder.dispacher.actions.plugins.action_regex_project import ActionRegexProject

class TestActionRegexProject(unittest.TestCase):

    def setUp(self):
        self.args = AutoCoderArgs(
            source_dir=".",
            project_type="regex://test",
            query="Test query",
            execute=True,
            auto_merge="editblock",
            target_file="test_output.txt",
            model_max_input_length=1000            
        )
        self.llm = MagicMock()

    def tearDown(self):
        if os.path.exists("test_output.txt"):
            os.remove("test_output.txt")

    @patch("autocoder.dispacher.actions.plugins.action_regex_project.RegexProject")
    def test_run(self, mock_regex_project):
        mock_regex_project.return_value.output.return_value = "Test output"
        action = ActionRegexProject(self.args, self.llm)
        action.run()
        mock_regex_project.assert_called_once_with(args=self.args, llm=self.llm)
        self.assertTrue(os.path.exists("test_output.txt"))
        with open("test_output.txt", "r") as f:
            self.assertEqual(f.read(), "Test output")

    @patch("autocoder.dispacher.actions.plugins.action_regex_project.CodeAutoGenerateEditBlock")
    def test_process_content(self, mock_code_auto_generate):
        mock_code_auto_generate.return_value.single_round_run.return_value = (["Generated content"], None)
        action = ActionRegexProject(self.args, self.llm)
        action.process_content("Test content")
        mock_code_auto_generate.assert_called_once_with(llm=self.llm, args=self.args, action=action)
        with open("test_output.txt", "r") as f:
            self.assertEqual(f.read(), "Generated content")

if __name__ == "__main__":
    unittest.main()