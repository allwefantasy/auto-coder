from typing import List, Optional
import byzerllm
from loguru import logger

def validate_chunk(llm: byzerllm.ByzerLLM, content: Optional[List[str]] = None, query: Optional[str] = None) -> str:
    """
    验证文本分块模型的效果
    
    Args:
        llm: ByzerLLM实例
        content: 待验证的内容列表
        query: 相关问题
    
    Returns:
        验证结果
    """
    if content is None:
        content = [
            """
class TokenLimiter:
    def __init__(
        self,
        count_tokens: Callable[[str], int],
        full_text_limit: int,
        segment_limit: int,
        buff_limit: int,
        llm:ByzerLLM,
        disable_segment_reorder: bool,
    ):
        self.count_tokens = count_tokens
        self.full_text_limit = full_text_limit
        self.segment_limit = segment_limit
        self.buff_limit = buff_limit
        self.llm = llm

    def limit_tokens(self, relevant_docs: List[SourceCode]):
        pass
            """
        ]
    
    if query is None:
        query = "What are the main methods in TokenLimiter class?"

    try:
        from autocoder.rag.token_limiter import TokenLimiter
        def count_tokens(text:str):
            return 0
        token_limiter = TokenLimiter(
            llm=llm,
            count_tokens=count_tokens,
            full_text_limit=1000,
            segment_limit=1000,
            buff_limit=1000,
            disable_segment_reorder=False
        )
        conversations = [
            {"role": "user", "content": query}
        ]
        result = token_limiter.extract_relevance_range_from_docs_with_conversation.with_llm(llm).run(conversations, content)
        
        # 结果验证和解析
        validation_result = []
        for doc_idx, doc in enumerate(content):
            doc_lines = doc.split('\n')
            for range_info in result:
                start_line = range_info.get('start_line', 0)
                end_line = range_info.get('end_line', 0)
                if start_line >= 0 and end_line > start_line and end_line <= len(doc_lines):
                    extracted_text = '\n'.join(doc_lines[start_line-1:end_line])
                    validation_result.append(
                        f"Document {doc_idx + 1} - Extracted Range (lines {start_line}-{end_line}):\n{extracted_text}"
                    )

        if not validation_result:
            return "No valid ranges extracted from the documents."

        return "\n\n".join(validation_result)

    except Exception as e:
        logger.error(f"Error validating chunk model: {str(e)}")
        return f"Error: {str(e)}"