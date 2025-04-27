
---
description: 标准化事件系统用法，用于模块间解耦通信和记录交互。
globs: ["src/**/*.py"] # 适用于需要记录事件或进行事件驱动通信的模块
alwaysApply: false
---

# 标准化事件系统使用指南

## 简要说明
本规则定义了使用基于文件存储的事件系统进行模块间通信或记录详细交互过程的标准方法。核心组件包括事件管理器 (`EventManager`)、结构化事件内容 (`event_content`) 和事件存储 (`EventStore`)。该系统通过单例模式 (`get_event_manager`) 提供访问点，使用 Pydantic 模型定义事件内容，并通过专门的方法写入不同类型的事件（如流式输出、最终结果、错误、完成状态）。适用于需要详细追踪操作流程、实现系统解耦、或进行异步/事件驱动交互的场景。

## 典型用法
```python
import os
import time
from autocoder.events import (
    get_event_manager,
    create_stream_thinking,
    create_stream_content,
    create_result,
    create_markdown_result,
    create_error,
    create_completion,
    EventType # Optional: If you need to read/filter events
)
from autocoder.events.event_types import EventMetadata # For adding metadata

# 1. 获取 EventManager 实例
# 通常需要指定一个事件文件路径，用于隔离不同会话或任务的事件流
# 如果不指定，会使用默认实例（可能用于全局事件）
event_file_path = ".auto-coder/events/my_task_session.jsonl"
event_manager = get_event_manager(event_file_path)

# [可选] 清空之前的事件记录 (谨慎使用)
# event_manager.truncate()

# 2. 定义元数据 (可选但推荐)
# 元数据可以帮助追踪事件来源和上下文
metadata = EventMetadata(
    action_file="src/my_module/my_processor.py", # 事件发生的源文件
    path="/my_module/process_data", # 逻辑路径或标识符
    stream_out_type="/my_module/output" # 事件流的用途分类
)

# 3. 记录不同类型的事件

# 3.1 记录思考过程 (流式事件)
thinking_content = create_stream_thinking("正在分析输入数据结构...", sequence=1)
event_manager.write_stream(content=thinking_content.to_dict(), metadata=metadata.to_dict())
time.sleep(0.1) # 模拟处理

# 3.2 记录中间输出 (流式事件)
stream_output = create_stream_content("数据结构分析完成，发现 3 个关键点。", sequence=2)
event_manager.write_stream(content=stream_output.to_dict(), metadata=metadata.to_dict())
time.sleep(0.1)

# 3.3 记录最终结果 (结果事件)
# 可以是简单文本，也可以是结构化数据 (Pydantic 模型需先转 dict)
result_data = {"processed_items": 100, "valid": True}
result_content = create_result(content=result_data, metadata={"source": "data_processor"})
# 合并基础元数据和特定元数据
combined_metadata = {**metadata.to_dict(), **result_content.metadata}
event_manager.write_result(content=result_content.to_dict(), metadata=combined_metadata)

# 3.4 记录 Markdown 格式的结果 (结果事件)
markdown_report = """
# 分析报告
- 处理了 **100** 个项目。
- 验证状态: **成功**
"""
md_result_content = create_markdown_result(content=markdown_report, metadata={"report_version": "1.0"})
combined_metadata_md = {**metadata.to_dict(), **md_result_content.metadata}
event_manager.write_result(content=md_result_content.to_dict(), metadata=combined_metadata_md)


# 3.5 记录错误情况 (错误事件)
try:
    # 模拟一个可能出错的操作
    # raise ValueError("输入格式不兼容")
    pass # 假设这里没有错误
except Exception as e:
    error_content = create_error(
        error_code="PROCESSING_ERROR",
        error_message=f"处理数据时发生错误: {str(e)}",
        details={"input_sample": "...", "exception_type": type(e).__name__}
    )
    event_manager.write_error(content=error_content.to_dict(), metadata=metadata.to_dict())

# 3.6 记录操作成功完成 (完成事件)
# 只有在没有发生错误时才记录完成
if 'error_content' not in locals(): # 检查是否发生了错误
    completion_content = create_completion(
        success_code="PROCESS_COMPLETE",
        success_message="数据处理流程成功完成",
        result={"output_path": "/path/to/results.csv"},
        details={"total_duration": 0.2}
    )
    event_manager.write_completion(content=completion_content.to_dict(), metadata=metadata.to_dict())

# 4. 关闭事件管理器 (如果需要释放资源，虽然通常由应用生命周期管理)
# event_manager.close()

print(f"事件已记录到: {os.path.abspath(event_file_path)}")

# 注意: 关于 ask_user 和 respond_to_user
这两个方法 (`ask_user` 和 `respond_to_user`) 用于实现 **同步** 的用户交互。

- **`ask_user(question: str, options: Optional[List[str]] = None, timeout: Optional[float] = None) -> str`**:
    - 写入一个 `ASK_USER` 类型的事件，包含问题文本 (`question`) 和可选的选项列表 (`options`)。
    - **阻塞** 当前执行线程，等待一个具有匹配 `ask_event_id` 的 `RESPOND_TO_USER` 事件被写入（或者直到 `timeout` 超时）。
    - 这个机制依赖于一个外部组件（例如，用户界面、另一个进程或服务）来监听 `ASK_USER` 事件，向用户呈现问题和选项，收集用户的响应，然后调用 `respond_to_user` 方法将响应写回事件流。
    - 如果在指定的 `timeout` 秒内没有收到响应，会引发 `TimeoutError`。
    - 成功时返回用户提供的响应字符串 (`response`)。

- **`respond_to_user(response: str, ask_event_id: str)`**:
    - 写入一个 `RESPOND_TO_USER` 类型的事件，包含用户的回答 (`response`) 和与之对应的原始 `ASK_USER` 事件的唯一标识符 (`ask_event_id`)。
    - 此方法本身 **不阻塞**。它的主要作用是记录用户的响应，并 **解除** 对应 `ask_user` 调用的阻塞状态，允许之前的阻塞线程继续执行。

**使用场景:**
这种同步交互模式适用于需要暂停自动化流程，等待用户明确输入或确认后才能继续执行的场景。例如，在代码生成过程中请求用户澄清模糊的需求，或者在执行破坏性操作前请求用户确认。

**复杂性与注意事项:**
- **阻塞行为**: `ask_user` 的阻塞特性意味着调用它的线程会暂停，直到收到响应或超时。这在设计并发或响应式系统时需要特别注意。
- **外部依赖**: 该机制的完整功能依赖于一个能处理用户交互并调用 `respond_to_user` 的外部系统。仅靠 `EventManager` 本身无法完成整个交互循环。
- **实现**: 正如原始注释所指，这些方法的具体实现和在复杂应用（如 `agentic_edit.py` 所代表的Agentic流程）中的集成可能涉及更复杂的逻辑，例如通过回调或特定的消息队列来管理交互状态。在简单的事件记录场景中，这两个方法通常不被直接使用。
```

## 依赖说明
- **核心依赖**:
    - `autocoder.events` 模块 (项目内部依赖)。
    - `pydantic`: 用于事件内容的模型定义和验证。
- **间接依赖 (由 `autocoder.events` 内部使用)**:
    - `loguru`: 用于日志记录。
    - `readerwriterlock`: 用于 `JsonlEventStore` 的读写锁。
    - Python 标准库: `os`, `json`, `time`, `threading`, `uuid`, `enum`, `dataclasses`, `re`, `glob`, `pathlib`.
- **环境要求**: 标准 Python 3.x 环境。
- **初始化**: 无特殊初始化流程，通过 `get_event_manager(event_file)` 获取实例即可开始使用。事件文件和目录会自动创建。

## 学习来源
该规则提取自以下模块和文件：
- `/Users/allwefantasy/projects/auto-coder/src/autocoder/events/` 目录下的核心模块 (`event_types.py`, `event_content.py`, `event_store.py`, `event_manager.py`, `event_manager_singleton.py`) 定义了整个事件系统的结构和功能。
- `/Users/allwefantasy/projects/auto-coder/src/autocoder/common/v2/agent/agentic_edit.py` 中的 `run_with_events` 方法展示了如何在实际流程中捕获不同阶段的信息并使用 `EventManager` 和 `EventContentCreator` 将其记录为标准事件。
- `/Users/allwefantasy/projects/auto-coder/src/autocoder/events/README.md` 提供了事件内容的详细格式参考。
