
# 048_AutoCoder如何辅助项目代码阅读

## 背景

AutoCoder 提供了一系列工具和功能来辅助开发者进行项目代码阅读，本文将介绍其中的两个主要功能：/ask 和 agent/project_reader。

## chat-auto-coder 中的/ask 命令

chat-auto-coder 是个命令行交互工具，其中的

`/ask` 命令允许用户直接向 AI 提问，获取与当前项目相关的信息。

### 示例

以下是一个使用 `/ask` 命令的示例：

```
/ask 这个项目是用来做啥的？
```

为了能够使用该功能,需要先构建索引：

```
/index/build
```

此外，你也可以使用 `/chat` 来对通过 `/add_files` 添加的活动文件来进行提问。`/chat` 是不需要
索引支持的。

```
/add_files chat_auto_coder.py
/chat 这个文件里都有哪些指令？
```

这里，我们添加了一个文件 `chat_auto_coder.py`，然后使用 `/chat` 对这个问题进行提问。


## auto-coder 中的 agent/project_reader

`agent/project_reader` 是另一个强大的工具，chat-auto-coder中的 `/ask` 也是基于该工具做的二次封装，
用于分析和提取项目中的关键信息。

### 示例

使用 `agent/project_reader` 可以生成一个包含项目关键文件和函数的详细报告：

```
auto-coder index --file ./actions/base/base.yml
auto-coder agent project_reader --file ./actions/base/base.yml --query "帮我找到 exclude_dirs函数，并且给出完整代码"
```

还有一些常见的问题：

1. 罗列 xxxx 中所有的类函数
2. IndexManager 类都被哪些文件使用了？
3. 帮我阅读下planner.py 为啥里面需要用 IndexManager?
4. 该项目是如何完成自动代码合并的

## 一些比较好的实践

比如你可能好奇， chat-auto-coder 项目是如何实现代码自动合并的，此时你可以进入 auto-coder项目，然后直接问题：

```
/ask 该项目是如何完成自动代码合并的？
```

输出：

```
=============RESPONSE==================


该项目通过`CodeAutoMerge`和`CodeAutoMergeDiff`两个类来完成自动代码合并。`CodeAutoMerge`类主要通过`merge_code`方法实现代码合并，该方法首先读取文件内容，计算MD5值，然后尝试将代码解析并写入到指定路径的文件中。如果文件不存在，则创建新文件。合并完成后，如果未强制跳过Git操作，则提交更改到Git仓库。

`CodeAutoMergeDiff`类则通过`merge_code`方法实现更复杂的代码合并，它首先获取代码差异，然后应用这些差异到文件中。如果差异应用成功，则更新文件内容；如果失败，则抛出异常。同样，如果未强制跳过Git操作，合并完成后也会提交更改到Git仓库。

这两个类都依赖于`byzerllm`和`autocoder`库中的其他工具和方法，如`git_utils`用于Git操作，`code_utils`用于代码处理等。通过这些工具和方法的组合，实现了自动化的代码合并功能。
```

可以看到，整体效果还是不错，但是还是有遗漏，因为大模型还是没把项目完全看全。

此时我们可以分两个步骤来解决，先找到相关文件：

```
/index/query 自动代码合并相关的文件
```

这个是找到的内容：
```
index_filter_level:1, total files: 6 filter files by query: 自动代码合并相关的文件

+-----------------------------------------------------------+--------------------------------------------------------------+
| file_path                                                 | reason                                                       |
+===========================================================+==============================================================+
| /Users/allwefantasy/projects/auto-                        | This file contains functions related to automatic code       |
| coder/src/autocoder/common/code_auto_merge.py             | merging, including parsing text and merging code.            |
+-----------------------------------------------------------+--------------------------------------------------------------+
| /Users/allwefantasy/projects/auto-                        | This file focuses on merging code edit blocks, facilitating  |
| coder/src/autocoder/common/code_auto_merge_editblock.py   | efficient code integration and modification.                 |
+-----------------------------------------------------------+--------------------------------------------------------------+
| /Users/allwefantasy/projects/auto-                        | This file deals with strict diff handling in automatic code  |
| coder/src/autocoder/common/code_auto_merge_strict_diff.py | merging, ensuring precise code integration.                  |
+-----------------------------------------------------------+--------------------------------------------------------------+
| /Users/allwefantasy/projects/auto-                        | This file handles automatic code merging with diff           |
| coder/src/autocoder/common/code_auto_merge_diff.py        | processing, including applying hunks and merging code.       |
+-----------------------------------------------------------+--------------------------------------------------------------+
| /Users/allwefantasy/projects/auto-                        | Contains functions related to building and querying indexes, |
| coder/src/autocoder/index/index.py                        | which might be involved in code merging processes.           |
+-----------------------------------------------------------+--------------------------------------------------------------+
| /Users/allwefantasy/projects/auto-                        | Includes functions for managing files and directories, which |
| coder/src/autocoder/chat_auto_coder.py                    | could be relevant for code merging.                          |
+-----------------------------------------------------------+--------------------------------------------------------------+
```

然后在 /ask 里让他主动关注下这几个文件：

```
/ask 直接阅读下下面几个文件：code_auto_merge.py,code_auto_merge_editblock.py,code_auto_merge_strict_diff.py,code_auto_merge_diff.py，然后告诉我这些文件是如何实现自动代码合并的？
```

这个时候的输出：

```

```

## 暂时无法解决的一些问题

1. 可以指定文件检测语法错误，比如说： 看看 planner.py 中是否有语法错误， 但无法做到：项目中有哪些代码文件有语法错误（需要遍历整个项目文件，代价太大）。
2. 无法任意查找一个文件，只能查找已经构建索引的文件。所以构建取决于 project_type 和是否执行了 /index/build 或者  auto-coder index 命令。
3. 无法查找一个函数的调用者，只能查找一个函数的定义。

## 问题

因为采用了 Cot 来处理，有的时候会超出deepseek chat的最大窗口，会失败，可以换个问法。一般如果超出窗口长度，报错如下：

```
2024-06-23 22:16:09,104 ERROR serialization.py:414 -- Failed to unpickle serialized exception
Traceback (most recent call last):
  File "/opt/miniconda3/envs/byzerllm/lib/python3.10/site-packages/ray/exceptions.py", line 49, in from_ray_exception
    return pickle.loads(ray_exception.serialized_exception)
TypeError: APIStatusError.__init__() missing 2 required keyword-only arguments: 'response' and 'body'
```


## 结论

通过使用 `/ask` 或者 `agent/project_reader`，开发者可以更高效地理解和分析项目代码，提高开发和维护效率。
