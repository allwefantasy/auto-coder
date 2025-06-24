在 .auto-coder/targets 目录下生成如下验证代码：

```python
from autocoder.common.ac_style_command_parser.parser import CommandParser

p = CommandParser()

result = p.parse("""/command "tdd/hello.md" name='''威廉'''""")

print(result)
```
然后运行该代码，我们期待的运行结果是这样的：

{'command': {'args': ['tdd/hello.md'], 'kwargs': {'name':'威廉'}}}

也就是我们希望能够支持解析 '''''' 引用起来的文本。

运行上面的python代码，直到运行结果符合我们预期。