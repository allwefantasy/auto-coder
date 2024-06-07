import re
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum

class SymbolsInfo(BaseModel):
    usage: Optional[str] = Field(None, alias="用途")
    functions: List[str] = Field([], alias="函数")
    variables: List[str] = Field([], alias="变量")
    classes: List[str] = Field([], alias="类")
    import_statements: List[str] = Field([], alias="导入语句")

def extract_symbols(text: str) -> SymbolsInfo:
    patterns = {
        "usage": r"用途：(.+)",
        "functions": r"函数：(.+)",
        "variables": r"变量：(.+)",
        "classes": r"类：(.+)",
        "import_statements": r"导入语句：(.+)",
    }

    info = SymbolsInfo()
    for field, pattern in patterns.items():
        match = re.search(pattern, text)
        if match:
            value = match.group(1).strip()
            if field == "import_statements":
                value = [v.strip() for v in value.split("^^")]
            elif field == "functions" or field == "variables" or field == "classes":
                value = [v.strip() for v in value.split(",")]
            setattr(info, field, value)

    return info