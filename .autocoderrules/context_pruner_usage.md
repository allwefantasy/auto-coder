---
description: 解释如何使用PruneContext类和ConversationPruner类进行智能上下文管理 — PruneContext基于用户对话智能抽取大文件内容，ConversationPruner优化长对话历史，两者协同减少Token消耗并保留最相关内容。
globs:
  - "**/*.py"  
alwaysApply: false
---

# Context Pruner 使用指南

`PruneContext` 类提供了基于对话内容的智能上下文裁剪功能，它通过分析用户的查询和对话来判断哪些代码片段最相关，从而智能抽取大型文件中的关键内容，确保在保留最相关内容的同时减少 LLM 输入的 token 消耗。

## 关键步骤：

1. **初始化 PruneContext**：创建裁剪器实例，指定 token 限制、参数和 LLM 模型。
   ```python
   from autocoder.common.context_pruner import PruneContext
   from autocoder.common import AutoCoderArgs
   
   context_pruner = PruneContext(
       max_tokens=8000,  # 最大允许的 token 数
       args=args,        # AutoCoderArgs 实例
       llm=llm           # ByzerLLM 或 SimpleByzerLLM 实例
   )
   ```

2. **处理文件集合**：使用 `handle_overflow` 方法处理文件列表，选择合适的裁剪策略，并传入对话内容用于智能分析。
   ```python
   pruned_files = context_pruner.handle_overflow(
       file_sources,                  # 源文件列表 (SourceCode 对象)
       conversations,                 # 对话上下文，用于智能评估相关性和抽取
       strategy="score"               # 裁剪策略：score/delete/extract
   )
   ```

3. **裁剪策略选择**：
   * `score`：通过对话分析对文件进行相关性评分，保留分数最高的文件
   * `delete`：简单地从列表开始移除文件，直到满足 token 限制
   * `extract`：**基于用户对话内容**智能提取每个文件中的关键代码片段，是处理大文件的推荐方式

## 对话驱动的代码抽取

`extract` 策略尤为重要，它能根据当前对话内容分析并仅提取大文件中最相关的代码片段：

```python
# 使用extract策略进行智能代码片段抽取
extracted_files = context_pruner.handle_overflow(
    file_sources, 
    [{"role": "user", "content": "如何实现登录功能？"}],  # 用户对话内容
    strategy="extract"
)
```

该方法会分析用户的问题，从源文件中仅提取与"登录功能"相关的代码片段，甚至可以处理上百MB的大文件，智能提取最相关部分。

## 在 build_index_and_filter_files 中的使用示例：

```python
# 开启了裁剪，则需要做裁剪
if args.context_prune:
    context_pruner = PruneContext(
        max_tokens=args.conversation_prune_safe_zone_tokens, 
        args=args, 
        llm=llm
    )
    
    # 根据文件位置排序（如果有位置信息）
    if file_positions:
        # 排序逻辑...
        
    # 执行裁剪处理，传入用户查询作为对话内容
    pruned_files = context_pruner.handle_overflow(
        temp_sources, 
        [{"role": "user", "content": args.query}],  # 用户查询作为对话内容
        args.context_prune_strategy
    )
    source_code_list.sources = pruned_files
```

## 配置参数说明：

* `args.context_prune`：是否启用上下文裁剪（布尔值）
* `args.conversation_prune_safe_zone_tokens`：裁剪后最大允许的 token 数
* `args.context_prune_strategy`：裁剪策略（"score"/"delete"/"extract"）
* `args.context_prune_sliding_window_size`：滑动窗口大小（用于大文件分析）
* `args.context_prune_sliding_window_overlap`：滑动窗口重叠行数

注意在调用裁剪功能前，确保每个 SourceCode 对象已正确计算其 tokens 属性，以便更准确地进行裁剪决策。 

# Conversation Pruner 使用指南

`ConversationPruner` 类提供了对话历史裁剪功能，用于处理长时间对话中积累的历史信息，避免超出 token 限制，同时保留关键上下文内容。

## 关键步骤：

1. **初始化 ConversationPruner**：创建对话裁剪器实例。
   ```python
   from autocoder.common.conversation_pruner import ConversationPruner
   from autocoder.common import AutoCoderArgs
   
   pruner = ConversationPruner(
       args=args,        # AutoCoderArgs 实例
       llm=llm           # ByzerLLM 或 SimpleByzerLLM 实例
   )
   ```

2. **对话裁剪**：当对话长度超出限制时，使用 `prune_conversations` 方法裁剪对话历史。
   ```python
   pruned_conversations = pruner.prune_conversations(
       conversations,                  # 对话历史列表
       strategy_name="summarize"       # 裁剪策略：summarize/truncate/hybrid
   )
   ```

3. **裁剪策略选择**：
   * `summarize`：对早期对话进行分组摘要，保留关键信息
   * `truncate`：分组截断最早的部分对话
   * `hybrid`：先尝试分组摘要，如果仍超限则分组截断

## 在 auto_command.py 中的使用示例：

```python
# 统计 token 数量
total_tokens = count_tokens(json.dumps(conversations, ensure_ascii=False))

# 如果对话过长，使用默认策略进行修剪
if total_tokens > self.args.conversation_prune_safe_zone_tokens:
    self.printer.print_in_terminal(
        "conversation_pruning_start",
        style="yellow",
        total_tokens=total_tokens,
        safe_zone=self.args.conversation_prune_safe_zone_tokens
    )
    from autocoder.common.conversation_pruner import ConversationPruner
    pruner = ConversationPruner(self.args, self.llm)
    conversations = pruner.prune_conversations(conversations)
```

## 配置参数说明：

* `args.conversation_prune_safe_zone_tokens`：裁剪后最大允许的 token 数
* `args.conversation_prune_group_size`：处理对话时的分组大小

# Context Pruner 与 Conversation Pruner 的使用场景对比

两种裁剪器虽然目标相似（减少 token 消耗），但应用场景和处理对象不同：

## Context Pruner
* **处理对象**：源代码文件内容
* **使用时机**：在执行 RAG 或索引查询前，对检索到的文件内容进行裁剪
* **特色功能**：基于用户对话/查询智能抽取大文件中的相关代码片段
* **主要场景**：
  - 在将大量文件用作 LLM 上下文前进行智能筛选
  - 只保留与当前查询最相关的文件或代码片段
  - 用于 build_index_and_filter_files 等文件处理流程中

## Conversation Pruner
* **处理对象**：历史对话记录
* **使用时机**：在多轮对话过程中，当累积的对话历史超出 token 限制时
* **主要场景**：
  - 长时间运行的对话 agent 中维持对话连贯性
  - 保持重要上下文的同时减少 token 消耗
  - 用于 auto_command 等涉及多轮交互的场景

## 实践建议
* 同时使用两种裁剪器可以全面控制 token 消耗
* Context Pruner 侧重于"基于对话内容选择什么文件/代码片段提供给 LLM"
* Conversation Pruner 侧重于"如何压缩/管理长时间积累的对话历史" 