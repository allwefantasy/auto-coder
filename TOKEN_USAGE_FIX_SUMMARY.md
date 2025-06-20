# Token Usage 显示问题修复总结

## 问题描述
用户报告 Token usage 显示有问题，出现类似 `<byzerllm.utils.types.SingleOutputMeta object at 0x1542afad0>` 的对象引用显示，而不是实际的 token 使用信息。

## 问题原因
在原来的代码中，`token_usage` 事件的处理直接打印了 `SingleOutputMeta` 对象而没有提取其具体属性值，导致显示对象引用而非有意义的信息。

## 修复方案

### 1. 添加累计 Token 使用功能

在 `AutoCoderCore` 类中添加了累计 token 使用情况的功能：

```python
# 初始化时添加累计 token 使用状态
self._accumulated_token_usage = {
    "model_name": "",
    "input_tokens": 0,
    "output_tokens": 0,
    "input_cost": 0.0,
    "output_cost": 0.0
}
```

### 2. 正确处理 TokenUsageEvent

实现了 `_process_token_usage_event` 方法来正确提取 `SingleOutputMeta` 对象的属性：

```python
def _process_token_usage_event(self, usage):
    # 正确提取 SingleOutputMeta 对象的属性
    input_tokens = getattr(usage, 'input_tokens_count', 0)
    output_tokens = getattr(usage, 'generated_tokens_count', 0)
    
    # 获取模型信息用于定价计算
    # 计算成本并累计到总使用量中
    # 显示当前的 token 使用情况
```

### 3. 添加 WindowLengthChangeEvent 处理

参考 `agentic_edit.py` 中的处理方式，添加了对窗口长度变化事件的支持：

```python
elif 'WindowLengthChangeEvent' in event_class_name:
    tokens_used = getattr(event, 'tokens_used', 0)
    if tokens_used > 0:
        self._console.print(f"[dim]当前会话总 tokens: {tokens_used}[/dim]")
```

### 4. 增强事件类型处理

使用动态检查的方式来处理新的事件类型，避免导入依赖问题：

- `TokenUsageEvent` - 累计并显示 token 使用情况
- `WindowLengthChangeEvent` - 显示当前会话总 tokens
- `LLMThinkingEvent` - 显示 AI 思考过程
- `LLMOutputEvent` - 显示 LLM 输出
- `ToolCallEvent` - 显示工具调用信息
- `ToolResultEvent` - 显示工具执行结果
- `CompletionEvent` - 显示任务完成信息
- `PlanModeRespondEvent` - 显示计划模式响应
- `ErrorEvent` - 显示错误信息
- `ConversationIdEvent` - 显示对话ID

### 5. 最终 Token 使用统计

实现了 `_print_final_token_usage` 方法，在操作完成时打印累计的 token 使用统计：

```python
def _print_final_token_usage(self):
    # 使用 Printer 类打印最终的累计统计
    # 包括输入 tokens、输出 tokens、成本等信息
```

### 6. 在所有主要方法中集成

在以下方法中都添加了 token 使用统计功能：
- `query_stream` - 异步流式查询
- `query_sync` - 同步查询  
- `modify_code` - 代码修改
- `modify_code_stream` - 异步流式代码修改

每个方法在开始时重置统计，在完成或异常时打印最终统计。

## 测试验证

运行集成测试验证修复效果：

```bash
cd examples/sdk_integration_test && python run_tests.py
```

测试结果：
- Python API 测试：✅ 通过 (4/4)
- CLI 测试：✅ 通过 (5/5)
- 总体测试：✅ 通过 (2/2)

## 修复效果

修复后，Token usage 会正确显示为：
- 当前使用：`Token usage: Input=150, Output=75, Total=225`
- 窗口变化：`当前会话总 tokens: 1024`
- 最终统计：使用 Printer 类显示详细的成本和使用情况

而不是原来的对象引用显示。

## 技术细节

1. **动态事件类型检查**：使用 `type(event).__name__` 来检查事件类型，避免导入依赖
2. **属性安全提取**：使用 `getattr(obj, 'attr', default)` 来安全提取对象属性
3. **成本计算**：集成了模型价格信息，计算输入和输出 token 的实际成本
4. **向后兼容**：保持对旧格式事件的支持
5. **错误处理**：在各个环节都添加了适当的异常处理

这个修复方案不仅解决了 Token usage 显示问题，还参考 `agentic_edit.py` 的实现，为 SDK 添加了完整的事件处理和统计功能，提供了更好的用户体验。 