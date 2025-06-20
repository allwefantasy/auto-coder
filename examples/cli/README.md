
# Auto-Coder CLI 演示示例

本目录包含了 Auto-Coder CLI 工具的使用演示脚本和示例。

## 文件说明

### demo_cli_usage.sh
CLI 使用演示脚本，展示 `auto-coder.run` 命令的各种功能和用法。

**功能特性：**
- 自动创建演示项目目录
- 演示基本代码生成功能
- 演示代码优化和测试生成
- 演示不同输出格式（text、json）
- 演示工具限制功能
- 自动运行生成的测试
- 彩色输出和错误处理

### demo_python_api.py
Python API 使用演示脚本（计划中），将展示 Auto-Coder SDK 的 Python API 功能。

**计划功能：**
- 同步和异步查询示例
- 代码修改和流式处理
- 会话管理和持久化
- 配置选项和错误处理
- 与 CLI 演示的功能对比

> 注意：此脚本目前为占位符，实际功能将在后续版本中实现。

## 使用方法

### 运行 CLI 演示

```bash
# 进入项目根目录
cd /path/to/auto-coder

# 运行 CLI 演示脚本
./examples/cli/demo_cli_usage.sh
```

### 演示内容

脚本将依次演示以下功能：

1. **基本代码生成**
   - 生成一个 Python 计算器模块
   - 包含类型提示和文档字符串

2. **代码优化**
   - 为计算器添加错误处理
   - 生成对应的单元测试文件

3. **JSON 输出格式**
   - 生成项目 README 文件
   - 演示 JSON 格式输出

4. **工具限制**
   - 限制只使用读取和搜索工具
   - 进行代码分析

5. **测试运行**
   - 自动运行生成的单元测试
   - 显示测试结果

### 生成的项目结构

演示完成后，将在 `examples/cli/simple_project/` 目录下生成以下文件：

```
simple_project/
├── calculator.py          # 计算器模块
├── test_calculator.py     # 单元测试
├── README.md             # 项目说明
└── output.json           # JSON 输出示例
```

## 依赖要求

- 已安装 auto-coder 包：`pip install -e .`
- Python 3.10+ 环境
- 可选：pytest（用于运行测试）
- 可选：tree 命令（用于显示目录结构）

## 命令行选项说明

### auto-coder.run 基本用法

```bash
# 单次运行模式
auto-coder.run -p "Write a function to calculate Fibonacci numbers"

# 通过管道提供输入
echo "Explain this code" | auto-coder.run -p

# 指定输出格式
auto-coder.run -p "Generate a hello world function" --output-format json

# 继续最近的对话
auto-coder.run --continue

# 恢复特定会话
auto-coder.run --resume SESSION_ID
```

### 高级选项

```bash
# 设置最大对话轮数
auto-coder.run -p "Help me debug this code" --max-turns 5

# 指定系统提示
auto-coder.run -p "Create a web API" --system-prompt "You are a backend developer"

# 限制可用工具
auto-coder.run -p "Analyze this file" --allowed-tools read_file search_files

# 设置权限模式
auto-coder.run -p "Fix this bug" --permission-mode acceptEdits

# 详细输出
auto-coder.run -p "Optimize this algorithm" --verbose
```

### 输出格式

- `text`: 纯文本格式（默认）
- `json`: JSON 格式
- `stream-json`: 流式 JSON 格式

### 权限模式

- `manual`: 手动确认每个操作（默认）
- `acceptEdits`: 自动接受文件编辑操作

### 可用工具

- `execute_command`: 执行命令
- `read_file`: 读取文件
- `write_to_file`: 写入文件
- `replace_in_file`: 替换文件内容
- `search_files`: 搜索文件
- `list_files`: 列出文件
- `list_code_definition_names`: 列出代码定义
- `ask_followup_question`: 询问后续问题
- `attempt_completion`: 尝试完成任务
- `list_package_info`: 列出包信息
- `mcp_tool`: MCP 工具
- `rag_tool`: RAG 工具

## 故障排除

### 常见问题

1. **命令未找到错误**
   ```bash
   auto-coder.run: command not found
   ```
   **解决方案：** 确保已正确安装 auto-coder 包：
   ```bash
   pip install -e .
   ```

2. **权限被拒绝**
   ```bash
   Permission denied: ./examples/cli/demo_cli_usage.sh
   ```
   **解决方案：** 添加执行权限：
   ```bash
   chmod +x examples/cli/demo_cli_usage.sh
   ```

3. **测试运行失败**
   ```bash
   pytest: command not found
   ```
   **解决方案：** 安装 pytest：
   ```bash
   pip install pytest
   ```

## 扩展用法

### 自定义演示脚本

您可以基于 `demo_cli_usage.sh` 创建自己的演示脚本：

1. 复制脚本文件
2. 修改项目名称和演示内容
3. 添加自定义的 prompt 和功能演示
4. 调整输出格式和工具限制

### 集成到 CI/CD

可以将演示脚本集成到持续集成流程中：

```yaml
# .github/workflows/demo.yml
name: CLI Demo Test
on: [push, pull_request]
jobs:
  demo:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Setup Python
        uses: actions/setup-python@v2
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -e .
      - name: Run CLI demo
        run: ./examples/cli/demo_cli_usage.sh
```

## 相关文档

- [Auto-Coder SDK README](../../src/autocoder/sdk/README.md)
- [项目主 README](../../README.md)
- [API 文档](../../docs/)

## 反馈和贡献

如果您发现问题或有改进建议，请：

1. 提交 Issue 描述问题
2. 提交 Pull Request 贡献代码
3. 在社区讨论中分享使用经验

