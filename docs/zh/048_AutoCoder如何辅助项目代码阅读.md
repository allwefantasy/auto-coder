
# 048_AutoCoder如何辅助项目代码阅读

## 背景

AutoCoder 提供了一系列工具和功能来辅助开发者进行项目代码阅读，本文将介绍其中的两个主要功能：/ask 和 agent/project_reader。

## chat-auto-coder 中的/ask 命令

chat-auto-coder 是个命令行交互工具，其中的

`/ask` 命令允许用户直接向 AI 提问，获取与当前项目相关的信息。

### 示例

以下是一个使用 `/ask` 命令的示例：

```bash
/ask 这个项目是用来做啥的？
```

为了能够使用该功能,需要先构建索引：

```bash
/index/build
```

特别注意：

索引构建并不会对整个项目所有文件进行索引，而是根据 project_type 来选择性的构建索引，chat-auto-coder会读取 ./actions/base/base.yml 文件中的 project_type 来决定构建索引的文件类型

你可以手动在当前会话里进行更改，

前端项目你可以通过如下方式设置：

```bash
/conf project_type:ts
```

其他项目可以通过后缀设置,比如你可以同时设置索引.java,.scala后缀名的文件：

```bash
/conf project_type:.java,.scala
```

`/ask` 命令会自动解析问题并返回相应的答案。如果你想要查看更多信息，可以使用 `/more` 命令：

```bash

此外，你也可以使用 `/chat` 来对通过 `/add_files` 添加的活动文件来进行提问。`/chat` 是不需要
索引支持的。

```bash
/add_files chat_auto_coder.py
/chat 这个文件里都有哪些指令？
```

这里，我们添加了一个文件 `chat_auto_coder.py`，然后使用 `/chat` 对这个问题进行提问。

此外，如果你想单纯的问大模型一些通用知识，可以直接使用 `/chat` 命令。

```bash
/chat  python 如何移除指定前缀
```
你可以清理掉当前的活动文件，从而使得响应更快：

```bash
/remove_files /all
```         



## auto-coder 中的 agent/project_reader

`agent/project_reader` 是另一个强大的工具，chat-auto-coder中的 `/ask` 也是基于该工具做的二次封装，
用于分析和提取项目中的关键信息。

### 示例

使用 `agent/project_reader` 可以生成一个包含项目关键文件和函数的详细报告：

```bash
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

```bash
/ask 该项目是如何完成自动代码合并的？
```

输出：

```
=============RESPONSE==================


该项目通过`CodeAutoMerge`和`CodeAutoMergeDiff`两个类来完成自动代码合并。`CodeAutoMerge`类主要通过`merge_code`方法实现代码合并，该方法首先读取文件内容，计算MD5值，然后尝试将代码解析并写入到指定路径的文件中。如果文件不存在，则创建新文件。合并完成后，如果未强制跳过Git操作，则提交更改到Git仓库。

`CodeAutoMergeDiff`类则通过`merge_code`方法实现更复杂的代码合并，它首先获取代码差异，然后应用这些差异到文件中。如果差异应用成功，则更新文件内容；如果失败，则抛出异常。同样，如果未强制跳过Git操作，合并完成后也会提交更改到Git仓库。

这两个类都依赖于`byzerllm`和`autocoder`库中的其他工具和方法，如`git_utils`用于Git操作，`code_utils`用于代码处理等。通过这些工具和方法的组合，实现了自动化的代码合并功能。
```


另外，我们也可以更加手动挡一些，循序渐进的提问，比如第一次我先找到一些可能和我问题相关的文件：

```bash
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

这样我可以人工选一些文件（有的时候系统自动找的文件太多，会导致最后问询失败），然后在 /ask 里让他主动阅读者几个文件的源码来回答我的问题：

```bash
/ask 直接阅读下下面几个文件：code_auto_merge.py,code_auto_merge_editblock.py,code_auto_merge_strict_diff.py,code_auto_merge_diff.py，然后告诉我这些文件是如何实现自动代码合并的？
```

这个时候的输出：

```
=============RESPONSE==================


这些文件通过解析文本，提取代码块，并使用不同的方法将这些代码块合并到项目中。`code_auto_merge.py` 使用 `parse_whole_text_v2` 方法解析文本，`code_auto_merge_editblock.py` 支持编辑块的合并，而 `code_auto_merge_strict_diff.py` 和 `code_auto_merge_diff.py` 则通过解析 diff 格式的文本来处理代码差异。这些文件都依赖于 `byzerllm` 和 `autocoder.common` 中的工具和方法来实现自动代码合并。
```

接着你可以继续这么问：

```bash
/ask `code_auto_merge.py` 使用 `parse_whole_text_v2` 方法解析文本,该方法的具体实现是怎么样的?
```

这次的输出:

```
=============RESPONSE==================


`parse_whole_text_v2` 方法的实现主要分为以下几个步骤：

1. 首先，将输入的文本按行分割，存储在列表 `lines` 中。
2. 定义了几个辅助函数来识别文本中的标记：
   - `start_marker` 函数用于检测是否为代码块的开始标记，即行首是否为 '```'，并且下一行是否以 '##File:' 开始。
   - `inline_start_marker` 函数用于检测内联代码块的开始标记，即行首是否为 '```'，并且该行不等于 '```'。
   - `end_marker` 函数用于检测代码块的结束标记，即行首是否为 '```'，并且该行等于 '```'。
3. 遍历每一行文本，根据不同的标记进行处理：
   - 如果检测到代码块的开始标记，增加 `start_marker_count`。
   - 如果检测到内联代码块的开始标记，增加 `inline_start_marker_count`，并将该行添加到 `block` 列表中。
   - 如果检测到代码块的结束标记，并且 `start_marker_count` 为 1，`inline_start_marker_count` 为 0，则提取文件路径和内容，并将其添加到 `path_and_code_list` 列表中。
   - 如果检测到内联代码块的结束标记，减少 `inline_start_marker_count`。
   - 如果 `start_marker_count` 大于 0，将当前行添加到 `block` 列表中。
4. 最后，返回包含所有解析出的文件路径和内容的列表 `path_and_code_list`。

这个方法主要用于从文本中提取出格式化的代码块，包括文件路径和代码内容，以便后续处理。
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
