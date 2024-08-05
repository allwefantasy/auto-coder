import unittest
from autocoder.common.command_completer import CommandTextParser, COMMANDS

class TestCommandTextParser(unittest.TestCase):
    def test_add_files_basic(self):
        parser = CommandTextParser("/add_files file1 file2 file3", "/add_files")
        parser.add_files()
        self.assertFalse(parser.is_extracted)
        self.assertEqual(parser.pos, len("/add_files file1 file2 file3") - 1)

    def test_add_files_group(self):
        parser = CommandTextParser("/add_files /group list", "/add_files")
        parser.add_files()
        self.assertFalse(parser.is_extracted)
        self.assertEqual(parser.pos, len("/add_files /group list") - 1)

    def test_add_files_group_add(self):
        parser = CommandTextParser("/add_files /group /add groupname", "/add_files")
        parser.add_files()
        self.assertFalse(parser.is_extracted)
        self.assertEqual(parser.pos, len("/add_files /group /add groupname") - 1)

    def test_add_files_group_drop(self):
        parser = CommandTextParser("/add_files /group /drop groupname", "/add_files")
        parser.add_files()
        self.assertFalse(parser.is_extracted)
        self.assertEqual(parser.pos, len("/add_files /group /drop groupname") - 1)

    def test_add_files_group_multiple(self):
        parser = CommandTextParser("/add_files /group group1,group2", "/add_files")
        parser.add_files()
        self.assertFalse(parser.is_extracted)
        self.assertEqual(parser.pos, len("/add_files /group group1,group2") - 1)

    def test_add_files_refresh(self):
        parser = CommandTextParser("/add_files /refresh", "/add_files")
        parser.add_files()
        self.assertFalse(parser.is_extracted)
        self.assertEqual(parser.pos, len("/add_files /refresh") - 1)

    def test_is_sub_command(self):
        parser = CommandTextParser("/group", "/add_files")
        self.assertTrue(parser.is_sub_command())

        parser = CommandTextParser("notasubcommand", "/add_files")
        self.assertFalse(parser.is_sub_command())

    def test_consume_sub_command(self):
        parser = CommandTextParser("/group /add", "/add_files")
        result = parser.consume_sub_command()
        self.assertEqual(result, "/group")
        self.assertEqual(parser.pos, len("/group") - 1)

    def test_current_word(self):
        parser = CommandTextParser("/add_files /group", "/add_files")
        parser.current_word_start_pos = 11
        parser.current_word_end_pos = 17
        self.assertEqual(parser.current_word(), "/group")

if __name__ == '__main__':
    unittest.main()