from typing import List, Dict, Any, Optional
from autocoder.common import AutoCoderArgs, SourceCode
from byzerllm import ByzerLLM
from .simple_rag import SimpleRAG
from .long_context_rag import LongContextRAG

def get_rag(llm: ByzerLLM, args: AutoCoderArgs, path: str) -> SimpleRAG | LongContextRAG:
    """
    Factory function to get the appropriate RAG implementation based on arguments.
    
    Args:
        llm (ByzerLLM): The ByzerLLM instance.
        args (AutoCoderArgs): The arguments for configuring RAG.
        path (str): The path to the data.
        
    Returns:
        SimpleRAG or LongContextRAG: The appropriate RAG implementation.
    """
    if args.rag_type == "long_context":
        return LongContextRAG(llm, args, path)
    else:
        return SimpleRAG(llm, args, path)

def rag_search(llm: ByzerLLM, args: AutoCoderArgs, path: str, query: str) -> List[SourceCode]:
    """
    Perform a RAG search using the appropriate implementation.
    
    Args:
        llm (ByzerLLM): The ByzerLLM instance.
        args (AutoCoderArgs): The arguments for configuring RAG.
        path (str): The path to the data.
        query (str): The search query.
        
    Returns:
        List[SourceCode]: The search results.
    """
    rag = get_rag(llm, args, path)
    return rag.search(query)

def rag_stream_chat_oai(
    llm: ByzerLLM,
    args: AutoCoderArgs,
    path: str,
    conversations: List[Dict[str, Any]],
    model: Optional[str] = None,
    role_mapping: Optional[Dict[str, str]] = None,
    llm_config: Dict[str, Any] = {},
):
    """
    Perform a streaming chat using the appropriate RAG implementation.
    
    Args:
        llm (ByzerLLM): The ByzerLLM instance.
        args (AutoCoderArgs): The arguments for configuring RAG.
        path (str): The path to the data.
        conversations (List[Dict[str, Any]]): The conversation history.
        model (Optional[str]): The model to use for chat.
        role_mapping (Optional[Dict[str, str]]): Role mapping for the conversation.
        llm_config (Dict[str, Any]): Additional LLM configuration.
        
    Returns:
        Tuple containing the chat response generator and any additional context.
    """
    rag = get_rag(llm, args, path)
    return rag.stream_chat_oai(conversations, model, role_mapping, llm_config)

def rag_build(llm: ByzerLLM, args: AutoCoderArgs, path: str):
    """
    Build the RAG index using the appropriate implementation.
    
    Args:
        llm (ByzerLLM): The ByzerLLM instance.
        args (AutoCoderArgs): The arguments for configuring RAG.
        path (str): The path to the data.
    """
    rag = get_rag(llm, args, path)
    rag.build()