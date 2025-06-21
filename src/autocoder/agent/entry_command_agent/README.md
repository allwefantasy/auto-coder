
# Entry Command Agent 模块

该模块包含各种入口命令的代理实现，用于处理不同类型的用户命令。每个代理都封装了特定命令的完整业务逻辑，提供统一的接口和清晰的职责分离。

## 模块概览

```
entry_command_agent/
├── __init__.py          # 模块导入接口
├── chat.py             # 聊天命令代理
└── README.md           # 本文档
```

## 代理列表

### ChatAgent - 聊天命令代理

处理所有与聊天相关的命令逻辑，包括会话管理、上下文构建、多种响应模式等。

#### 基本用法

```python
from autocoder.agent.entry_command_agent import ChatAgent

# 创建聊天代理实例
chat_agent = ChatAgent(args, llm, raw_args)

# 执行聊天命令
chat_agent.run()
```

#### 构造函数参数

- `args`: `AutoCoderArgs` - 应用程序参数对象
- `llm`: LLM 模型实例 - 语言模型对象
- `raw_args`: 原始命令行参数对象

#### 主要功能

1. **会话管理**
   - 新会话创建
   - 聊天历史加载和保存
   - 会话状态管理

2. **上下文构建**
   - 文件内容解析
   - 项目索引构建
   - 模型过滤应用

3. **多种响应模式**
   - 标准聊天模式
   - RAG（检索增强生成）模式
   - MCP（模型上下文协议）模式
   - 代码审查模式
   - 学习模式

4. **人工模型模式**
   - 人工干预支持
   - 剪贴板集成
   - 交互式输入

5. **后处理功能**
   - 响应复制到剪贴板
   - 内存文件保存
   - 统计信息输出

#### 支持的命令选项

ChatAgent 支持通过 `args.action` 传入的各种命令选项：

- `new_session`: 创建新的聊天会话
- `no_context`: 禁用上下文构建
- `rag`: 启用 RAG 模式
- `mcp`: 启用 MCP 模式
- `review`: 启用代码审查模式
- `learn`: 启用学习模式
- `copy`: 将响应复制到剪贴板
- `save`: 保存对话到内存文件

#### 配置示例

```python
# 基本聊天配置
args.action = ["chat"]
args.query = "你好，请帮我分析这段代码"

# 启用 RAG 模式
args.action = {"rag": {}}
args.query = "基于文档回答问题"

# 代码审查模式
args.action = {"review": {"args": ["分析代码质量"], "kwargs": {"commit": "abc123"}}}

# 保存对话
args.action = {"save": {"args": ["output.txt"]}}
```

#### 错误处理

ChatAgent 会处理以下常见错误情况：

- 模型连接失败
- 文件读写错误
- 剪贴板操作失败
- 用户中断操作

#### 性能监控

ChatAgent 自动收集和报告以下性能指标：

- 响应时间
- Token 使用量
- 成本估算
- 生成速度

## 扩展指南

### 添加新的命令代理

1. 在该目录下创建新的 Python 文件（如 `doc.py`）
2. 实现代理类，遵循以下接口规范：

```python
class DocAgent:
    def __init__(self, args, llm, raw_args):
        self.args = args
        self.llm = llm
        self.raw_args = raw_args
    
    def run(self):
        """执行命令的主要逻辑"""
        pass
```

3. 在 `__init__.py` 中添加导入：

```python
from .doc import DocAgent
__all__ = ['ChatAgent', 'DocAgent']
```

4. 在 `auto_coder.py` 中添加调用逻辑：

```python
elif raw_args.agent_command == "doc":
    from autocoder.agent.entry_command_agent import DocAgent
    doc_agent = DocAgent(args, llm, raw_args)
    doc_agent.run()
    return
```



## 依赖关系

该模块依赖以下核心组件：

- `autocoder.common.*`: 通用工具和配置
- `autocoder.utils.*`: 实用工具函数
- `autocoder.rag.*`: RAG 相关功能
- `autocoder.events.*`: 事件管理系统
- `byzerllm`: LLM 模型接口
- `rich`: 终端输出美化
- `prompt_toolkit`: 交互式输入


