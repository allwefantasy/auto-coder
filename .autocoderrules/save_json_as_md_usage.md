---
description: 标准化日志保存方法，用于保存格式化的JSON日志为Markdown格式到项目指定目录
globs: ["*/*.py"]
alwaysApply: false
---

# 格式化日志保存标准方法 save_formatted_log

## 简要说明
`save_formatted_log` 函数提供了一种标准化的方式来保存各种类型的JSON格式日志到项目的`.cache/logs`目录中，特别适用于保存RAG对话、模型响应、调试信息等需要后续分析的数据。

## 典型用法

```python
# 导入必要的库
import json
from autocoder.common.save_formatted_log import save_formatted_log

# 基本用法 - 保存RAG对话日志
try:
    # 准备要保存的数据
    conversations = [
        {"role": "user", "content": "如何使用Python读取文件？"},
        {"role": "assistant", "content": "在Python中，你可以使用open()函数读取文件..."}
    ]
    
    # 将数据转换为JSON字符串
    json_text = json.dumps(conversations, ensure_ascii=False)
    
    # 保存日志（指定项目根目录和日志类型）
    project_root = "/path/to/project"  # 通常从args.source_dir获取
    save_formatted_log(project_root, json_text, "rag_conversation")
    
    # 日志将被保存到: /path/to/project/.cache/logs/rag_conversation_YYYYMMDD_HHMMSS.json
except Exception as e:
    logger.warning(f"保存日志失败: {e}")
```

## 高级用法

```python
# 在LongContextRAG中的实际应用示例
def stream_chat_oai(self, conversations, ...):
    # ... 前面的代码省略 ...
    
    # 创建RAG对话并准备发送给模型
    qa_strategy = get_qa_strategy(self.args)
    new_conversations = qa_strategy.create_conversation(
        documents=[doc.source_code for doc in relevant_docs],
        conversations=conversations, 
        local_image_host=self.args.local_image_host
    )

    # 保存生成的RAG对话到日志文件
    try:                    
        logger.info(f"Saving new_conversations log to {self.args.source_dir}/.cache/logs")
        project_root = self.args.source_dir
        json_text = json.dumps(new_conversations, ensure_ascii=False)
        save_formatted_log(project_root, json_text, "rag_conversation")
    except Exception as e:
        logger.warning(f"Failed to save new_conversations log: {e}")
    
    # 发送到模型并处理响应
    # ... 后续代码省略 ...
```

## 参数说明

`save_formatted_log`函数接受三个参数:

1. `project_root` (str): 项目根目录路径，日志将保存在此目录下的`.cache/logs`文件夹中
2. `content` (str): 要保存的内容，通常是JSON格式的字符串
3. `type_name` (str): 日志类型名称，将作为生成的日志文件名前缀

## 日志文件命名

生成的日志文件将按以下格式命名:
```
{project_root}/.cache/logs/{type_name}_{timestamp}.json
```

其中`timestamp`格式为`YYYYMMDD_HHMMSS`，确保每个日志文件名唯一。

## 最佳实践

1. **总是进行异常处理**: 由于日志保存涉及文件操作，应始终使用try-except包裹相关代码
2. **提供有意义的类型名**: 使用描述性的`type_name`参数，以便于后续查找和分析特定类型的日志
3. **避免敏感信息**: 确保保存的日志不包含API密钥等敏感信息
4. **使用ensure_ascii=False**: 设置`json.dumps(data, ensure_ascii=False)`以正确保存中文字符

## 学习来源
该规则提取自`src/autocoder/rag/long_context_rag.py`中的`_stream_chat_oai`方法，该方法演示了如何在RAG处理流程中保存格式化的对话日志，便于后续调试和分析。 