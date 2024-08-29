from autocoder.common import AutoCoderArgs, SourceCode
from pydantic import BaseModel

class DocRelevance(BaseModel):
    is_relevant: bool
    relevant_score: int

class FilterDoc(BaseModel):
    source_code: SourceCode
    relevance: DocRelevance

import re
from typing import Optional

def parse_relevance(text: str) -> Optional[DocRelevance]:
    pattern = r"(yes|no)/(\d+)"
    match = re.search(pattern, text, re.IGNORECASE)
    
    if match:
        is_relevant = match.group(1).lower() == "yes"
        relevant_score = int(match.group(2))
        return DocRelevance(is_relevant=is_relevant, relevant_score=relevant_score)
    
    return None


