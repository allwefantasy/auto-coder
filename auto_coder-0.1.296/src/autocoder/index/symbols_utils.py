import re
from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum


class SymbolType(Enum):
    USAGE = "usage"
    FUNCTIONS = "functions"
    VARIABLES = "variables"
    CLASSES = "classes"
    IMPORT_STATEMENTS = "import_statements"


class SymbolsInfo(BaseModel):
    usage: Optional[str] = Field(None, description="用途")
    functions: List[str] = Field([], description="函数")
    variables: List[str] = Field([], description="变量")
    classes: List[str] = Field([], description="类")
    import_statements: List[str] = Field([], description="导入语句")


def extract_symbols(text: str) -> SymbolsInfo:
    patterns = {
        "usage": r"用途：(.+)",
        "functions": r"函数：(.+)",
        "variables": r"变量：(.+)",
        "classes": r"类：(.+)",
        "import_statements": r"导入语句：(.+)",
    }    
    ## index.json 中可能会出现 text 为 null 的情况
    if not text or text == "null":        
        return SymbolsInfo(usage="",functions=[],variables=[],classes=[],import_statements=[])
    
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


def symbols_info_to_str(info: SymbolsInfo, symbol_types: List[SymbolType]) -> str:
    result = []
    for symbol_type in symbol_types:
        value = getattr(info, symbol_type.value)        
        if value:
            if symbol_type == SymbolType.IMPORT_STATEMENTS:
                value_str = "^^".join(value)
            elif symbol_type in [
                SymbolType.FUNCTIONS,
                SymbolType.VARIABLES,
                SymbolType.CLASSES,
            ]:
                value_str = ",".join(value)
            else:
                value_str = value
            result.append(f"{symbol_type.value}：{value_str}")

    return "\n".join(result)
