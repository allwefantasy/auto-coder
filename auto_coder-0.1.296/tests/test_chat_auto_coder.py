import os
import sys
import json
import unittest
from unittest.mock import Mock, patch
from io import StringIO

from autocoder.chat_auto_coder import (
    get_all_file_names_in_project,
    get_all_file_in_project,
    get_all_dir_names_in_project,
    find_files_in_project,
    convert_config_value,
    configure,
    show_help,
    save_memory,
    load_memory,
    revert,
    add_files,
    remove_files,
    chat,
    exclude_dirs,
    index_query,
    memory,
)

class TestChatAutoCoder(unittest.TestCase):
    def setUp(self):
        self.test_dir = os.path.join(os.path.dirname(__file__), "test_project")
        os.makedirs(self.test_dir, exist_ok=True)
        self.files = ["file1.txt", "file2.txt", "subdir/file3.txt"]
        for file in self.files:
            file_path = os.path.join(self.test_dir, file)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, "w") as f:
                f.write("test content")

    def tearDown(self):
        for root, dirs, files in os.walk(self.test_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(self.test_dir)

    def test_get_all_file_names_in_project(self):
        with patch("os.getcwd", return_value=self.test_dir):
            file_names = get_all_file_names_in_project()
            expected_names = [os.path.basename(file) for file in self.files]
            self.assertCountEqual(file_names, expected_names)

    def test_get_all_file_in_project(self):
        with patch("os.getcwd", return_value=self.test_dir):
            file_paths = get_all_file_in_project()
            expected_paths = [os.path.join(self.test_dir, file) for file in self.files]
            self.assertCountEqual(file_paths, expected_paths)

    def test_get_all_dir_names_in_project(self):
        with patch("os.getcwd", return_value=self.test_dir):
            dir_names = get_all_dir_names_in_project()
            self.assertIn("subdir", dir_names)

    def test_find_files_in_project(self):
        with patch("os.getcwd", return_value=self.test_dir):
            file_names = ["file1.txt", "subdir/file3.txt"]
            matched_files = find_files_in_project(file_names)
            expected_paths = [os.path.join(self.test_dir, file) for file in file_names]
            self.assertCountEqual(matched_files, expected_paths)

    def test_convert_config_value(self):
        self.assertTrue(convert_config_value("human_as_model", "true"))
        self.assertFalse(convert_config_value("human_as_model", "false"))
        self.assertEqual(convert_config_value("index_model_max_length", "10"), 10)        

    def test_configure(self):
        with patch("autocoder.chat_auto_coder.save_memory") as mock_save_memory:
            configure("key: value")
            self.assertEqual(memory["conf"]["key"], "value")
            mock_save_memory.assert_called_once()

    def test_show_help(self):
        with patch("sys.stdout", new=StringIO()) as fake_out:
            show_help()
            output = fake_out.getvalue()
            self.assertIn("Supported commands:", output)
            self.assertIn("/add_files", output)
            self.assertIn("/remove_files", output)
            # Add more assertions for other commands

    def test_save_and_load_memory(self):
        chat.memory = {"key": "value"}
        with patch("autocoder.chat_auto_coder.base_persist_dir", self.test_dir):
            save_memory()
            chat.memory = {}
            load_memory()
            self.assertEqual(chat.memory["key"], "value")

    def test_revert(self):
        with patch("autocoder.chat_auto_coder.get_last_yaml_file", return_value="last.yml"), \
             patch("autocoder.chat_auto_coder.auto_coder_main") as mock_auto_coder_main, \
             patch("os.remove") as mock_remove:
            revert()
            mock_auto_coder_main.assert_called_once_with(["revert", "--file", "actions/last.yml"])
            mock_remove.assert_called_once_with("actions/last.yml")

    def test_add_and_remove_files(self):
        with patch("autocoder.chat_auto_coder.find_files_in_project", return_value=self.files), \
             patch("autocoder.chat_auto_coder.save_memory") as mock_save_memory:
            add_files(["file1.txt", "file2.txt"])
            self.assertCountEqual(chat.memory["current_files"]["files"], self.files[:2])
            mock_save_memory.assert_called_once()

            remove_files(["file1.txt"])
            self.assertCountEqual(chat.memory["current_files"]["files"], [self.files[1]])
            self.assertEqual(mock_save_memory.call_count, 2)

    def test_chat(self):
        chat.memory["current_files"]["files"] = self.files
        with patch("autocoder.chat_auto_coder.auto_coder_main") as mock_auto_coder_main, \
             patch("autocoder.chat_auto_coder.get_last_yaml_file", return_value="last.yml"), \
             patch("autocoder.chat_auto_coder.save_memory") as mock_save_memory, \
             patch("builtins.open", unittest.mock.mock_open()) as mock_file:
            chat("test query")
            self.assertEqual(chat.memory["conversation"][-1], {"role": "user", "content": "test query"})
            mock_auto_coder_main.assert_called_once()
            mock_save_memory.assert_called_once()
            mock_file.assert_called_once_with("actions/last.yml", "w")

    def test_exclude_dirs(self):
        with patch("autocoder.chat_auto_coder.save_memory") as mock_save_memory:
            exclude_dirs(["exclude1", "exclude2"])
            self.assertCountEqual(chat.memory["exclude_dirs"], ["exclude1", "exclude2"])
            mock_save_memory.assert_called_once()

    def test_index_query(self):
        with patch("autocoder.chat_auto_coder.auto_coder_main") as mock_auto_coder_main, \
             patch("builtins.open", unittest.mock.mock_open()) as mock_file:
            index_query("test query")
            mock_auto_coder_main.assert_called_once()
            mock_file.assert_called_once()

if __name__ == "__main__":
    unittest.main()