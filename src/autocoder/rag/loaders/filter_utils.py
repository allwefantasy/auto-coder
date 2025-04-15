import os
import json
import threading
from typing import Dict, Optional, List
from loguru import logger
from functools import lru_cache

class FilterRuleManager:
    '''
    单例模式的过滤规则管理器。支持按文件类型定义不同的过滤规则。
    
    支持的规则格式：
    {
        "image": {
            "whitelist": ["*.png", "*.jpg"],
            "blacklist": ["*/private/*"]
        },
        "document": {
            "whitelist": ["*.pdf", "*.docx"],
            "blacklist": ["*/tmp/*"]
        },
        "default": {
            "whitelist": [],
            "blacklist": ["*/node_modules/*", "*/.*"]
        }
    }
    '''
    _instance = None
    _lock = threading.RLock()  # 使用可重入锁避免死锁

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:  # 双重检查锁定模式
                    cls._instance = super(FilterRuleManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    @classmethod
    def get_instance(cls):
        return cls()  # 直接调用__new__，不需要重复加锁

    def __init__(self):
        with self._lock:
            if hasattr(self, '_initialized') and self._initialized:
                return
                
            self.source_dir = os.getcwd()
            self.filter_rules_path = os.path.join(self.source_dir, ".cache", "filterrules")
            self._cache_rules: Optional[Dict] = None
            self._cache_mtime: Optional[float] = None
            self._rule_lock = threading.RLock()  # 单独的锁用于规则访问
            self._initialized = True

    def load_filter_rules(self) -> Dict:
        # 先检查是否需要重新加载，不持有锁
        current_mtime = self._get_file_mtime()
        need_reload = False

        if self._cache_rules is None:
            need_reload = True
        elif current_mtime is not None and self._cache_mtime != current_mtime:
            need_reload = True

        # 只在需要重新加载时获取锁
        if need_reload:
            with self._rule_lock:
                # 双重检查，避免多线程重复加载
                current_mtime = self._get_file_mtime()
                if self._cache_rules is None or (current_mtime is not None and self._cache_mtime != current_mtime):
                    self._load_rules_from_file(current_mtime)

        # 返回规则副本，避免外部修改影响缓存
        with self._rule_lock:
            return self._cache_rules.copy() if self._cache_rules else self._get_default_rules()

    def _get_file_mtime(self) -> Optional[float]:
        """获取文件修改时间，与IO相关的操作单独提取出来"""
        try:
            return os.path.getmtime(self.filter_rules_path) if os.path.exists(self.filter_rules_path) else None
        except Exception:
            logger.warning(f"Failed to get mtime for {self.filter_rules_path}")
            return None

    def _get_default_rules(self) -> Dict:
        """返回默认的规则结构"""
        return {
            "default": {
                "whitelist": [],
                "blacklist": []
            }
        }

    def _load_rules_from_file(self, current_mtime: Optional[float]) -> None:
        """从文件加载规则，仅在持有锁时调用"""
        self._cache_rules = self._get_default_rules()
        try:
            if os.path.exists(self.filter_rules_path):
                with open(self.filter_rules_path, "r", encoding="utf-8") as f:
                    file_rules = json.load(f)
                    
                    # 转换旧格式规则到新格式（如果需要）
                    if "whitelist" in file_rules or "blacklist" in file_rules:
                        # 旧格式转换为新格式
                        self._cache_rules = {
                            "default": {
                                "whitelist": file_rules.get("whitelist", []),
                                "blacklist": file_rules.get("blacklist", [])
                            }
                        }
                        logger.info("Converted old format rules to new format")
                    else:
                        # 新格式直接使用
                        self._cache_rules = file_rules
            self._cache_mtime = current_mtime
        except Exception as e:
            logger.warning(f"Failed to load filterrules: {e}")

    @lru_cache(maxsize=1024)  # 缓存频繁使用的路径判断结果
    def should_parse_file(self, file_path: str, file_type: str = "default") -> bool:
        """
        判断某个文件是否需要进行解析。
        
        参数:
            file_path: 文件路径
            file_type: 文件类型（如"image"、"document"等），默认为"default"
            
        返回:
            True 表示应该解析
            False 表示不解析
        """
        import fnmatch
        
        rules = self.load_filter_rules()
        
        # 获取指定类型的规则，如果不存在则使用默认规则
        type_rules = rules.get(file_type, rules.get("default", {"whitelist": [], "blacklist": []}))
        whitelist = type_rules.get("whitelist", [])
        blacklist = type_rules.get("blacklist", [])
        
        # 优先匹配黑名单
        for pattern in blacklist:
            if fnmatch.fnmatch(file_path, pattern):
                return False
        
        # 如果白名单为空，则默认所有文件都通过（除非被黑名单过滤）
        if not whitelist:
            return True
            
        # 匹配白名单
        for pattern in whitelist:
            if fnmatch.fnmatch(file_path, pattern):
                return True
                
        # 有白名单但不匹配，不通过
        return False
        
    # 保持向后兼容
    def should_parse_image(self, file_path: str) -> bool:
        """
        判断某个图片文件是否需要解析（兼容旧版API）
        """
        return self.should_parse_file(file_path, "image")
