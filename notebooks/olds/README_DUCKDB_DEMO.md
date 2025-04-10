# DuckDB本地存储缓存演示

这个演示程序展示了如何使用`LocalDuckDBStorageCache`来创建、管理和查询代码库的缓存。

## 功能概述

`LocalDuckDBStorageCache`是一个用于存储和检索代码文件的缓存管理器，它具有以下功能：

1. 自动扫描目录中的代码文件
2. 使用DuckDB存储代码文件的内容和向量嵌入
3. 支持基于语义向量搜索查询相关代码
4. 自动检测和更新已修改的文件

## 先决条件

在运行此演示前，您需要安装以下依赖项：

```bash
pip install autocoder loguru duckdb byzerllm tokenizers
```

## 演示内容

这个演示程序执行以下操作：

1. 创建示例代码文件（计算器类、字符串处理类和数据处理类）
2. 初始化DuckDB缓存管理器
3. 构建代码库索引
4. 执行多个语义查询并展示结果
5. 更新一个代码文件并测试缓存自动更新功能
6. 查询新添加的代码功能

## 如何运行

```bash
python demo_duckdb_cache.py
```

## 输出说明

演示程序运行时会输出详细的日志，包括：

- 缓存初始化过程
- 索引构建进度
- 查询结果
- 文件更新检测
- 缓存更新过程

## 自定义使用

如果您想在自己的项目中使用`LocalDuckDBStorageCache`，可以参考以下步骤：

1. 初始化LLM（用于生成向量嵌入）
   ```python
   from autocoder.utils.llms import get_single_llm
   llm = get_single_llm("v3_chat", product_mode="lite")
   ```

2. 配置参数
   ```python
   from autocoder.common import AutoCoderArgs
   args = AutoCoderArgs(
       source_dir="your_code_dir",
       rag_duckdb_vector_dim=None,  # 使用默认嵌入维度
       duckdb_query_similarity=0.7,  # 向量搜索相似度阈值
       duckdb_query_top_k=20,        # 返回的最多相似文档数
       hybrid_index_max_output_tokens=10000  # 最大输出token数
   )
   ```

3. 初始化缓存管理器
   ```python
   from autocoder.rag.cache.local_duckdb_storage_cache import LocalDuckDBStorageCache
   from autocoder.rag.utils import GitignoreSpec
   
   cache_manager = LocalDuckDBStorageCache(
       path="cache_dir",  # 缓存存储目录
       ignore_spec=GitignoreSpec([]),  # 忽略规则，类似.gitignore
       required_exts=[".py", ".js"],  # 要索引的文件扩展名
       extra_params=args,
       emb_llm=llm
   )
   ```

4. 构建缓存
   ```python
   cache_manager.build_cache()
   ```

5. 执行查询
   ```python
   results = cache_manager.get_cache({
       "queries": ["如何计算平均值"],
       "enable_vector_search": True
   })
   ```

6. 处理查询结果
   ```python
   for file_path, file_info in results.items():
       print(f"文件: {file_path}")
       for doc in file_info['content']:
           print(f"代码: {doc['source_code']}")
   ```

## 注意事项

- 确保您的系统中已正确安装了DuckDB
- 第一次构建缓存可能需要较长时间，特别是对于大型代码库
- 向量搜索需要较多的内存资源 