from typing import List, Dict, Any, Optional
from autocoder.common import AutoCoderArgs, SourceCode
from byzerllm import ByzerLLM
from .simple_rag import SimpleRAG
from .long_context_rag import LongContextRAG
class RAGFactory:
    
    
    @staticmethod
    def get_rag(llm: ByzerLLM, args: AutoCoderArgs, path: str,**kargs) -> SimpleRAG | LongContextRAG:
        """
        Factory method to get the appropriate RAG implementation based on arguments.
        
        Args:
            llm (ByzerLLM): The ByzerLLM instance.
            args (AutoCoderArgs): The arguments for configuring RAG.
            path (str): The path to the data.
            
        Returns:
            SimpleRAG or LongContextRAG: The appropriate RAG implementation.
        """
        if args.rag_type == "simple":
            return LongContextRAG(llm, args, path,**kargs)
        else:
            return SimpleRAG(llm, args, path)

class RAGManager:
    def __init__(self, llm: ByzerLLM, args: AutoCoderArgs, path: str):
        self.llm = llm
        self.args = args
        self.path = path
        self.rag = RAGFactory.get_rag(llm, args, path)

    def search(self, query: str) -> List[SourceCode]:
        """
        Perform a RAG search using the appropriate implementation.
        
        Args:
            query (str): The search query.
            
        Returns:
            List[SourceCode]: The search results.
        """
        return self.rag.search(query)

    def stream_chat_oai(
        self,
        conversations: List[Dict[str, Any]],
        model: Optional[str] = None,
        role_mapping: Optional[Dict[str, str]] = None,
        llm_config: Dict[str, Any] = {},
    ):
        """
        Perform a streaming chat using the appropriate RAG implementation.
        
        Args:
            conversations (List[Dict[str, Any]]): The conversation history.
            model (Optional[str]): The model to use for chat.
            role_mapping (Optional[Dict[str, str]]): Role mapping for the conversation.
            llm_config (Dict[str, Any]): Additional LLM configuration.
            
        Returns:
            Tuple containing the chat response generator and any additional context.
        """
        return self.rag.stream_chat_oai(conversations, model, role_mapping, llm_config)

    def build(self):
        """
        Build the RAG index using the appropriate implementation.
        """
        self.rag.build()
