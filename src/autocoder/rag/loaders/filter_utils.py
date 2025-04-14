
import os
import json
import threading
from typing import Dict, Optional
from loguru import logger

class FilterRuleManager:
    '''
    {
        "whitelist": [
            "glob:*.png",
            "regex:^/tmp/.*hidden.*"
        ],
        "blacklist": [
            "glob:*/private/*",
            "regex:.*/secret/.*\\.jpg$"
        ]
        }
    '''
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(FilterRuleManager, cls).__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self, llm, source_dir: str):
        """
        初始化过滤规则管理器

        参数:
            llm: 大模型对象，当前未使用，预留
            source_dir: 项目根目录路径
        """
        if self._initialized:
            return
            
        self.llm = llm
        self.source_dir = source_dir
        self.filter_rules_path = os.path.join(self.source_dir, ".cache", "filterrules")
        self._cache_rules: Optional[Dict] = None
        self._cache_mtime: Optional[float] = None
        self._initialized = True

    def load_filter_rules(self) -> Dict:
        try:
            current_mtime = os.path.getmtime(self.filter_rules_path) if os.path.exists(self.filter_rules_path) else None
        except Exception:
            current_mtime = None

        need_reload = False

        # 如果缓存为空，或者文件已更新，触发重新加载
        if self._cache_rules is None:
            need_reload = True
        elif current_mtime is not None and self._cache_mtime != current_mtime:
            need_reload = True

        if need_reload:
            self._cache_rules = {"whitelist": [], "blacklist": []}
            try:
                if os.path.exists(self.filter_rules_path):
                    with open(self.filter_rules_path, "r", encoding="utf-8") as f:
                        self._cache_rules = json.load(f)
                self._cache_mtime = current_mtime
            except Exception as e:
                logger.warning(f"Failed to load filterrules: {e}")

        return self._cache_rules or {"whitelist": [], "blacklist": []}

    def should_parse_image(self, file_path: str) -> bool:
        """
        判断某个文件是否需要对图片进行解析。

        支持规则格式：
        - glob通配符匹配，示例："glob:*.png" 或 "*.png"
        - 正则表达式匹配，示例："regex:^/tmp/.*hidden.*"

        返回:
            True 表示应该解析
            False 表示不解析
        """
        import fnmatch
        import re

        rules = self.load_filter_rules()
        whitelist = rules.get("whitelist", [])
        blacklist = rules.get("blacklist", [])

        def match_pattern(pattern: str, path: str) -> bool:
            if pattern.startswith("glob:"):
                pat = pattern[len("glob:"):]
                return fnmatch.fnmatch(path, pat)
            elif pattern.startswith("regex:"):
                pat = pattern[len("regex:"):]
                try:
                    return re.search(pat, path) is not None
                except re.error:
                    logger.warning(f"Invalid regex pattern: {pat}")
                    return False
            else:
                # 默认按glob处理
                return fnmatch.fnmatch(path, pattern)

        # 优先匹配黑名单
        for pattern in blacklist:
            if match_pattern(pattern, file_path):
                return False

        # 再匹配白名单
        for pattern in whitelist:
            if match_pattern(pattern, file_path):
                return True

        # 默认不解析
        return False
