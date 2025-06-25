

# 测试迁移指南：从原始测试到 Pytest

本文档说明了如何从原始的 `test_agentic_conversation_pruner.py` 迁移到标准的 pytest 测试结构。

## 迁移概述

### 原始测试文件特点
- 使用简单的函数定义测试
- 手动运行和验证
- 基本的 print 输出
- 缺乏结构化的断言

### 新 Pytest 测试特点
- 使用类和方法组织测试
- 标准的 pytest fixtures
- 完整的断言和错误处理
- 参数化测试支持
- 集成测试和单元测试分离

## 具体迁移对比

### 1. 测试结构对比

**原始测试:**
```python
def test_agentic_conversation_pruner():
    """Test the agentic conversation pruner functionality"""
    # Mock args and llm
    args = MagicMock()
    args.conversation_prune_safe_zone_tokens = 1000
    llm = MagicMock()
    
    # Create pruner instance
    pruner = AgenticConversationPruner(args=args, llm=llm)
    # ... 测试逻辑
```

**新 Pytest 测试:**
```python
class TestAgenticConversationPruner:
    @pytest.fixture
    def mock_args(self):
        args = MagicMock(spec=AutoCoderArgs)
        args.conversation_prune_safe_zone_tokens = 1000
        return args

    @pytest.fixture
    def pruner(self, mock_args, mock_llm):
        return AgenticConversationPruner(args=mock_args, llm=mock_llm)

    def test_initialization(self, mock_args, mock_llm):
        # 使用 fixtures 进行测试
```

### 2. 断言对比

**原始测试:**
```python
# 手动验证和打印
tool_result_found = False
cleaned_tool_result_found = False

for conv in pruned_conversations:
    if conv.get("role") == "user" and "<tool_result" in conv.get("content", ""):
        if "This message has been cleared" in conv.get("content", ""):
            cleaned_tool_result_found = True
        else:
            tool_result_found = True

print(f"\nTool results cleaned: {cleaned_tool_result_found}")
print(f"Original tool results remaining: {tool_result_found}")
```

**新 Pytest 测试:**
```python
# 标准断言
cleaned_found = False
for conv in result:
    if conv.get("role") == "user" and "<tool_result" in conv.get("content", ""):
        if "This message has been cleared" in conv.get("content", ""):
            cleaned_found = True
            break

assert cleaned_found, "Expected to find cleaned tool results"
```

### 3. 测试数据管理对比

**原始测试:**
```python
def test_tool_name_extraction():
    pruner = AgenticConversationPruner(MagicMock(), MagicMock())
    
    test_cases = [
        ("<tool_result tool_name='ReadFileTool' success='true'>", "ReadFileTool"),
        # ... 更多测试用例
    ]
    
    for content, expected in test_cases:
        result = pruner._extract_tool_name(content)
        status = "✓" if result == expected else "✗"
        print(f"{status} '{content[:50]}...' -> '{result}' (expected: '{expected}')")
```

**新 Pytest 测试:**
```python
@pytest.mark.parametrize("tool_name,expected", [
    ("ReadFileTool", "ReadFileTool"),
    ("ListFilesTool", "ListFilesTool"),
    ("WriteTool", "WriteTool"),
    # ... 更多测试用例
])
def test_tool_name_extraction_parametrized(self, tool_name, expected):
    pruner = AgenticConversationPruner(MagicMock(), MagicMock())
    content = f"<tool_result tool_name='{tool_name}' success='true'>"
    result = pruner._extract_tool_name(content)
    assert result == expected
```

## 主要改进

### 1. 结构化组织
- **原始**: 3个独立函数
- **新版**: 3个测试类，13个测试方法，完整覆盖

### 2. 测试覆盖
- **原始**: 基本功能测试
- **新版**: 单元测试 + 集成测试 + 边界测试 + 参数化测试

### 3. 错误处理
- **原始**: 基本的成功/失败检查
- **新版**: 详细的异常测试和边界条件

### 4. 可维护性
- **原始**: 硬编码的测试数据
- **新版**: Fixtures 和参数化测试，易于扩展

### 5. 调试能力
- **原始**: 基本的 print 输出
- **新版**: 详细的断言消息和 pytest 调试支持

## 新增的测试功能

### 1. Fixtures 管理
```python
@pytest.fixture
def sample_conversations(self):
    """可重用的测试数据"""
    return [...]

@pytest.fixture
def pruner(self, mock_args, mock_llm):
    """可重用的测试实例"""
    return AgenticConversationPruner(args=mock_args, llm=mock_llm)
```

### 2. Mock 和 Patch
```python
@patch('autocoder.rag.token_counter.count_tokens')
def test_prune_conversations_exceeds_limit(self, mock_count_tokens, pruner):
    mock_count_tokens.side_effect = [2000, 1500, 800]
    # 测试逻辑
```

### 3. 参数化测试
```python
@pytest.mark.parametrize("content,expected", [
    ("<tool_result tool_name='Test'>", True),
    ("Regular message", False),
])
def test_tool_result_detection(self, content, expected):
    # 测试逻辑
```

### 4. 集成测试
```python
class TestAgenticConversationPrunerIntegration:
    def test_realistic_scenario(self, real_args):
        # 真实场景测试
```

## 运行对比

### 原始测试运行
```bash
python test_agentic_conversation_pruner.py
```
输出：基本的 print 信息，手动验证结果

### 新 Pytest 测试运行
```bash
pytest test_agentic_conversation_pruner_pytest.py -v
```
输出：
- 详细的测试结果
- 清晰的成功/失败状态
- 测试覆盖率信息
- 性能统计

## 迁移建议

### 1. 保留原始测试
- 作为参考和对比
- 用于快速验证基本功能

### 2. 使用新 Pytest 测试
- 日常开发和 CI/CD
- 详细的功能验证
- 回归测试

### 3. 逐步扩展
- 根据需要添加新的测试用例
- 增加更多的边界条件测试
- 提高测试覆盖率

### 4. 最佳实践
- 使用 fixtures 管理测试数据
- 合理使用 mock 和 patch
- 编写清晰的断言消息
- 定期运行完整的测试套件

## 总结

新的 pytest 测试提供了：
- ✅ 更好的结构化组织
- ✅ 更全面的测试覆盖
- ✅ 更强的可维护性
- ✅ 更好的调试能力
- ✅ 标准的测试框架支持

建议在日常开发中使用新的 pytest 测试，同时保留原始测试作为参考。


