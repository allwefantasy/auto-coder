
import os
import json
from typing import Dict, Optional
from loguru import logger

FILTER_RULES_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
    ".cache", "filterrules"
)

_cache_rules: Optional[Dict] = None

def load_filter_rules() -> Dict:
    global _cache_rules
    if _cache_rules is not None:
        return _cache_rules
    _cache_rules = {"whitelist": [], "blacklist": []}
    try:
        if os.path.exists(FILTER_RULES_PATH):
            with open(FILTER_RULES_PATH, "r", encoding="utf-8") as f:
                _cache_rules = json.load(f)
    except Exception as e:
        logger.warning(f"Failed to load filterrules: {e}")
    return _cache_rules

def should_parse_image(file_path: str) -> bool:
    """
    判断某个文件是否需要对图片进行解析。

    返回:
        True 表示应该解析
        False 表示不解析
    """
    rules = load_filter_rules()
    whitelist = rules.get("whitelist", [])
    blacklist = rules.get("blacklist", [])

    # 优先匹配黑名单
    for pattern in blacklist:
        if pattern in file_path:
            return False

    # 再匹配白名单
    for pattern in whitelist:
        if pattern in file_path:
            return True

    # 默认允许
    return True
