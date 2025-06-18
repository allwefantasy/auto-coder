"""
PersistConversationManager 配置类定义
"""

import os
import json
from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from copy import deepcopy


@dataclass
class ConversationManagerConfig:
    """对话管理器配置类"""
    
    storage_path: str = "./.auto-coder/conversations"
    max_cache_size: int = 100
    cache_ttl: float = 300.0
    lock_timeout: float = 10.0
    backup_enabled: bool = True
    backup_interval: float = 3600.0
    max_backups: int = 10
    enable_compression: bool = False
    log_level: str = "INFO"
    
    def __post_init__(self):
        """配置验证"""
        self._validate()
    
    def _validate(self):
        """验证配置数据"""
        # 验证存储路径
        if not self.storage_path or not isinstance(self.storage_path, str):
            raise ValueError("存储路径不能为空")
        
        # 验证缓存大小
        if not isinstance(self.max_cache_size, int) or self.max_cache_size <= 0:
            raise ValueError("缓存大小必须是正整数")
        
        # 验证缓存TTL
        if not isinstance(self.cache_ttl, (int, float)) or self.cache_ttl <= 0:
            raise ValueError("缓存TTL必须是正数")
        
        # 验证锁超时
        if not isinstance(self.lock_timeout, (int, float)) or self.lock_timeout <= 0:
            raise ValueError("锁超时时间必须是正数")
        
        # 验证备份间隔
        if not isinstance(self.backup_interval, (int, float)) or self.backup_interval <= 0:
            raise ValueError("备份间隔必须是正数")
        
        # 验证最大备份数
        if not isinstance(self.max_backups, int) or self.max_backups <= 0:
            raise ValueError("最大备份数必须是正整数")
        
        # 验证日志级别
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if self.log_level not in valid_levels:
            raise ValueError(f"无效的日志级别: {self.log_level}，有效级别: {valid_levels}")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "storage_path": self.storage_path,
            "max_cache_size": self.max_cache_size,
            "cache_ttl": self.cache_ttl,
            "lock_timeout": self.lock_timeout,
            "backup_enabled": self.backup_enabled,
            "backup_interval": self.backup_interval,
            "max_backups": self.max_backups,
            "enable_compression": self.enable_compression,
            "log_level": self.log_level
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ConversationManagerConfig":
        """从字典创建配置"""
        # 创建默认配置
        config = cls()
        
        # 更新配置字段
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        
        # 重新验证
        config._validate()
        
        return config
    
    @classmethod
    def from_env(cls, prefix: str = "CONVERSATION_") -> "ConversationManagerConfig":
        """从环境变量创建配置"""
        config = cls()
        
        # 环境变量映射
        env_mapping = {
            f"{prefix}STORAGE_PATH": "storage_path",
            f"{prefix}MAX_CACHE_SIZE": "max_cache_size",
            f"{prefix}CACHE_TTL": "cache_ttl",
            f"{prefix}LOCK_TIMEOUT": "lock_timeout",
            f"{prefix}BACKUP_ENABLED": "backup_enabled",
            f"{prefix}BACKUP_INTERVAL": "backup_interval",
            f"{prefix}MAX_BACKUPS": "max_backups",
            f"{prefix}ENABLE_COMPRESSION": "enable_compression",
            f"{prefix}LOG_LEVEL": "log_level"
        }
        
        for env_key, attr_name in env_mapping.items():
            env_value = os.environ.get(env_key)
            if env_value is not None:
                # 类型转换
                try:
                    if attr_name in ["max_cache_size", "max_backups"]:
                        value = int(env_value)
                    elif attr_name in ["cache_ttl", "lock_timeout", "backup_interval"]:
                        value = float(env_value)
                    elif attr_name in ["backup_enabled", "enable_compression"]:
                        value = env_value.lower() in ["true", "1", "yes", "on"]
                    else:
                        value = env_value
                    
                    setattr(config, attr_name, value)
                except (ValueError, TypeError) as e:
                    raise ValueError(f"环境变量 {env_key} 的值 '{env_value}' 无效: {e}")
        
        # 重新验证
        config._validate()
        
        return config
    
    def save_to_file(self, file_path: str):
        """保存配置到文件"""
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> "ConversationManagerConfig":
        """从文件加载配置"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"配置文件不存在: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            return cls.from_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"配置文件格式错误: {e}")
    
    def copy(self) -> "ConversationManagerConfig":
        """创建配置的深拷贝"""
        return ConversationManagerConfig.from_dict(self.to_dict())
    
    def update(self, **kwargs):
        """更新配置字段"""
        # 先备份当前配置
        backup_values = {}
        for key in kwargs.keys():
            if hasattr(self, key):
                backup_values[key] = getattr(self, key)
            else:
                raise AttributeError(f"配置类没有属性: {key}")
        
        # 尝试更新
        try:
            for key, value in kwargs.items():
                setattr(self, key, value)
            # 重新验证
            self._validate()
        except Exception:
            # 如果验证失败，恢复原值
            for key, value in backup_values.items():
                setattr(self, key, value)
            raise
    
    def __repr__(self) -> str:
        """字符串表示"""
        return (f"ConversationManagerConfig("
                f"storage_path='{self.storage_path}', "
                f"max_cache_size={self.max_cache_size}, "
                f"cache_ttl={self.cache_ttl}, "
                f"lock_timeout={self.lock_timeout}, "
                f"backup_enabled={self.backup_enabled}, "
                f"log_level='{self.log_level}')")
    
    def __eq__(self, other) -> bool:
        """相等性比较"""
        if not isinstance(other, ConversationManagerConfig):
            return False
        
        return self.to_dict() == other.to_dict() 