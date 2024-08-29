from autocoder.common import AutoCoderArgs, SourceCode
from pydantic import BaseModel

class FilterDoc(BaseModel):
    source_code: SourceCode
    relevance: DocRelevance

from .relevant_utils import DocRelevance, parse_relevance

class LongContextRAG:
    def __init__(self, llm: ByzerLLM, args: AutoCoderArgs, path: str) -> None:
        self.llm = llm
        self.args = args
        self.path = path