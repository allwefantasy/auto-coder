from typing import Dict, Type, ClassVar, Optional, List
import logging
import inspect
from .types import BaseTool, ToolDescription, ToolExample
from .tools.base_tool_resolver import BaseToolResolver

from loguru import logger


class ToolRegistry:
    """
    工具注册表，用于管理工具和对应的解析器
    """
    # 类变量，存储工具和解析器的映射关系
    _tool_resolver_map: ClassVar[Dict[Type[BaseTool], Type[BaseToolResolver]]] = {}
    _tag_model_map: ClassVar[Dict[str, Type[BaseTool]]] = {}
    
    # 存储工具描述和示例
    _tool_descriptions: ClassVar[Dict[str, ToolDescription]] = {}
    _tool_examples: ClassVar[Dict[str, ToolExample]] = {}
    
    # 存储工具使用指南
    _tool_use_guidelines: ClassVar[Dict[str, str]] = {}
    
    # 存储工具用例文档
    _tools_case_doc: ClassVar[Dict[str, Dict[str, object]]] = {}
    
    # 存储角色描述和通用描述
    _role_descriptions: ClassVar[Dict[str, str]] = {}
    
    # 存储默认工具集
    _default_tools: ClassVar[Dict[str, Type[BaseTool]]] = {}

    @classmethod
    def register_tool(cls, tool_tag: str, tool_cls: Type[BaseTool], resolver_cls: Type[BaseToolResolver], 
                     description: ToolDescription, example: ToolExample, use_guideline: str = "") -> None:
        """
        注册工具和对应的解析器

        Args:
            tool_tag: XML标签名称
            tool_cls: 工具类
            resolver_cls: 解析器类
            description: 工具描述，包含title和body，将用于生成提示
            example: 工具使用示例，包含title和body，将用于生成提示
            use_guideline: 工具使用指南，提供给LLM关于如何正确使用该工具的具体指导
        """
        if tool_cls in cls._tool_resolver_map:
            logger.warning(f"工具 {tool_cls.__name__} 已经注册过，将被覆盖")
        
        cls._tool_resolver_map[tool_cls] = resolver_cls
        cls._tag_model_map[tool_tag] = tool_cls
        
        # 注册描述和示例        
        cls._tool_descriptions[tool_tag] = description                
        cls._tool_examples[tool_tag] = example
        
        # 注册使用指南
        if use_guideline:
            cls._tool_use_guidelines[tool_tag] = use_guideline
            
        logger.info(f"成功注册工具: {tool_tag} -> {tool_cls.__name__} 使用解析器 {resolver_cls.__name__}")
    
    @classmethod
    def register_default_tool(cls, tool_tag: str, tool_cls: Type[BaseTool], resolver_cls: Type[BaseToolResolver], 
                             description: ToolDescription, example: ToolExample, use_guideline: str = "") -> None:
        """
        注册默认工具和对应的解析器，同时记录在默认工具集中

        Args:
            tool_tag: XML标签名称
            tool_cls: 工具类
            resolver_cls: 解析器类
            description: 工具描述，包含title和body，将用于生成提示
            example: 工具使用示例，包含title和body，将用于生成提示
            use_guideline: 工具使用指南，提供给LLM关于如何正确使用该工具的具体指导
        """
        # 注册工具
        cls.register_tool(tool_tag, tool_cls, resolver_cls, description, example, use_guideline)
        
        # 添加到默认工具集
        cls._default_tools[tool_tag] = tool_cls
        logger.info(f"已将工具 {tool_tag} 添加到默认工具集")
    
    @classmethod
    def register_tools_case_doc(cls, case_name: str, tools: List[str], doc: str) -> None:
        """
        注册工具用例文档

        Args:
            case_name: 用例名称
            tools: 工具名称列表
            doc: 用例文档说明
        """
        cls._tools_case_doc[case_name] = {
            "tools": tools,
            "doc": doc
        }
        logger.info(f"成功注册工具用例文档: {case_name}, 包含工具: {', '.join(tools)}")
    
    @classmethod
    def register_unified_tool(cls, tool_tag: str, tool_info: Dict) -> None:
        """
        统一注册工具的所有相关信息

        Args:
            tool_tag: 工具标签
            tool_info: 工具信息字典，包含以下字段：
                - tool_cls: 工具类
                - resolver_cls: 解析器类
                - description: 工具描述对象
                - example: 工具示例对象
                - use_guideline: 工具使用指南（可选）
                - category: 工具分类（可选）
                - is_default: 是否为默认工具（可选，默认为False）
                - case_docs: 关联的用例文档列表（可选）
        """
        # 提取工具信息
        tool_cls = tool_info.get("tool_cls")
        resolver_cls = tool_info.get("resolver_cls")
        description = tool_info.get("description")
        example = tool_info.get("example")
        use_guideline = tool_info.get("use_guideline", "")
        is_default = tool_info.get("is_default", False)
        case_docs = tool_info.get("case_docs", [])
        
        # 验证必要字段
        if not all([tool_cls, resolver_cls, description]):
            logger.error(f"注册工具 {tool_tag} 失败：缺少必要信息")
            return
        
        # 注册工具
        if is_default:
            cls.register_default_tool(
                tool_tag=tool_tag,
                tool_cls=tool_cls,
                resolver_cls=resolver_cls,
                description=description,
                example=example,
                use_guideline=use_guideline
            )
        else:
            cls.register_tool(
                tool_tag=tool_tag,
                tool_cls=tool_cls,
                resolver_cls=resolver_cls,
                description=description,
                example=example,
                use_guideline=use_guideline
            )
        
        # 关联用例文档
        for case_doc in case_docs:
            if case_doc in cls._tools_case_doc:
                if tool_tag not in cls._tools_case_doc[case_doc]["tools"]:
                    cls._tools_case_doc[case_doc]["tools"].append(tool_tag)
                    logger.info(f"将工具 {tool_tag} 添加到用例文档 {case_doc}")
        
        logger.info(f"成功统一注册工具: {tool_tag}")

    
    @classmethod
    def unregister_tool(cls, tool_tag: str) -> bool:
        """
        卸载一个已注册的工具
        
        Args:
            tool_tag: 工具标签
            
        Returns:
            是否成功卸载
        """
        tool_cls = cls._tag_model_map.get(tool_tag)
        if tool_cls is None:
            logger.warning(f"找不到要卸载的工具: {tool_tag}")
            return False
        
        # 清除工具关联数据
        if tool_cls in cls._tool_resolver_map:
            del cls._tool_resolver_map[tool_cls]
        if tool_tag in cls._tag_model_map:
            del cls._tag_model_map[tool_tag]
        if tool_tag in cls._tool_descriptions:
            del cls._tool_descriptions[tool_tag]
        if tool_tag in cls._tool_examples:
            del cls._tool_examples[tool_tag]
        if tool_tag in cls._tool_use_guidelines:
            del cls._tool_use_guidelines[tool_tag]
        if tool_tag in cls._default_tools:
            del cls._default_tools[tool_tag]
        
        # 清除工具在用例文档中的引用
        for case_name, case_data in list(cls._tools_case_doc.items()):
            if tool_tag in case_data["tools"]:
                # 如果该工具是用例中唯一的工具，删除整个用例
                if len(case_data["tools"]) == 1:
                    del cls._tools_case_doc[case_name]
                    logger.info(f"已删除依赖于工具 {tool_tag} 的用例文档: {case_name}")
                else:
                    # 否则只从工具列表中移除该工具
                    case_data["tools"].remove(tool_tag)
                    logger.info(f"已从用例 {case_name} 中移除工具 {tool_tag}")
            
        logger.info(f"成功卸载工具: {tool_tag}")
        return True
    
    @classmethod
    def reset_to_default_tools(cls) -> None:
        """
        重置为仅包含默认工具的状态，移除所有非默认工具
        """
        # 获取需要保留的工具标签
        default_tags = set(cls._default_tools.keys())
        # 获取所有当前工具标签
        all_tags = set(cls._tag_model_map.keys())
        # 计算要删除的标签
        tags_to_remove = all_tags - default_tags
        
        # 移除非默认工具
        for tag in tags_to_remove:
            cls.unregister_tool(tag)
            
        logger.info(f"工具注册表已重置为默认工具集，保留了 {len(default_tags)} 个默认工具")
    
    @classmethod
    def is_default_tool(cls, tool_tag: str) -> bool:
        """
        检查工具是否为默认工具
        
        Args:
            tool_tag: 工具标签
            
        Returns:
            是否为默认工具
        """
        return tool_tag in cls._default_tools
    
    @classmethod
    def get_default_tools(cls) -> List[str]:
        """
        获取所有默认工具标签
        
        Returns:
            默认工具标签列表
        """
        return list(cls._default_tools.keys())

    @classmethod
    def register_role_description(cls, agent_type: str, description: str) -> None:
        """
        注册代理角色描述

        Args:
            agent_type: 代理类型标识
            description: 角色描述文本
        """
        cls._role_descriptions[agent_type] = description
        logger.info(f"成功注册角色描述: {agent_type}")
    
    @classmethod
    def get_role_description(cls, agent_type: str) -> Optional[str]:
        """
        获取代理角色描述

        Args:
            agent_type: 代理类型标识

        Returns:
            角色描述文本，如果未找到则返回None
        """
        return cls._role_descriptions.get(agent_type)

    @classmethod
    def get_tool_description(cls, tool_tag: str) -> Optional[ToolDescription]:
        """
        获取工具描述

        Args:
            tool_tag: 工具标签

        Returns:
            工具描述对象，如果未找到则返回None
        """
        return cls._tool_descriptions.get(tool_tag)
    
    @classmethod
    def get_tool_example(cls, tool_tag: str) -> Optional[ToolExample]:
        """
        获取工具示例

        Args:
            tool_tag: 工具标签

        Returns:
            工具示例对象，如果未找到则返回None
        """
        return cls._tool_examples.get(tool_tag)
    
    @classmethod
    def get_tool_use_guideline(cls, tool_tag: str) -> Optional[str]:
        """
        获取工具使用指南

        Args:
            tool_tag: 工具标签

        Returns:
            工具使用指南，如果未找到则返回None
        """
        return cls._tool_use_guidelines.get(tool_tag)
    
    @classmethod
    def get_tools_case_doc(cls, case_name: str) -> Optional[Dict[str, object]]:
        """
        获取工具用例文档

        Args:
            case_name: 用例名称

        Returns:
            工具用例文档，包含tools和doc字段，如果未找到则返回None
        """
        return cls._tools_case_doc.get(case_name)
    
    @classmethod
    def get_all_tool_descriptions(cls) -> Dict[str, ToolDescription]:
        """
        获取所有工具描述

        Returns:
            工具描述字典，key为工具标签，value为描述对象
        """
        return cls._tool_descriptions.copy()
    
    @classmethod
    def get_all_tool_examples(cls) -> Dict[str, ToolExample]:
        """
        获取所有工具示例

        Returns:
            工具示例字典，key为工具标签，value为示例对象
        """
        return cls._tool_examples.copy()
    
    @classmethod
    def get_all_tool_use_guidelines(cls) -> Dict[str, str]:
        """
        获取所有工具使用指南

        Returns:
            工具使用指南字典，key为工具标签，value为使用指南文本
        """
        return cls._tool_use_guidelines.copy()
    
    @classmethod
    def get_all_tools_case_docs(cls) -> Dict[str, Dict[str, object]]:
        """
        获取所有工具用例文档

        Returns:
            工具用例文档字典，key为用例名称，value为包含tools和doc字段的字典
        """
        return cls._tools_case_doc.copy()

    @classmethod
    def get_resolver_for_tool(cls, tool_cls_or_instance) -> Type[BaseToolResolver]:
        """
        获取工具对应的解析器类

        Args:
            tool_cls_or_instance: 工具类或工具实例

        Returns:
            解析器类
        """
        # 如果传入的是实例，获取其类
        if not inspect.isclass(tool_cls_or_instance):
            tool_cls = type(tool_cls_or_instance)
        else:
            tool_cls = tool_cls_or_instance
            
        return cls._tool_resolver_map.get(tool_cls)

    @classmethod
    def get_model_for_tag(cls, tool_tag: str) -> Type[BaseTool]:
        """
        根据标签获取对应的工具类

        Args:
            tool_tag: 工具标签

        Returns:
            工具类
        """
        return cls._tag_model_map.get(tool_tag)

    @classmethod
    def get_tool_resolver_map(cls) -> Dict[Type[BaseTool], Type[BaseToolResolver]]:
        """
        获取工具和解析器的映射关系

        Returns:
            工具和解析器的映射字典
        """
        return cls._tool_resolver_map.copy()

    @classmethod
    def get_tag_model_map(cls) -> Dict[str, Type[BaseTool]]:
        """
        获取标签和工具的映射关系

        Returns:
            标签和工具的映射字典
        """
        return cls._tag_model_map.copy()
    
    @classmethod
    def get_all_registered_tools(cls) -> List[str]:
        """
        获取所有已注册的工具标签

        Returns:
            工具标签列表
        """
        return list(cls._tag_model_map.keys())