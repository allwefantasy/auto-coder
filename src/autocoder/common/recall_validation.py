from typing import List, Optional
import byzerllm
from loguru import logger

def validate_recall(llm: byzerllm.ByzerLLM, content: Optional[List[str]] = None, query: Optional[str] = None) -> str:
    """
    验证召回模型的效果
    
    Args:
        llm: ByzerLLM实例
        content: 待验证的内容列表
        query: 查询语句
    
    Returns:
        验证结果
    """
    if content is None:
        content = [
            """
            # Deploying Models with ByzerLLM
            
            To deploy a model using ByzerLLM, follow these steps:
            
            1. Initialize the client
            2. Configure model parameters
            3. Deploy the model
            
            Example:
            ```python
            import byzerllm
            llm = byzerllm.ByzerLLM()
            llm.deploy_model('my_model')
            ```
            """
        ]
    
    if query is None:
        query = "How do I deploy a model with ByzerLLM?"
    
    conversations = [
        {"role": "user", "content": query}
    ]
    
    try:
        relevance = llm.chat_oai(
            conversations=conversations, 
            documents=content,
            model=llm.get_default_model_name()
        )
        return relevance[0].output
    except Exception as e:
        logger.error(f"Error validating recall: {str(e)}")
        return f"Error: {str(e)}"