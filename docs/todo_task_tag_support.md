
# Todo 工具的 <task> 标签支持

## 概述

TodoWriteToolResolver 现在支持使用 `<task>` 标签格式来定义任务，这提供了一种更结构化和明确的方式来指定待办事项。

## 功能特性

### 1. 创建 Todo 列表 (create 操作)

#### 使用 <task> 标签格式

```xml
<task>Analyze the existing codebase structure</task>
<task>Design the new feature architecture</task>
<task>Implement the core functionality</task>
<task>Add comprehensive tests</task>
<task>Update documentation</task>
<task>Review and refactor code</task>
```

#### 传统格式（向后兼容）

```
1. 分析现有代码库结构
2. 设计新功能架构
3. 实现核心功能
4. 添加全面测试
5. 更新文档
6. 审查和重构代码
```

#### 混合格式

```
这是一个项目任务列表：
<task>设置开发环境</task>
<task>创建项目骨架</task>
其他说明文字
<task>编写初始代码</task>
```

### 2. 添加单个任务 (add_task 操作)

#### 使用 <task> 标签

```xml
<task>使用标签格式添加的新任务</task>
```

#### 传统格式

```
传统格式添加的任务
```

## 解析规则

### 优先级

1. **<task> 标签优先**: 如果内容中包含 `<task>` 标签，系统将优先解析这些标签内的内容
2. **传统格式回退**: 如果没有找到 `<task>` 标签，系统会回退到传统的行解析模式

### <task> 标签解析

- **多行支持**: `<task>` 标签内可以包含多行内容
- **空标签过滤**: 空的或只包含空白字符的 `<task>` 标签会被自动忽略
- **内容清理**: 标签内的内容会自动去除前后空白字符

### 传统格式解析

- **前缀移除**: 自动移除常见的列表前缀（如 "1.", "- ", "* " 等）
- **空行跳过**: 空行会被自动忽略
- **行级处理**: 每行被视为一个独立的任务

## 特殊情况处理

### 1. 空的 <task> 标签

```xml
<task>有效任务</task>
<task></task>
<task>   </task>
<task>另一个有效任务</task>
```

结果：只会创建两个任务（"有效任务" 和 "另一个有效任务"）

### 2. add_task 操作中的多个 <task> 标签

```xml
<task>第一个任务</task>
<task>第二个任务</task>
<task>第三个任务</task>
```

结果：只会添加第一个任务（"第一个任务"）

### 3. 多行任务内容

```xml
<task>这是一个多行的任务
包含详细的描述
和具体的步骤</task>
```

结果：整个多行内容会被保存为一个任务

## 向后兼容性

- **完全兼容**: 所有现有的传统格式输入都会继续正常工作
- **自动检测**: 系统会自动检测输入格式并选择合适的解析方式
- **无破坏性变更**: 现有代码无需修改即可继续使用

## 使用示例

### Python 代码示例

```python
from autocoder.common.v2.agent.agentic_edit_types import TodoWriteTool
from autocoder.common.v2.agent.agentic_edit_tools.todo_write_tool_resolver import TodoWriteToolResolver

# 使用 <task> 标签创建任务列表
content = """<task>Analyze the existing codebase structure</task>
<task>Design the new feature architecture</task>
<task>Implement the core functionality</task>"""

tool = TodoWriteTool(
    action="create",
    content=content,
    priority="high"
)

resolver = TodoWriteToolResolver(agent=None, tool=tool, args=args)
result = resolver.resolve()
```

### XML 工具调用示例

```xml
<todo_write>
<action>create</action>
<content><task>Analyze the existing codebase structure</task>
<task>Design the new feature architecture</task>
<task>Implement the core functionality</task>
<task>Add comprehensive tests</task>
<task>Update documentation</task>
<task>Review and refactor code</task></content>
<priority>high</priority>
</todo_write>
```

## 测试

项目包含完整的单元测试来验证所有功能：

```bash
python -m pytest src/autocoder/common/v2/agent/agentic_edit_tools/tests/test_todo_write_tool_resolver.py -v
```

测试覆盖了以下场景：
- <task> 标签格式解析
- 传统格式向后兼容性
- 混合格式处理
- 空标签过滤
- 多行内容支持
- 错误处理

