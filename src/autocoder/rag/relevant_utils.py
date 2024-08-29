from autocoder.common import AutoCoderArgs, SourceCode
from pydantic import BaseModel

class DocRelevance(BaseModel):
    is_relevant: bool
    relevant_score: int

class FilterDoc(BaseModel):
    source_code: SourceCode
    relevance: DocRelevance

def parse_relevance():
    pass


