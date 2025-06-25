

# Pruner Module Tests

本目录包含 AutoCoder Pruner 模块的测试文件，包括原始测试和新的 pytest 标准测试。

## 测试文件说明

### 原始测试文件
- `test_agentic_conversation_pruner.py` - 原始的测试文件，包含基本的功能测试

### 新的 Pytest 测试文件
- `test_agentic_conversation_pruner_pytest.py` - 转换为 pytest 标准的完整测试套件

### 配置文件
- `pytest.ini` - Pytest 配置文件
- `TEST_README.md` - 本文档

## 运行测试

### 1. 安装依赖

确保已安装必要的测试依赖：

```bash
pip install pytest pytest-mock
```

### 2. 运行所有测试

在 pruner 目录下运行：

```bash
# 运行所有 pytest 测试
pytest test_agentic_conversation_pruner_pytest.py -v

# 或者运行所有测试文件
pytest . -v
```

### 3. 运行特定测试

```bash
# 运行特定测试类
pytest test_agentic_conversation_pruner_pytest.py::TestAgenticConversationPruner -v

# 运行特定测试方法
pytest test_agentic_conversation_pruner_pytest.py::TestAgenticConversationPruner::test_initialization -v

# 运行参数化测试
pytest test_agentic_conversation_pruner_pytest.py::TestParametrized -v
```

### 4. 运行带标记的测试

```bash
# 运行单元测试
pytest -m unit -v

# 运行集成测试
pytest -m integration -v

# 运行参数化测试
pytest -m parametrized -v
```

### 5. 生成测试报告

```bash
# 生成详细的测试报告
pytest test_agentic_conversation_pruner_pytest.py --tb=long -v

# 生成覆盖率报告（需要安装 pytest-cov）
pip install pytest-cov
pytest test_agentic_conversation_pruner_pytest.py --cov=autocoder.common.pruner.agentic_conversation_pruner --cov-report=html
```

### 6. 运行原始测试

如果需要运行原始测试文件：

```bash
python test_agentic_conversation_pruner.py
```

## 测试结构说明

### TestAgenticConversationPruner 类
主要的测试类，包含：

- **Fixtures**: 
  - `mock_args`: 模拟的 AutoCoderArgs
  - `mock_llm`: 模拟的 LLM 实例
  - `pruner`: AgenticConversationPruner 实例
  - `sample_conversations`: 示例对话数据

- **核心功能测试**:
  - 初始化测试
  - 策略获取测试
  - 对话裁剪测试（超限和未超限情况）
  - 工具结果检测测试
  - 工具名称提取测试
  - 替换消息生成测试
  - 清理统计测试

- **边界情况测试**:
  - 无效策略处理
  - 空对话列表
  - 无工具结果的对话
  - 渐进式清理
  - 各种边界情况

### TestAgenticConversationPrunerIntegration 类
集成测试类，测试真实场景下的模块行为。

### TestParametrized 类
参数化测试类，使用 pytest 的参数化功能进行全面测试覆盖。

## 测试特点

### 1. 完整的模拟 (Mocking)
- 使用 `unittest.mock.MagicMock` 模拟外部依赖
- 使用 `@patch` 装饰器模拟 token 计数功能
- 确保测试的独立性和可重复性

### 2. 全面的覆盖
- 测试所有公共方法和重要的私有方法
- 包含正常流程、异常情况和边界条件
- 使用参数化测试确保各种输入的正确处理

### 3. 清晰的断言
- 每个测试都有明确的断言
- 包含描述性的错误消息
- 验证预期行为和输出

### 4. 良好的组织
- 使用 pytest fixtures 管理测试数据
- 按功能分组测试方法
- 清晰的测试方法命名

## 测试最佳实践

### 1. 运行测试前
- 确保环境中安装了所有必要的依赖
- 检查当前工作目录是否正确

### 2. 编写新测试
- 遵循现有的测试结构和命名约定
- 使用适当的 fixtures 和 mocking
- 添加清晰的文档字符串

### 3. 调试测试
- 使用 `-v` 选项获取详细输出
- 使用 `--tb=long` 获取完整的错误追踪
- 使用 `--pdb` 在失败时进入调试器

### 4. 持续集成
- 确保所有测试在 CI/CD 环境中都能通过
- 定期运行完整的测试套件
- 监控测试覆盖率

## 故障排除

### 常见问题

1. **ImportError**: 确保 PYTHONPATH 包含项目根目录
2. **ModuleNotFoundError**: 检查依赖是否正确安装
3. **Mock 相关错误**: 验证 mock 对象的配置是否正确
4. **Assertion 错误**: 检查测试数据和预期结果是否匹配

### 调试技巧

```bash
# 运行单个失败的测试
pytest test_agentic_conversation_pruner_pytest.py::test_method_name -v -s

# 进入调试器
pytest test_agentic_conversation_pruner_pytest.py::test_method_name --pdb

# 显示所有输出
pytest test_agentic_conversation_pruner_pytest.py -v -s --tb=long
```

## 贡献指南

如果需要添加新的测试：

1. 在适当的测试类中添加新的测试方法
2. 使用描述性的方法名（以 `test_` 开头）
3. 添加清晰的文档字符串
4. 使用适当的 fixtures 和断言
5. 确保测试是独立的和可重复的
6. 运行测试确保通过

