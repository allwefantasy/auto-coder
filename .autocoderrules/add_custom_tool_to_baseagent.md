---
description: 如何在 BaseAgent  中动态注册自定义工具
globs: ["*.py"]
alwaysApply: false
---

# 在 BaseAgent 中动态注册自定义工具

## 简要说明
BaseAgent 支持通过动态注册机制添加新的工具，无需修改源代码。只需创建工具类、工具解析器类，并通过 `ToolRegistry` 注册即可使新工具可用。本指南将以 `ListFilesTool` 为例，介绍添加自定义工具的完整流程。

## 典型用法
```python
from autocoder.agent.base_agentic.tool_registry import ToolRegistry
from autocoder.agent.base_agentic.types import BaseTool, ToolDescription, ToolExample
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from typing import Optional, Dict, Any

# 1. 定义工具类 - 继承自 BaseTool
class MyCustomTool(BaseTool):
    path: str  # 工具需要的参数
    option: Optional[bool] = False  # 可选参数带默认值

# 2. 创建工具解析器 - 继承自 BaseToolResolver
class MyCustomToolResolver(BaseToolResolver):
    def __init__(self, agent, tool, args):
        super().__init__(agent, tool, args)
        self.tool: MyCustomTool = tool  # 提供类型提示
    
    def resolve(self) -> ToolResult:
        """实现解析逻辑"""
        try:
            # 工具的具体实现逻辑
            path = self.tool.path
            option = self.tool.option
            
            # 进行操作...
            result = f"处理了路径 {path}，选项值为 {option}"
            
            return ToolResult(success=True, message="工具执行成功", content=result)
        except Exception as e:
            return ToolResult(success=False, message=f"工具执行失败: {str(e)}")

# 3. 注册工具
def register_my_custom_tool():
    # 准备工具描述
    description = ToolDescription(
        description="我的自定义工具",
        parameters="path: 文件路径\noption: 可选参数，默认为False",
        usage="用于执行自定义操作"
    )
    
    # 准备工具示例
    example = ToolExample(
        title="自定义工具使用示例",
        body="""
<my_custom>
<path>/path/to/directory</path>
<option>true</option>
</my_custom>
"""
    )
    
    # 注册工具
    ToolRegistry.register_tool(
        tool_tag="my_custom",  # XML标签名
        tool_cls=MyCustomTool,  # 工具类
        resolver_cls=MyCustomToolResolver,  # 解析器类
        description=description,  # 工具描述
        example=example,  # 工具示例
        use_guideline="此工具用于处理特定路径下的内容，设置option为true可启用额外功能。"  # 可选的使用指南
    )
```

## ListFilesTool 示例
以下是 `ListFilesTool` 的实现和注册示例：

```python
# 工具定义 (在 types.py 中)
class ListFilesTool(BaseTool):
    path: str
    recursive: Optional[bool] = False

# 工具注册 (在 default_tools.py 中)
# 使用 byzerllm.prompt() 装饰器构建描述
class ToolDescriptionGenerators:
    @byzerllm.prompt()
    def list_files_description(self) -> Dict:
        """
        List directory contents
        """
        return {}
    
    @byzerllm.prompt()
    def list_files_parameters(self) -> Dict:
        """
        path: Directory path
        recursive: Whether to list files recursively (default: false)
        """
        return {}
    
    @byzerllm.prompt()
    def list_files_usage(self) -> Dict:
        """
        Used to list files and directories in a given path
        """
        return {}

class ToolExampleGenerators:
    @byzerllm.prompt()
    def list_files_example(self) -> Dict:
        """
        <list_files>
        <path>src</path>
        <recursive>true</recursive>
        </list_files>
        """
        return {}

# 在 register_default_tools() 中注册
ToolRegistry.register_tool(
        tool_tag="list_files",
        tool_cls=ListFilesTool,
        resolver_cls=ListFilesToolResolver,
        description=ToolDescription(
            description=desc_gen.list_files_description.prompt(),
            parameters=desc_gen.list_files_parameters.prompt(),
            usage=desc_gen.list_files_usage.prompt()
        ),
        example=ToolExample(
            title="列出目录内容示例",
            body=example_gen.list_files_example.prompt()
        )
    )
```

## 关键步骤说明

1. **创建工具类**：
   - 继承 `BaseTool`
   - 使用 Pydantic 字段定义参数
   - 可选参数需提供默认值

2. **实现工具解析器**：
   - 继承 `BaseToolResolver`
   - 实现 `resolve()` 方法
   - 处理异常并返回 `ToolResult`

3. **准备描述和示例**：
   - 创建 `ToolDescription` 实例，包含功能描述、参数说明和用途
   - 创建 `ToolExample` 实例，展示 XML 格式的调用示例

4. **注册工具**：
   - 使用 `ToolRegistry.register_tool()` 方法   
   - 可选提供 `use_guideline` 参数，给 LLM 提供更详细的使用指导

5. **应用 byzerllm.prompt() 装饰器**（可选）：
   - 可用于更优雅地构建描述和示例
   - 利用 docstring 作为模板，返回值作为渲染上下文

## 最佳实践
- 保持工具功能单一明确
- 为每个参数提供清晰的说明
- 编写详细而具有代表性的示例
- 捕获并优雅处理所有可能的异常
- 考虑安全性，避免危险操作
- 合理命名 XML 标签，避免与现有工具冲突

## 学习来源
从 `/Users/allwefantasy/projects/auto-coder/src/autocoder/agent/base_agentic` 目录提取，特别是 `ListFilesTool` 和 `ListFilesToolResolver` 的实现，以及 `tool_registry.py` 中的注册机制。 