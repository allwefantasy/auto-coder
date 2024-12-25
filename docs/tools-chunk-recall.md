# 文档相关性工具使用指南

Auto-coder 提供了两个用于评估和验证文档相关性的命令行工具: `chunk` 和 `recall`。这两个工具可以帮助开发者测试和优化文档检索系统的性能。

## recall 工具

`recall` 工具用于验证文档召回模型的效果。它可以帮助我们了解模型在给定查询时是否能够正确检索到相关文档。

### 基本用法

```bash
auto-coder.rag tools recall --model MODEL_NAME [--content CONTENT] [--query QUERY]
```

参数说明:
- `--model`: (必需) 要使用的模型名称
- `--content`: (可选) 待验证的文档内容
- `--query`: (可选) 用于测试的查询语句

### 使用示例

1. 使用默认测试内容:

```bash
auto-coder.rag tools recall --model deepseek_chat
```

2. 使用自定义内容和查询:

```bash
auto-coder.rag tools recall \
  --model deepseek_chat \
  --content "这是一个关于机器学习的文档，主要讨论神经网络的基础知识..." \
  --query "机器学习的基础概念是什么?"
```

### 输出解释

工具会返回一个相关性分数和详细的分析结果,帮助你了解:
- 文档与查询的相关程度
- 模型识别出的关键信息
- 相关性判断的依据

## chunk 工具

`chunk` 工具用于验证文本分块模型的性能。它可以帮助我们评估模型在文档分段方面的表现。

### 基本用法

```bash
auto-coder.rag tools chunk --model MODEL_NAME [--content CONTENT] [--query QUERY]
```

参数说明:
- `--model`: (必需) 要使用的模型名称
- `--content`: (可选) 待验证的文档内容
- `--query`: (可选) 相关问题,用于引导分块

### 使用示例

1. 使用默认测试内容:

```bash
auto-coder.rag tools chunk --model deepseek_chat
```

2. 使用自定义内容:

```bash
auto-coder.rag tools chunk \
  --model deepseek_chat \
  --content "class TokenLimiter:
    def __init__(self, count_tokens, full_text_limit):
        self.count_tokens = count_tokens
        self.full_text_limit = full_text_limit
    
    def limit_tokens(self, docs):
        return docs[:self.full_text_limit]" \
  --query "TokenLimiter类的主要方法有哪些?"
```

### 输出解释

工具会返回:
- 识别出的逻辑分块范围
- 每个分块的详细内容
- 分块策略的说明

## 使用建议

1. 在开发 RAG 系统时，先使用这些工具评估和调优模型性能
2. 针对特定场景选择合适的测试用例
3. 通过实验不同的参数来找到最佳配置

## 实际应用案例

### 优化文档检索系统

```python
# 测试文档召回效果
result = subprocess.run([
    "auto-coder.rag", "tools", "recall",
    "--model", "deepseek_chat",
    "--content", "RAG (Retrieval Augmented Generation) 是一种结合检索和生成的AI技术...",
    "--query", "什么是RAG?"
])
print(result.stdout)

# 测试文档分块效果
result = subprocess.run([
    "auto-coder.rag", "tools", "chunk",
    "--model", "deepseek_chat",
    "--content", long_document,
    "--query", "文档的主要章节有哪些?"
])
print(result.stdout)
```

### 代码文档分析

这两个工具对于处理代码文档特别有用:
- 使用 `recall` 验证代码片段的相关性检索
- 使用 `chunk` 对代码文件进行智能分段

## 最佳实践

1. **准备测试数据**
   - 使用真实场景的文档样本
   - 准备多样化的查询问题
   - 包含不同难度级别的测试用例

2. **评估和优化**
   - 定期运行测试评估性能
   - 根据测试结果调整模型参数
   - 记录并分析性能变化

3. **持续改进**
   - 收集用户反馈
   - 更新测试用例
   - 优化模型配置

## 总结

`chunk` 和 `recall` 工具是 auto-coder.rag 提供的强大的文档相关性评估工具。通过合理使用这些工具，我们可以:
- 评估并改进文档检索系统的性能
- 优化文档分块策略
- 提高 RAG 系统的整体效果

有关更多高级用法和详细配置，请参考官方文档。