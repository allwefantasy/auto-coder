
# 048_AutoCoder如何辅助项目代码阅读

## 背景

AutoCoder 提供了一系列工具和功能来辅助开发者进行项目代码阅读，本文将介绍其中的两个主要功能：/ask 和 agent/project_reader。

## chat-auto-coder 中的/ask 命令

chat-auto-coder 中是个命令行交互工具，其中的

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


## auto-coder 中的 agent/project_reader

`agent/project_reader` 是另一个强大的工具，用于分析和提取项目中的关键信息。

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


## 结论

通过使用 `/ask` 或者 `agent/project_reader`，开发者可以更高效地理解和分析项目代码，提高开发和维护效率。
