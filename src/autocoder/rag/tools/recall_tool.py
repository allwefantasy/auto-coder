"""
RecallTool 模块

该模块实现了 RecallTool 和 RecallToolResolver 类，用于在 BaseAgent 框架中
提供基于 LongContextRAG 的文档内容召回功能。
"""

import os
import traceback
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
from autocoder.common import SourceCode
from autocoder.rag.relevant_utils import TaskTiming


class RecallTool(BaseTool):
    """召回工具，用于获取与查询相关的文档内容"""
    query: str  # 用户查询
    file_paths: Optional[List[str]] = None  # 指定要处理的文件路径列表，如果为空则自动搜索


class RecallToolResolver(BaseToolResolver):
    """召回工具解析器，实现召回逻辑"""
    def __init__(self, agent, tool, args):
        super().__init__(agent, tool, args)
        self.tool: RecallTool = tool
        
    def resolve(self) -> ToolResult:
        """实现召回工具的解析逻辑"""
        try:
            # 获取参数
            query = self.tool.query                        
            file_paths = self.tool.file_paths
            rag:LongContextRAG = self.agent.rag                                    
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
            
            # 如果提供了文件路径，则直接使用；否则，执行搜索
            if file_paths:                
                
                # 创建 FilterDoc 对象
                relevant_docs = []
                for file_path in file_paths:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        source_code = SourceCode(
                            module_name=file_path,
                            source_code=content
                        )
                        
                        doc = FilterDoc(
                            source_code=source_code,
                            relevance=DocRelevance(is_relevant=True, relevant_score=5),  # 默认相关性
                            task_timing=TaskTiming()
                        )
                        relevant_docs.append(doc)
                    except Exception as e:
                        logger.error(f"读取文件 {file_path} 失败: {str(e)}")
            else:
                # 调用文档检索处理
                generator = rag._process_document_retrieval(conversations, query, rag_stat)
                
                # 获取检索结果
                relevant_docs = None
                for item in generator:
                    if isinstance(item, dict) and "result" in item:
                        relevant_docs = item["result"]
                
                if not relevant_docs:
                    return ToolResult(
                        success=False,
                        message="未找到相关文档",
                        content=[]
                    )
            
            # 调用文档分块处理
            relevant_docs = [doc.source_code for doc in relevant_docs]
            doc_chunking_generator = rag._process_document_chunking(relevant_docs, conversations, rag_stat, 0)
            
            # 获取分块结果
            final_relevant_docs = None
            for item in doc_chunking_generator:
                if isinstance(item, dict) and "result" in item:
                    final_relevant_docs = item["result"]
            
            if not final_relevant_docs:
                return ToolResult(
                    success=False,
                    message="文档分块处理失败",
                    content=[]
                )
            
            # 格式化结果
            doc_contents = []
            for doc in final_relevant_docs:
                doc_contents.append({
                    "path": doc.module_name,
                    "content": doc.source_code                    
                })
            
            return ToolResult(
                success=True,
                message=f"成功召回 {len(doc_contents)} 个相关文档片段",
                content=doc_contents
            )
            
        except Exception as e:
            import traceback
            return ToolResult(
                success=False,
                message=f"召回工具执行失败: {str(e)}",
                content=traceback.format_exc()
            )


def register_recall_tool():
    """注册召回工具"""
    # 准备工具描述
    description = ToolDescription(
        description="召回与查询相关的文档内容",
        parameters="query: 搜索查询\nfile_paths: 指定要处理的文件路径列表（可选）",
        usage="用于根据查询获取相关文档的内容片段"
    )
    
    # 准备工具示例
    example = ToolExample(
        title="召回工具使用示例",
        body="""<recall>
<query>如何实现文件监控功能</query>
</recall>"""
    )
    
    # 注册工具
    ToolRegistry.register_tool(
        tool_tag="recall",  # XML标签名
        tool_cls=RecallTool,  # 工具类
        resolver_cls=RecallToolResolver,  # 解析器类
        description=description,  # 工具描述
        example=example,  # 工具示例
        use_guideline="此工具用于根据用户查询召回相关文档内容，返回经过分块和重排序的文档片段。适用于需要深入了解特定功能实现细节的场景。"  # 使用指南
    )
