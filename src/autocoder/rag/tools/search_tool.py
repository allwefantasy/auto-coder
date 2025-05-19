"""
SearchTool 模块

该模块实现了 SearchTool 和 SearchToolResolver 类，用于在 BaseAgent 框架中
提供基于 LongContextRAG 的文档搜索功能。
"""

import os
from typing import Dict, Any, List, Optional

from loguru import logger

from autocoder.agent.base_agentic.types import BaseTool, ToolResult
from autocoder.agent.base_agentic.tool_registry import ToolRegistry
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.agent.base_agentic.types import ToolDescription, ToolExample
from autocoder.common import AutoCoderArgs
from autocoder.rag.long_context_rag import LongContextRAG
from autocoder.rag.types import RecallStat, ChunkStat, AnswerStat, RAGStat
from autocoder.rag.relevant_utils import FilterDoc, DocRelevance, DocFilterResult


class SearchTool(BaseTool):
    """搜索工具，用于获取与查询相关的文件列表"""
    query: str  # 用户查询
    max_files: Optional[int] = 10  # 最大返回文件数量


class SearchToolResolver(BaseToolResolver):
    """搜索工具解析器，实现搜索逻辑"""
    def __init__(self, agent, tool, args):
        super().__init__(agent, tool, args)
        self.tool: SearchTool = tool
        
    def resolve(self) -> ToolResult:
        """实现搜索工具的解析逻辑"""
        try:
            # 获取参数
            query = self.tool.query            
            max_files = self.tool.max_files            
            rag = self.agent.rag            
            # 构建对话历史
            conversations = [
                {"role": "user", "content": query}
            ]
            
            # 创建 RAGStat 对象            
            rag_stat = RAGStat(
                recall_stat=RecallStat(total_input_tokens=0, total_generated_tokens=0),
                chunk_stat=ChunkStat(total_input_tokens=0, total_generated_tokens=0),
                answer_stat=AnswerStat(total_input_tokens=0, total_generated_tokens=0)
            )
            
            # 调用文档检索处理
            generator = rag._process_document_retrieval(conversations, query, rag_stat)
            
            # 获取最终结果
            result = None
            for item in generator:
                if isinstance(item, dict) and "result" in item:
                    result = item["result"]
            
            if not result:
                return ToolResult(
                    success=False,
                    message="未找到相关文档",
                    content=[]
                )
            
            # 格式化结果
            file_list = []
            for doc in result:
                file_list.append({
                    "path": doc.source_code.module_name,
                    "relevance": doc.relevance.relevant_score if doc.relevance else 0,
                    "is_relevant": doc.relevance.is_relevant if doc.relevance else False
                })
            
            # 按相关性排序
            file_list.sort(key=lambda x: x["relevance"], reverse=True)
            
            # 限制返回数量
            file_list = file_list[:max_files]
            
            return ToolResult(
                success=True,
                message=f"成功检索到 {len(file_list)} 个相关文件",
                content=file_list
            )
            
        except Exception as e:
            import traceback
            return ToolResult(
                success=False,
                message=f"搜索工具执行失败: {str(e)}",
                content=traceback.format_exc()
            )


def register_search_tool():
    """注册搜索工具"""
    # 准备工具描述
    description = ToolDescription(
        description="搜索与查询相关的文件",
        parameters="query: 搜索查询\nmax_files: 最大返回文件数量（可选，默认为10）",
        usage="用于根据查询找到相关的代码文件"
    )
    
    # 准备工具示例
    example = ToolExample(
        title="搜索工具使用示例",
        body="""<search>
<query>如何实现文件监控功能</query>
<max_files>5</max_files>
</search>"""
    )
    
    # 注册工具
    ToolRegistry.register_tool(
        tool_tag="search",  # XML标签名
        tool_cls=SearchTool,  # 工具类
        resolver_cls=SearchToolResolver,  # 解析器类
        description=description,  # 工具描述
        example=example,  # 工具示例
        use_guideline="此工具用于根据用户查询搜索相关代码文件，返回文件路径及其相关性分数。适用于需要快速找到与特定功能或概念相关的代码文件的场景。"  # 使用指南
    )
