import pydantic
from typing import List
from autocoder.common import SourceCode

class TokenLimiterResult(pydantic.BaseModel):
    # 注意， docs 只保留结果文档
    docs: List[SourceCode]
    # 注意， raw_docs 保留所有文档
    raw_docs: List[SourceCode]
    input_tokens_counts: List[int]
    generated_tokens_counts: List[int]
    durations: List[float]
    model_name: str = "unknown"