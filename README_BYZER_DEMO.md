# Byzer Storage本地存储缓存演示

这个演示程序展示了如何使用`LocalByzerStorageCache`来创建、管理和查询代码库的缓存。Byzer Storage是一个高性能的向量数据库，非常适合用于语义搜索。

## 功能概述

`LocalByzerStorageCache`是一个用于存储和检索代码文件的缓存管理器，它具有以下功能：

1. 自动扫描目录中的代码文件
2. 使用Byzer Storage存储代码文件的内容和向量嵌入
3. 支持基于语义向量搜索和文本搜索查询相关代码
4. 支持多查询合并策略
5. 自动检测和更新已修改的文件

## 先决条件

在运行此演示前，您需要安装以下依赖项：

```bash
pip install autocoder loguru byzerllm tokenizers
```

另外，您需要启动Byzer Storage服务。默认情况下，服务运行在`127.0.0.1:33333`。

## 演示内容

这个演示程序执行以下操作：

1. 创建示例代码文件（计算器类、字符串处理类和数据处理类）
2. 初始化Byzer Storage缓存管理器
3. 构建代码库索引
4. 执行单个语义查询并展示结果
5. 执行多查询合并测试
6. 更新一个代码文件并测试缓存自动更新功能
7. 查询新添加的代码功能
8. 演示混合搜索功能（同时使用向量搜索和文本搜索）

## 如何运行

```bash
python demo_byzer_storage_cache.py
```

## 输出说明

演示程序运行时会输出详细的日志，包括：

- 缓存初始化过程
- 索引构建进度
- 查询结果
- 文件更新检测
- 缓存更新过程

## 与DuckDB缓存的区别

相比于`LocalDuckDBStorageCache`，Byzer Storage缓存有以下特点：

1. 需要单独运行的存储服务
2. 支持更复杂的查询合并策略
3. 同时支持向量搜索和文本搜索
4. 更适合大规模代码库的索引和查询

## 自定义使用

如果您想在自己的项目中使用`LocalByzerStorageCache`，可以参考以下步骤：

1. 初始化LLM（用于生成向量嵌入）
   ```python
   from autocoder.utils.llms import get_single_llm
   llm = get_single_llm("v3_chat", product_mode="lite")
   emb_llm = get_single_llm("emb2", product_mode="lite")  # 用于生成向量嵌入
   ```

2. 配置参数
   ```python
   from autocoder.common import AutoCoderArgs
   args = AutoCoderArgs(
       source_dir="your_code_dir",
       rag_build_name="your_index_name",  # Byzer Storage需要的索引名称
       hybrid_index_max_output_tokens=10000  # 最大输出token数
   )
   ```

3. 初始化缓存管理器
   ```python
   from autocoder.rag.cache.local_byzer_storage_cache import LocalByzerStorageCache
   
   cache_manager = LocalByzerStorageCache(
       path="your_code_dir",  # 代码目录
       ignore_spec=None,      # 忽略规则，类似.gitignore
       required_exts=[".py", ".js"],  # 要索引的文件扩展名
       extra_params=args,
       emb_llm=emb_llm,
       host="127.0.0.1",  # Byzer Storage服务地址
       port=33333         # Byzer Storage服务端口
   )
   ```

4. 构建缓存
   ```python
   cache_manager.build_cache()
   ```

5. 执行单个查询
   ```python
   results = cache_manager.get_cache({
       "queries": ["如何计算平均值"],
       "enable_vector_search": True,
       "enable_text_search": True  # 同时启用文本搜索
   })
   ```

6. 执行多查询合并
   ```python
   results = cache_manager.get_cache({
       "queries": ["计算平均值", "字符串处理"],
       "merge_strategy": "WEIGHTED_RANK",  # 使用加权排名策略合并结果
       "max_results": 5  # 限制返回结果数量
   })
   ```

7. 处理查询结果
   ```python
   for file_path, file_info in results.items():
       print(f"文件: {file_path}")
       for doc in file_info['content']:
           print(f"代码: {doc['source_code']}")
   ```

## 多查询合并策略

`LocalByzerStorageCache`支持多种结果合并策略：

- `WEIGHTED_RANK`: 根据每个文档在各查询中的排名进行加权合并
- `MAX_SCORE`: 使用每个文档在所有查询中的最高分数
- `FIRST_QUERY_PRIORITY`: 优先考虑第一个查询的结果
- `UNION`: 简单合并所有查询结果

## 注意事项

- 确保Byzer Storage服务已经启动并可访问
- 第一次构建缓存可能需要较长时间，特别是对于大型代码库
- 向量搜索需要较多的内存资源
- 多查询功能可以帮助处理复杂的代码查询需求 