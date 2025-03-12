from typing import List, Optional
import byzerllm
from loguru import logger
from autocoder.rag.doc_filter import _check_relevance_with_conversation
from autocoder.rag.relevant_utils import parse_relevance

def validate_recall(llm: byzerllm.ByzerLLM, content: Optional[List[str]] = None, query: Optional[str] = None) -> bool:
    """
    验证召回模型的效果
    
    Args:
        llm: ByzerLLM实例
        content: 待验证的内容列表
        query: 查询语句
    
    Returns:
        验证成功返回True，失败返回False
    """
    if content is None:
        content = [
            """
            # ByzerLLM API Guide
            
            ByzerLLM provides a simple API for interacting with language models. 
            Here's how to use it:
            
            1. Initialize the client
            2. Send requests
            3. Process responses
            
            Example:
            ```python
            import byzerllm
            llm = byzerllm.ByzerLLM()
            response = llm.chat(prompt="Hello")
            ```
            """
        ]
    
    if query is None:
        query = "How do I use the ByzerLLM API?"
    
    conversations = [
        {"role": "user", "content": query}
    ]
    
    try:
        relevance_str = _check_relevance_with_conversation.with_llm(llm).run(conversations, content)
        relevance = parse_relevance(relevance_str)
        
        if relevance is None:
            logger.error("Failed to parse relevance result")
            return False
            
        return relevance.is_relevant
    except Exception as e:
        logger.error(f"Error validating recall: {str(e)}")
        return False