
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
auto-coder index --file ./base/base.yml
auto-coder agent project_reader --file ./base/base.yml --query "帮我找到 exclude_dirs函数，并且给出完整代码"
```

还有一些常见的问题：

1. 罗列 xxxx 中所有的类函数
2. IndexManager 类都被哪些文件使用了？
3. 帮我阅读下planner.py 为啥里面需要用 IndexManager?
4. 该项目合并代码的方式都有哪些？

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
