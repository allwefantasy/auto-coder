"""
工具注册示例，演示如何注册工具和使用工具注册表
"""
from loguru import logger
from .tool_registry import ToolRegistry
from .types import ToolDescription, ToolExample
from .tools.example_tool_resolver import ExampleTool, ExampleToolResolver


def register_example_tools():
    """
    注册示例工具
    """
    # 准备工具描述和示例
    description = ToolDescription(
        title="示例工具",
        body="这是一个示例工具，用于展示工具注册和使用流程。"
    )
    
    example = ToolExample(
        title="示例工具使用示例",
        body="""
<example>
<message>这是示例消息</message>
<times>3</times>
</example>
"""
    )
    
    # 注册示例工具
    ToolRegistry.register_tool(
        tool_tag="example",  # XML标签名
        tool_cls=ExampleTool,  # 工具类
        resolver_cls=ExampleToolResolver,  # 解析器类
        description=description,  # 工具描述
        example=example  # 工具示例
    )
    
    logger.info("示例工具已注册")


def get_registered_tools():
    """
    获取已注册的工具映射关系
    
    Returns:
        工具映射字典，包括工具解析器映射和标签模型映射
    """
    return {
        "tool_resolver_map": ToolRegistry.get_tool_resolver_map(),
        "tag_model_map": ToolRegistry.get_tag_model_map()
    }


if __name__ == "__main__":
    # 示例：如何注册工具并查看注册的工具
    register_example_tools()
    
    # 获取注册的工具映射
    registered_tools = get_registered_tools()
    
    # 打印注册的工具
    print("工具解析器映射:")
    for tool_cls, resolver_cls in registered_tools["tool_resolver_map"].items():
        print(f"  {tool_cls.__name__} -> {resolver_cls.__name__}")
    
    print("\n标签模型映射:")
    for tag, model_cls in registered_tools["tag_model_map"].items():
        print(f"  {tag} -> {model_cls.__name__}")
    
    # 打印工具描述和示例
    print("\n工具描述:")
    for tag, desc in ToolRegistry.get_all_tool_descriptions().items():
        print(f"  {tag} -> 标题: {desc.title}")
        print(f"       描述: {desc.body}")
    
    print("\n工具示例:")
    for tag, example in ToolRegistry.get_all_tool_examples().items():
        print(f"  {tag} -> 标题: {example.title}")
        print(f"       示例: {example.body}") 