from enum import Enum
import pydantic
from typing import List, Dict, Tuple,Any,Optional
class Mode(Enum):
    MULTI_ROUND = "multi_round"
    SINGLE_ROUND = "single_round"

class StepNum(pydantic.BaseModel):
    step_num:int= pydantic.Field(1,description="总共步骤数")
    content:int= pydantic.Field(1,description="详细的执行步骤，每个步骤需要包含一个shell/python 代码块")    

class CodeGenerateResult(pydantic.BaseModel):
    contents:List[str]
    conversations:List[List[Dict[str, Any]]]
    metadata:Dict[str, Any] = {}

class MergeCodeWithoutEffect(pydantic.BaseModel):
    success_blocks: List[Tuple[str, str]]
    failed_blocks: List[Any]
    merged_blocks: Optional[Any] = None