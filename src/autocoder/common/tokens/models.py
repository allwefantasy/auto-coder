from typing import List, Dict, Optional
from dataclasses import dataclass


@dataclass
class TokenResult:
    """单个文件的 token 统计结果"""
    file_path: str
    token_count: int
    char_count: int
    line_count: int
    success: bool = True
    error: Optional[str] = None


@dataclass
class DirectoryTokenResult:
    """目录的 token 统计结果"""
    directory_path: str
    total_tokens: int
    file_count: int
    skipped_count: int
    files: List[TokenResult]
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
