
# 代码索引器使用指南

## 概述

代码索引器用于构建代码库的索引，支持按关键词搜索代码中的类、函数和文件。

## 主要功能

1. 索引多种编程语言的源代码文件
2. 提取代码中的类和函数定义
3. 支持按关键词搜索代码库

## 使用方法

### 初始化索引器

```python
from code_indexer import CodeIndexer

# 创建索引器实例
indexer = CodeIndexer("/path/to/code/directory")
```

### 构建索引

```python
# 构建代码索引
indexer.build_index()
```

### 搜索代码

```python
# 按关键词搜索
results = indexer.search("keyword")

# 处理搜索结果
for result in results:
    print(result)
```

## 支持的文件类型

代码索引器支持以下文件类型：
- Python (.py)
- Java (.java)
- JavaScript (.js)
- TypeScript (.ts)
- C (.c)
- C++ (.cpp, .h)
- C# (.cs)
- Go (.go)

## 注意事项

1. 索引构建过程可能较慢，特别是对于大型代码库
2. 搜索结果按相关性排序，文件名匹配的相关性最高
3. 当前实现使用简单的正则表达式匹配，可能无法处理复杂的代码结构
