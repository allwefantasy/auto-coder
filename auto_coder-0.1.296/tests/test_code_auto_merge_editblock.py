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
当然，我可以根据 `code_auto_merge_editblock` 的实现为您编写一篇 Markdown 文档。这个文档将介绍 `CodeAutoMergeEditBlock` 类的功能、使用方法以及主要组件。以下是文档内容：

```markdown
##File: /path/to/code_auto_merge_editblock.py
# CodeAutoMergeEditBlock 文档

## 概述

`CodeAutoMergeEditBlock` 是一个用于自动合并代码编辑块的工具类。它能够解析包含编辑指令的文本，并将这些编辑应用到目标文件中。这个类特别适用于需要自动化代码修改过程的场景，如代码生成或自动重构。

## 主要功能

1. 解析包含编辑指令的文本
2. 将编辑应用到目标文件
3. 处理新文件的创建
4. 执行 Python 代码的语法检查
5. 与 Git 版本控制集成
6. 支持用户交互确认

## 初始化

```python
def __init__(self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs, fence_0: str = "```", fence_1: str = "```"):
```

- `llm`: ByzerLLM 实例，用于可能的语言模型交互
- `args`: AutoCoderArgs 实例，包含配置参数
- `fence_0` 和 `fence_1`: 用于标记代码块的分隔符，默认为三个反引号

## 主要方法

### parse_whole_text

```python
def parse_whole_text(self, text: str) -> List[PathAndCode]:
```

解析输入文本，提取文件路径和相应的代码块。

### get_edits

```python
def get_edits(self, content: str):
```

从解析后的内容中提取编辑指令。

### merge_code

```python
def merge_code(self, content: str, force_skip_git: bool = False):
```

执行代码合并操作。这是类的核心方法，它协调整个合并过程。

## 工作流程

1. 解析输入文本，提取编辑指令
2. 对每个编辑指令：
   - 如果目标文件不存在，创建新文件
   - 如果文件存在，应用编辑
   - 使用相似度比较处理不完全匹配的情况
3. 对 Python 文件执行 pylint 检查
4. 如果启用了 Git 集成，执行 Git 提交
5. 如果配置了用户交互，请求用户确认
6. 应用更改到文件系统

## 特殊功能

### Python 语法检查

使用 `run_pylint` 方法对 Python 文件进行基本的语法检查，确保合并后的代码不会引入明显的语法错误。

### Git 集成

通过 `git_utils` 模块与 Git 版本控制系统集成，在合并前后自动创建提交。

### 相似度匹配

当无法精确匹配编辑块时，使用 `TextSimilarity` 类来查找最佳匹配的代码段。

## 使用注意事项

1. 确保提供正确格式的编辑指令文本
2. 对于 Python 项目，建议启用 pylint 检查以确保代码质量
3. 使用 Git 集成时，确保在 Git 仓库中运行
4. 注意处理可能的合并冲突和未合并的代码块

## 结论

`CodeAutoMergeEditBlock` 提供了一个强大而灵活的方式来自动化代码编辑过程。通过仔细配置和使用，它可以显著提高代码修改和维护的效率。
```

这个 Markdown 文档提供了 `CodeAutoMergeEditBlock` 类的概览，包括其主要功能、使用方法、以及一些重要的实现细节。它应该能够帮助开发者理解这个类的用途和工作原理。如果您需要更详细的信息或者针对特定部分的深入解释，请随时告诉我。
"""
        result = self.merger.parse_whole_text(test_text)
        
        print(result[0].content)

    def test_parse_whole_text_empty(self):
        test_text = ""
        result = self.merger.parse_whole_text(test_text)
        self.assertEqual(len(result), 0)

if __name__ == '__main__':
    unittest.main()