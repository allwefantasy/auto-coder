from typing import List, Dict, Any, Optional, Union
import logging
import byzerllm
from pydantic import BaseModel
from autocoder.common import AutoCoderArgs

logger = logging.getLogger(__name__)


class SearchQuery(BaseModel):
    """搜索查询模型"""
    query: str
    importance: int = 5  # 1-10，表示查询的重要性
    purpose: str = ""    # 查询的目的说明

class ConversationToQueries:
    """
    将对话历史转换为搜索查询的工具类。
    """
    
    def __init__(self, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        """
        初始化对话转查询工具类。
        
        参数:
            llm: ByzerLLM 实例，用于执行 prompt 函数
        """
        self.llm = llm
    
    @byzerllm.prompt()
    def generate_search_queries(self, conversations: List[Dict[str, Any]], max_queries: int = 3) -> str:
        """
        根据历史对话生成搜索查询。
        
        参数:
            conversations: 历史对话列表，每个对话是一个字典，包含 'role' 和 'content' 字段
            max_queries: 最大生成的查询数量，默认为 3
            
        返回:
            生成的搜索查询列表的 JSON 字符串
            
        任务说明:
        你是一个专业的对话分析助手。你的任务是分析用户与 AI 的对话历史，从中提取关键信息，
        并生成用于搜索引擎的查询，以便获取与对话相关的知识和信息。
        
        具体要求:
        1. 仔细分析对话历史，特别是最近的几轮对话
        2. 识别用户可能需要更多信息或知识的关键问题和主题
        3. 将这些关键问题转化为明确、简洁的搜索查询
        4. 每个查询应该足够具体，能够通过搜索引擎找到有用的结果
        5. 为每个查询提供重要性评分（1-10 分）和用途说明
        6. 最多生成 {{ max_queries }} 个查询，按重要性排序
        7. 返回符合指定格式的 JSON 数据
        
        可能的场景:
        - 用户询问特定技术或概念，需要进一步的解释或示例
        - 用户遇到编程问题，需要查找解决方案或最佳实践
        - 用户讨论的话题涉及多个方面，需要查找不同角度的信息
        - 用户想了解某个领域的最新发展或趋势
        
        ---
        
        对话历史:
        <conversations>
        {% for msg in conversations %}
        {{ msg.role }}: {{ msg.content }}
        {% endfor %}
        </conversations>
        
        请分析上述对话，提取关键问题并生成最多 {{ max_queries }} 个搜索查询。
        
        输出格式:
        ```json
        [
          {
            "query": "搜索查询1",
            "importance": 评分(1-10),
            "purpose": "该查询的目的说明"
          },
          {
            "query": "搜索查询2",
            "importance": 评分(1-10),
            "purpose": "该查询的目的说明"
          }
        ]
        ```
        """
    
    def extract_queries(self, conversations: List[Dict[str, Any]], max_queries: int = 3) -> List[SearchQuery]:
        """
        从对话历史中提取搜索查询。
        
        参数:
            conversations: 历史对话列表
            max_queries: 最大生成的查询数量
            
        返回:
            SearchQuery 对象列表
        """
        try:
            # 使用 prompt 函数生成搜索查询
            queries = self.generate_search_queries.with_llm(self.llm).with_return_type(SearchQuery).run(
                conversations=conversations,
                max_queries=max_queries
            )            
            
            # 按重要性排序
            queries.sort(key=lambda x: x.importance, reverse=True)
            
            return queries
        except Exception as e:
            logger.error(f"Error extracting queries from conversation: {str(e)}")
            return []

def extract_search_queries(
    conversations: List[Dict[str, Any]], 
    args:AutoCoderArgs,
    llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM],
    max_queries: int = 3,    
) -> List[SearchQuery]:
    """
    从对话历史中提取搜索查询的便捷函数。
    
    参数:
        conversations: 历史对话列表
        llm: ByzerLLM 实例
        max_queries: 最大生成的查询数量
        
    返回:
        SearchQuery 对象列表
    """
    if max_queries == 0:
        return []
    try:    
        extractor = ConversationToQueries(llm)
        return extractor.extract_queries(conversations, max_queries) 
    except Exception as e:
        logger.error(f"Error extracting search queries from conversation: {str(e)}")
        return []