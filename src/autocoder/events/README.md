# 事件内容格式参考

下面详细列出了各种事件内容类型的完整格式，包括所有字段、数据类型及示例值。这些格式展示了各种内容类型序列化为JSON后的结构。

## 基础事件格式

所有事件对象具有以下基本结构：

```json
{
  "event_id": "8f9e5a3c-a1b2-4c3d-9e8f-7a6b5c4d3e2f",
  "event_type": "RESULT",  // 事件类型: RESULT, STREAM, ASK_USER, USER_RESPONSE, SYSTEM_COMMAND, ERROR
  "timestamp": 1626888000.0,
  "content": {
    // 具体内容，根据不同的内容类型有不同的结构，详见下方
  }
}
```

对于响应事件，还会有额外的 `response_to` 字段：

```json
{
  "event_id": "8f9e5a3c-a1b2-4c3d-9e8f-7a6b5c4d3e2f",
  "event_type": "USER_RESPONSE",
  "timestamp": 1626888000.0,
  "content": {
    // 响应内容
  },
  "response_to": "1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p"  // 引用的询问事件ID
}
```

## 1. BaseEventContent

这是所有内容类型的基类，包含通用字段：

```json
{
  "timestamp": 1626888000.0
}
```

## 2. StreamContent

用于流式传输的内容，可以表示思考过程或正式输出：

```json
{
  "timestamp": 1626888000.0,
  "state": "content",  // 可选值: "thinking", "content", "complete"
  "content": "正在处理请求...",
  "content_type": "text",  // 可选值: "text", "code", "image", "json", "html", "markdown"
  "sequence": 1,  // 序列号，用于排序
  "is_thinking": false  // 是否是思考过程
}
```

完整事件示例：

```json
{
  "event_id": "8f9e5a3c-a1b2-4c3d-9e8f-7a6b5c4d3e2f",
  "event_type": "STREAM",
  "timestamp": 1626888000.0,
  "content": {
    "timestamp": 1626888000.0,
    "state": "thinking",
    "content": "正在分析数据结构...",
    "content_type": "text",
    "sequence": 1,
    "is_thinking": true
  }
}
```

## 3. ResultContent

表示处理完成的结果：

```json
{
  "timestamp": 1626888000.0,
  "content": "处理已完成",  // 可以是字符串或任何JSON可序列化的对象
  "content_type": "text",  // 可选值: "text", "code", "image", "json", "html", "markdown"
  "metadata": {
    "processing_time": 1.23,
    "status": "success",
    "items_processed": 50
    // 可以包含任何额外信息
  }
}
```

完整事件示例：

```json
{
  "event_id": "8f9e5a3c-a1b2-4c3d-9e8f-7a6b5c4d3e2f",
  "event_type": "RESULT",
  "timestamp": 1626888000.0,
  "content": {
    "timestamp": 1626888000.0,
    "content": "文件分析已完成",
    "content_type": "text",
    "metadata": {
      "file_count": 25,
      "total_lines": 1520,
      "execution_time": 0.87,
      "success": true
    }
  }
}
```

## 4. AskUserContent

用于请求用户提供输入：

```json
{
  "timestamp": 1626888000.0,
  "prompt": "您想继续执行下一步操作吗?",
  "options": ["是", "否", "稍后再说"],  // 可选，提供选项列表
  "default_option": "是",  // 可选，默认选项
  "required": true,  // 是否必须回答
  "timeout": 60.0  // 超时时间（秒），可选
}
```

完整事件示例：

```json
{
  "event_id": "1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p",
  "event_type": "ASK_USER",
  "timestamp": 1626888000.0,
  "content": {
    "timestamp": 1626888000.0,
    "prompt": "检测到配置文件冲突，如何处理?",
    "options": ["使用新版本", "保留现有版本", "合并配置"],
    "default_option": "合并配置",
    "required": true,
    "timeout": 120.0
  }
}
```

## 5. UserResponseContent

用于表示用户对询问的回应：

```json
{
  "timestamp": 1626888000.0,
  "response": "是",  // 用户的回答
  "response_time": 1626888030.0,  // 回答的时间戳
  "original_prompt": "您想继续执行下一步操作吗?"  // 可选，原始提问
}
```

完整事件示例：

```json
{
  "event_id": "8f9e5a3c-a1b2-4c3d-9e8f-7a6b5c4d3e2f",
  "event_type": "USER_RESPONSE",
  "timestamp": 1626888030.0,
  "content": {
    "timestamp": 1626888030.0,
    "response": "使用新版本",
    "response_time": 1626888030.0,
    "original_prompt": "检测到配置文件冲突，如何处理?"
  },
  "response_to": "1a2b3c4d-5e6f-7g8h-9i0j-1k2l3m4n5o6p"
}
```

## 6. CodeContent

专门用于代码内容，继承自 StreamContent：

```json
{
  "timestamp": 1626888000.0,
  "state": "content",  // 可选值: "thinking", "content", "complete"
  "content": "def hello():\n    print('Hello, world!')",
  "content_type": "code",  // 固定为 "code"
  "language": "python",  // 代码语言
  "sequence": 1,
  "is_thinking": false
}
```

完整事件示例：

```json
{
  "event_id": "8f9e5a3c-a1b2-4c3d-9e8f-7a6b5c4d3e2f",
  "event_type": "STREAM",
  "timestamp": 1626888000.0,
  "content": {
    "timestamp": 1626888000.0,
    "state": "content",
    "content": "function calculateTotal(items) {\n  return items.reduce((sum, item) => sum + item.price, 0);\n}",
    "content_type": "code",
    "language": "javascript",
    "sequence": 5,
    "is_thinking": false
  }
}
```

## 7. MarkdownContent

专门用于 Markdown 内容，继承自 StreamContent：

```json
{
  "timestamp": 1626888000.0,
  "state": "content",  // 可选值: "thinking", "content", "complete"
  "content": "# 标题\n这是一段**Markdown**内容\n\n- 列表项1\n- 列表项2",
  "content_type": "markdown",  // 固定为 "markdown"
  "sequence": 1,
  "is_thinking": false
}
```

完整事件示例：

```json
{
  "event_id": "8f9e5a3c-a1b2-4c3d-9e8f-7a6b5c4d3e2f",
  "event_type": "STREAM",
  "timestamp": 1626888000.0,
  "content": {
    "timestamp": 1626888000.0,
    "state": "content",
    "content": "## 操作步骤\n\n1. 安装依赖: `npm install`\n2. 配置环境: 复制 `.env.example` 到 `.env`\n3. 启动服务: `npm start`\n\n> 注意: 确保数据库已初始化",
    "content_type": "markdown",
    "sequence": 6,
    "is_thinking": false
  }
}
```

## 8. ErrorContent

用于表示错误情况：

```json
{
  "timestamp": 1626888000.0,
  "error_code": "E1001",  // 错误代码
  "error_message": "处理失败: 无效的输入数据",  // 错误消息
  "details": {  // 详细错误信息，可选
    "location": "process_data",
    "reason": "invalid input",
    "input_value": "xyz",
    "expected_format": "number"
  }
}
```

完整事件示例：

```json
{
  "event_id": "8f9e5a3c-a1b2-4c3d-9e8f-7a6b5c4d3e2f",
  "event_type": "RESULT",  // 注意: ErrorContent 通常作为 RESULT 事件的内容
  "timestamp": 1626888000.0,
  "content": {
    "timestamp": 1626888000.0,
    "error_code": "DATA_VALIDATION_ERROR",
    "error_message": "数据格式验证失败，缺少必要字段",
    "details": {
      "operation": "data_validation",
      "input_data": {"size": 1024, "format": "json"},
      "expected_schema": "user_profile", 
      "error_location": "line 42",
      "missing_fields": ["name", "email"],
      "timestamp": 1626888000.0
    }
  }
}
```

## 9. CompletionContent

用于表示事件或操作正常完成的情况：

```json
{
  "timestamp": 1626888000.0,
  "success_code": "S1001",  // 成功代码
  "success_message": "操作成功完成",  // 成功消息
  "result": {  // 操作结果，可选
    "items_processed": 50,
    "warnings": 0,
    "artifacts": ["file1.txt", "file2.txt"]
  },
  "details": {  // 详细信息，可选
    "operation": "data_sync",
    "duration": 120.5,
    "start_time": 1626887880.0,
    "end_time": 1626888000.0
  },
  "completion_time": 1626888000.0  // 完成时间戳
}
```

完整事件示例：

```json
{
  "event_id": "8f9e5a3c-a1b2-4c3d-9e8f-7a6b5c4d3e2f",
  "event_type": "RESULT",  // 注意: CompletionContent 通常作为 RESULT 事件的内容
  "timestamp": 1626888000.0,
  "content": {
    "timestamp": 1626888000.0,
    "success_code": "BUILD_COMPLETE",
    "success_message": "项目构建成功",
    "result": {
      "files_generated": 15,
      "total_size": "2.4MB",
      "warnings": 2,
      "output_directory": "./dist"
    },
    "details": {
      "operation": "project_build",
      "start_time": 1626887850.0,
      "end_time": 1626888000.0,
      "duration": 150.0,
      "environment": "production",
      "build_id": "build-20230815-001"
    },
    "completion_time": 1626888000.0
  }
}
```

## 使用工厂函数创建内容

提供了多个工厂函数简化内容创建，创建后需要调用 `to_dict()` 转换为字典再传递给事件管理器：

```python
# 示例: 创建错误内容并写入事件
from autocoder.events import get_event_manager, create_error

error_content = create_error(
    error_code="FILE_NOT_FOUND",
    error_message="找不到指定文件",
    details={"path": "/tmp/data.json", "operation": "read"}
)

event_manager = get_event_manager()
event_manager.write_result(error_content.to_dict())
```
