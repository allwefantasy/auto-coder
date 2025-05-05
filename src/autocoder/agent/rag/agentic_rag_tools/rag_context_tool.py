import os
import re
import json
from typing import Dict, Any, Optional, List, Generator, Union, Tuple
from pydantic import BaseModel

from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.common.v2.agent.agentic_edit_tools.base_tool_resolver import BaseToolResolver
from autocoder.common.v2.agent.agentic_edit_types import BaseTool, ToolResult
from autocoder.rag.long_context_rag import LongContextRAG, RAGStat, RecallStat, ChunkStat, AnswerStat
from autocoder.rag.searchable import SearchableResults
from autocoder.rag.relevant_utils import DocFilterResult
from autocoder.rag.conversation_to_queries import extract_search_queries
from byzerllm.utils.types import SingleOutputMeta
from loguru import logger
import typing

if typing.TYPE_CHECKING:
    from autocoder.agent.rag.agentic_rag import AgenticRAG


# 定义工具类
class RagContextTool(BaseTool):
    """用于从项目中检索与查询相关的上下文的工具"""
    query: str
    path: str  # 项目路径
    max_docs: Optional[int] = 10  # 最大文档数量
    relevance_threshold: Optional[float] = 0.7  # 相关性阈值


class RagContextToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['AgenticRAG'], tool: RagContextTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: RagContextTool = tool
        self.path = os.path.abspath(os.path.join(self.args.source_dir, self.tool.path))
        
        # 在构造函数中初始化LongContextRAG
        self.rag = None
        try:
            self.rag = LongContextRAG(
                llm=agent.llm,
                args=args,
                path=self.path,
                tokenizer_path=None  # 使用默认tokenizer
            )
        except Exception as e:
            logger.error(f"初始化RAG失败: {e}")

    def resolve(self) -> ToolResult:
        """执行RAG上下文检索操作"""
        if not self.rag:
            return ToolResult(
                success=False,
                message="无法初始化RAG系统，请检查配置和依赖项",
                content=None
            )
        
        try:
            # 创建模拟对话
            conversations = [{"role": "user", "content": self.tool.query}]
            
            # 创建统计对象
            rag_stat = RAGStat(
                recall_stat=RecallStat(
                    total_input_tokens=0,
                    total_generated_tokens=0,
                    model_name=self.rag.recall_llm.default_model_name,
                ),
                chunk_stat=ChunkStat(
                    total_input_tokens=0,
                    total_generated_tokens=0,
                    model_name=self.rag.chunk_llm.default_model_name,
                ),
                answer_stat=AnswerStat(
                    total_input_tokens=0,
                    total_generated_tokens=0,
                    model_name=self.rag.qa_llm.default_model_name,
                ),
            )
            
            # 第一阶段：文档检索和过滤
            context = []
            query = self.tool.query
            
            # 执行第一阶段：文档召回和过滤
            retrieval_generator = self.rag._process_document_retrieval(
                conversations=conversations,
                query=query,
                rag_stat=rag_stat
            )
            
            # 处理第一阶段结果
            relevant_docs = []
            for item in retrieval_generator:
                if isinstance(item, dict) and "result" in item:
                    relevant_docs = item["result"]
                    context.extend([doc.source_code.module_name for doc in relevant_docs])
                    break  # 只需要结果，不需要中间状态
            
            if not relevant_docs:
                return ToolResult(
                    success=True,
                    message="未找到相关文档",
                    content=[]
                )
            
            # 记录相关文档信息
            logger.info(f"找到相关文档数量: {len(relevant_docs)}")
            
            # 执行第二阶段：文档分块与重排序
            chunking_generator = self.rag._process_document_chunking(
                relevant_docs=relevant_docs,
                conversations=conversations,
                rag_stat=rag_stat,
                filter_time=0  # 不重要的时间统计
            )
            
            # 处理第二阶段结果
            processed_docs = []
            for chunking_item in chunking_generator:
                if isinstance(chunking_item, dict) and "result" in chunking_item:
                    processed_docs = chunking_item["result"]
                    break  # 只需要结果，不需要中间状态
            
            if not processed_docs:
                return ToolResult(
                    success=True,
                    message="文档处理后未得到有效结果",
                    content=[]
                )
            
            # 限制返回的文档数量
            max_docs = self.tool.max_docs or 10
            processed_docs = processed_docs[:max_docs]
            
            # 使用SearchableResults重新排序结果
            try:
                searcher = SearchableResults()
                result = searcher.reorder(docs=processed_docs)
                
                # 将搜索结果转换为更友好的格式
                formatted_results = []
                for i, doc in enumerate(result.items):
                    formatted_doc = {
                        "index": i + 1,
                        "path": doc.module_name,
                        "relevance": doc.relevance.relevance if hasattr(doc, 'relevance') else 0,
                        "content": doc.source_code,
                        "metadata": doc.metadata
                    }
                    formatted_results.append(formatted_doc)
                
                # 创建包含统计信息的结果
                result_with_stats = {
                    "results": formatted_results,
                    "stats": {
                        "total_docs_found": len(relevant_docs),
                        "docs_returned": len(formatted_results),
                        "input_tokens": rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens,
                        "generated_tokens": rag_stat.recall_stat.total_generated_tokens + rag_stat.chunk_stat.total_generated_tokens,
                    }
                }
                
                return ToolResult(
                    success=True,
                    message=f"成功检索到 {len(formatted_results)} 个相关文档",
                    content=result_with_stats
                )
            except Exception as e:
                logger.error(f"处理搜索结果时出错: {e}")
                
                # 如果优化排序失败，返回原始处理后的文档
                basic_results = []
                for i, doc in enumerate(processed_docs):
                    basic_result = {
                        "index": i + 1,
                        "path": doc.source_code.module_name,
                        "content": doc.source_code.source_code,
                        "metadata": doc.source_code.metadata
                    }
                    basic_results.append(basic_result)
                
                return ToolResult(
                    success=True,
                    message=f"成功检索到 {len(basic_results)} 个相关文档（结果排序失败）",
                    content={"results": basic_results}
                )
        
        except Exception as e:
            logger.exception(f"执行RAG上下文检索时发生错误: {e}")
            return ToolResult(
                success=False,
                message=f"执行RAG上下文检索时发生错误: {str(e)}",
                content=None
            ) 