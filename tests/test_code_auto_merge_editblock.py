import unittest
from autocoder.common.code_auto_merge_editblock import CodeAutoMergeEditBlock, AutoCoderArgs

class TestCodeAutoMergeEditBlock(unittest.TestCase):
    def setUp(self):
        self.args = AutoCoderArgs()
        self.merger = CodeAutoMergeEditBlock(llm=None, args=self.args)

    def test_parse_whole_text(self):
        test_text = """
```python
##File: /path/to/file1.py
def function1():
    pass
```

Some text in between

```python
##File: /path/to/file2.py
def function2():
    return True
```
"""
        result = self.merger.parse_whole_text(test_text)
        
        self.assertEqual(len(result), 2)
        
        self.assertEqual(result[0].path, "/path/to/file1.py")
        self.assertEqual(result[0].content, "def function1():\n    pass")
        
        self.assertEqual(result[1].path, "/path/to/file2.py")
        self.assertEqual(result[1].content, "def function2():\n    return True")

    def test_parse_whole_text_with_inline_code(self):
        test_text = """
```python
##File: /path/to/file1.py
def function1():
    ```
    This is an inline code block
    ```
    pass
```
"""
        result = self.merger.parse_whole_text(test_text)
        
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].path, "/path/to/file1.py")
        self.assertEqual(result[0].content, 'def function1():\n    ```\n    This is an inline code block\n    ```\n    pass')

    def test_parse_whole_text_empty(self):
        test_text = ""
        result = self.merger.parse_whole_text(test_text)
        self.assertEqual(len(result), 0)

if __name__ == '__main__':
    unittest.main()