# LongContextRAG API

## 初始化

```python
rag = LongContextRAG(llm, args, path)
```

## 主要方法

- `search(query)`: 搜索相关文档
- `stream_chat_oai(conversations)`: 流式问答交互