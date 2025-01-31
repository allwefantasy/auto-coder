import pydantic
from typing import List

class IndexItem(pydantic.BaseModel):
    module_name: str
    symbols: str
    last_modified: float
    md5: str  # 新增文件内容的MD5哈希值字段


class TargetFile(pydantic.BaseModel):
    file_path: str
    reason: str = pydantic.Field(
        ..., description="The reason why the file is the target file"
    )


class VerifyFileRelevance(pydantic.BaseModel):
    relevant_score: int
    reason: str


class FileList(pydantic.BaseModel):
    file_list: List[TargetFile]

class FileNumberList(pydantic.BaseModel):
    file_list: List[int]    