from autocoder.common import AutoCoderArgs, SourceCode
from pydantic import BaseModel
import re
from typing import Optional, List


class DocRelevance(BaseModel):
    is_relevant: bool
    relevant_score: int


class TaskTiming(BaseModel):
    submit_time: float = 0
    end_time: float = 0
    duration: float = 0
    real_start_time: float = 0
    real_end_time: float = 0
    real_duration: float = 0
    
class FilterDoc(BaseModel):
    source_code: SourceCode
    relevance: DocRelevance
    task_timing: TaskTiming


class DocFilterResult(BaseModel):
    # 注意， docs 只保留最后成功过滤的文档
    docs: List[FilterDoc]
    # 注意， raw_docs 保留所有文档
    raw_docs: List[FilterDoc]
    input_tokens_counts: List[int]
    generated_tokens_counts: List[int]
    durations: List[float] 
    model_name: str = "unknown"
    

def parse_relevance(text: Optional[str]) -> Optional[DocRelevance]:    
    if text is None:
        return None
    pattern = r"(yes|no)/(\d+)"
    match = re.search(pattern, text, re.IGNORECASE)

    if match:
        is_relevant = match.group(1).lower() == "yes"
        relevant_score = int(match.group(2))
        return DocRelevance(is_relevant=is_relevant, relevant_score=relevant_score)

    return None
