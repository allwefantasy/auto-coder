"""
配置类测试
"""

import pytest
import os
import tempfile
from pathlib import Path
from autocoder.common.conversations.config import ConversationManagerConfig


class TestConversationManagerConfig:
    """测试ConversationManagerConfig配置类"""
    
    def test_config_creation_with_defaults(self):
        """测试使用默认值创建配置"""
        config = ConversationManagerConfig()
        
        assert config.storage_path == "./.auto-coder/conversations"
        assert config.max_cache_size == 100
        assert config.cache_ttl == 300.0
        assert config.lock_timeout == 10.0
        assert config.backup_enabled is True
        assert config.backup_interval == 3600.0
        assert config.max_backups == 10
        assert config.enable_compression is False
        assert config.log_level == "INFO"
    
    def test_config_creation_with_custom_values(self):
        """测试使用自定义值创建配置"""
        config = ConversationManagerConfig(
            storage_path="/custom/path",
            max_cache_size=200,
            cache_ttl=600.0,
            lock_timeout=20.0,
            backup_enabled=False,
            backup_interval=7200.0,
            max_backups=5,
            enable_compression=True,
            log_level="DEBUG"
        )
        
        assert config.storage_path == "/custom/path"
        assert config.max_cache_size == 200
        assert config.cache_ttl == 600.0
        assert config.lock_timeout == 20.0
        assert config.backup_enabled is False
        assert config.backup_interval == 7200.0
        assert config.max_backups == 5
        assert config.enable_compression is True
        assert config.log_level == "DEBUG"
    
    def test_config_validation_max_cache_size(self):
        """测试缓存大小验证"""
        # 有效值
        config = ConversationManagerConfig(max_cache_size=50)
        assert config.max_cache_size == 50
        
        # 无效值
        with pytest.raises(ValueError):
            ConversationManagerConfig(max_cache_size=0)
        
        with pytest.raises(ValueError):
            ConversationManagerConfig(max_cache_size=-1)
    
    def test_config_validation_cache_ttl(self):
        """测试缓存TTL验证"""
        # 有效值
        config = ConversationManagerConfig(cache_ttl=60.0)
        assert config.cache_ttl == 60.0
        
        # 无效值
        with pytest.raises(ValueError):
            ConversationManagerConfig(cache_ttl=0)
        
        with pytest.raises(ValueError):
            ConversationManagerConfig(cache_ttl=-1.0)
    
    def test_config_validation_lock_timeout(self):
        """测试锁超时验证"""
        # 有效值
        config = ConversationManagerConfig(lock_timeout=5.0)
        assert config.lock_timeout == 5.0
        
        # 无效值
        with pytest.raises(ValueError):
            ConversationManagerConfig(lock_timeout=0)
        
        with pytest.raises(ValueError):
            ConversationManagerConfig(lock_timeout=-1.0)
    
    def test_config_validation_backup_interval(self):
        """测试备份间隔验证"""
        # 有效值
        config = ConversationManagerConfig(backup_interval=1800.0)
        assert config.backup_interval == 1800.0
        
        # 无效值
        with pytest.raises(ValueError):
            ConversationManagerConfig(backup_interval=0)
        
        with pytest.raises(ValueError):
            ConversationManagerConfig(backup_interval=-1.0)
    
    def test_config_validation_max_backups(self):
        """测试最大备份数验证"""
        # 有效值
        config = ConversationManagerConfig(max_backups=20)
        assert config.max_backups == 20
        
        # 无效值
        with pytest.raises(ValueError):
            ConversationManagerConfig(max_backups=0)
        
        with pytest.raises(ValueError):
            ConversationManagerConfig(max_backups=-1)
    
    def test_config_validation_log_level(self):
        """测试日志级别验证"""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        
        for level in valid_levels:
            config = ConversationManagerConfig(log_level=level)
            assert config.log_level == level
        
        # 无效级别
        with pytest.raises(ValueError):
            ConversationManagerConfig(log_level="INVALID")
        
        with pytest.raises(ValueError):
            ConversationManagerConfig(log_level="debug")  # 小写无效
    
    def test_config_validation_storage_path(self):
        """测试存储路径验证"""
        # 有效路径
        config = ConversationManagerConfig(storage_path="/valid/path")
        assert config.storage_path == "/valid/path"
        
        # 空路径
        with pytest.raises(ValueError):
            ConversationManagerConfig(storage_path="")
        
        # None路径
        with pytest.raises(ValueError):
            ConversationManagerConfig(storage_path=None)
    
    def test_config_from_dict(self):
        """测试从字典创建配置"""
        data = {
            "storage_path": "/test/path",
            "max_cache_size": 150,
            "cache_ttl": 450.0,
            "lock_timeout": 15.0,
            "backup_enabled": False,
            "backup_interval": 1800.0,
            "max_backups": 15,
            "enable_compression": True,
            "log_level": "DEBUG"
        }
        
        config = ConversationManagerConfig.from_dict(data)
        
        assert config.storage_path == "/test/path"
        assert config.max_cache_size == 150
        assert config.cache_ttl == 450.0
        assert config.lock_timeout == 15.0
        assert config.backup_enabled is False
        assert config.backup_interval == 1800.0
        assert config.max_backups == 15
        assert config.enable_compression is True
        assert config.log_level == "DEBUG"
    
    def test_config_from_dict_with_missing_fields(self):
        """测试从不完整字典创建配置（使用默认值）"""
        data = {
            "storage_path": "/test/path",
            "max_cache_size": 150
        }
        
        config = ConversationManagerConfig.from_dict(data)
        
        assert config.storage_path == "/test/path"
        assert config.max_cache_size == 150
        # 其他字段应该使用默认值
        assert config.cache_ttl == 300.0
        assert config.lock_timeout == 10.0
        assert config.backup_enabled is True
    
    def test_config_from_dict_with_invalid_data(self):
        """测试从包含无效数据的字典创建配置"""
        data = {
            "storage_path": "/test/path",
            "max_cache_size": -1  # 无效值
        }
        
        with pytest.raises(ValueError):
            ConversationManagerConfig.from_dict(data)
    
    def test_config_to_dict(self):
        """测试配置转换为字典"""
        config = ConversationManagerConfig(
            storage_path="/test/path",
            max_cache_size=150,
            cache_ttl=450.0
        )
        
        data = config.to_dict()
        
        assert isinstance(data, dict)
        assert data["storage_path"] == "/test/path"
        assert data["max_cache_size"] == 150
        assert data["cache_ttl"] == 450.0
        assert data["lock_timeout"] == 10.0  # 默认值
        assert data["backup_enabled"] is True  # 默认值
    
    def test_config_serialization_round_trip(self):
        """测试配置序列化往返转换"""
        original_config = ConversationManagerConfig(
            storage_path="/original/path",
            max_cache_size=250,
            log_level="DEBUG"
        )
        
        # 序列化
        data = original_config.to_dict()
        
        # 反序列化
        restored_config = ConversationManagerConfig.from_dict(data)
        
        # 验证一致性
        assert restored_config.storage_path == original_config.storage_path
        assert restored_config.max_cache_size == original_config.max_cache_size
        assert restored_config.log_level == original_config.log_level
        assert restored_config.cache_ttl == original_config.cache_ttl
    
    def test_config_repr(self):
        """测试配置的字符串表示"""
        config = ConversationManagerConfig(storage_path="/test/path")
        repr_str = repr(config)
        
        assert "ConversationManagerConfig" in repr_str
        assert "/test/path" in repr_str
    
    def test_config_equality(self):
        """测试配置相等性比较"""
        config1 = ConversationManagerConfig(storage_path="/path1")
        config2 = ConversationManagerConfig(storage_path="/path1")
        config3 = ConversationManagerConfig(storage_path="/path2")
        
        assert config1 == config2
        assert config1 != config3
    
    def test_config_copy(self):
        """测试配置复制"""
        original = ConversationManagerConfig(
            storage_path="/original",
            max_cache_size=200
        )
        
        copy_config = original.copy()
        
        # 验证内容相同
        assert copy_config.storage_path == original.storage_path
        assert copy_config.max_cache_size == original.max_cache_size
        
        # 验证是不同对象
        assert copy_config is not original
        
        # 修改副本不影响原对象
        copy_config.storage_path = "/modified"
        assert original.storage_path == "/original"
    
    def test_config_update(self):
        """测试配置更新"""
        config = ConversationManagerConfig()
        
        # 更新单个字段
        config.update(storage_path="/updated/path")
        assert config.storage_path == "/updated/path"
        
        # 更新多个字段
        config.update(
            max_cache_size=300,
            log_level="ERROR"
        )
        assert config.max_cache_size == 300
        assert config.log_level == "ERROR"
        
        # 验证其他字段未改变
        assert config.cache_ttl == 300.0  # 默认值
    
    def test_config_validation_in_update(self):
        """测试更新时的配置验证"""
        config = ConversationManagerConfig()
        
        # 无效更新应该抛出异常
        with pytest.raises(ValueError):
            config.update(max_cache_size=-1)
        
        with pytest.raises(ValueError):
            config.update(log_level="INVALID")
        
        # 原配置应该保持不变
        assert config.max_cache_size == 100  # 默认值
        assert config.log_level == "INFO"  # 默认值


class TestConfigEnvironmentVariables:
    """测试配置从环境变量加载"""
    
    def test_config_from_env_vars(self):
        """测试从环境变量加载配置"""
        # 设置环境变量
        os.environ["CONVERSATION_STORAGE_PATH"] = "/env/path"
        os.environ["CONVERSATION_MAX_CACHE_SIZE"] = "500"
        os.environ["CONVERSATION_LOG_LEVEL"] = "DEBUG"
        
        try:
            config = ConversationManagerConfig.from_env()
            
            assert config.storage_path == "/env/path"
            assert config.max_cache_size == 500
            assert config.log_level == "DEBUG"
            # 未设置的应该使用默认值
            assert config.cache_ttl == 300.0
        finally:
            # 清理环境变量
            os.environ.pop("CONVERSATION_STORAGE_PATH", None)
            os.environ.pop("CONVERSATION_MAX_CACHE_SIZE", None)
            os.environ.pop("CONVERSATION_LOG_LEVEL", None)
    
    def test_config_from_env_vars_with_defaults(self):
        """测试环境变量不存在时使用默认值"""
        # 确保环境变量不存在
        for key in ["CONVERSATION_STORAGE_PATH", "CONVERSATION_MAX_CACHE_SIZE"]:
            os.environ.pop(key, None)
        
        config = ConversationManagerConfig.from_env()
        
        # 应该使用默认值
        assert config.storage_path == "./.auto-coder/conversations"
        assert config.max_cache_size == 100
    
    def test_config_from_env_vars_with_invalid_values(self):
        """测试环境变量包含无效值"""
        os.environ["CONVERSATION_MAX_CACHE_SIZE"] = "invalid"
        
        try:
            with pytest.raises(ValueError):
                ConversationManagerConfig.from_env()
        finally:
            os.environ.pop("CONVERSATION_MAX_CACHE_SIZE", None)


class TestConfigFileOperations:
    """测试配置文件操作"""
    
    def test_config_save_and_load_from_file(self, temp_dir):
        """测试配置保存和加载"""
        config_file = os.path.join(temp_dir, "config.json")
        
        # 创建配置
        original_config = ConversationManagerConfig(
            storage_path="/file/path",
            max_cache_size=400,
            log_level="WARNING"
        )
        
        # 保存到文件
        original_config.save_to_file(config_file)
        
        # 从文件加载
        loaded_config = ConversationManagerConfig.load_from_file(config_file)
        
        # 验证一致性
        assert loaded_config.storage_path == original_config.storage_path
        assert loaded_config.max_cache_size == original_config.max_cache_size
        assert loaded_config.log_level == original_config.log_level
    
    def test_config_load_from_nonexistent_file(self):
        """测试从不存在的文件加载配置"""
        with pytest.raises(FileNotFoundError):
            ConversationManagerConfig.load_from_file("/nonexistent/file.json")
    
    def test_config_load_from_invalid_json_file(self, temp_dir):
        """测试从无效JSON文件加载配置"""
        config_file = os.path.join(temp_dir, "invalid.json")
        
        # 写入无效JSON
        with open(config_file, 'w') as f:
            f.write("invalid json content")
        
        with pytest.raises(ValueError):
            ConversationManagerConfig.load_from_file(config_file)