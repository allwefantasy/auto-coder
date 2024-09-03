from autocoder.common import AutoCoderArgs, SourceCode
from pydantic import BaseModel
import re
from typing import Optional


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
