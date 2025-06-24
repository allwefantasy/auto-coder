"""
Pull Request 配置管理
"""
import os
from typing import Dict, Any, Optional
from .models import PRConfig, PlatformType
from .exceptions import ConfigurationError


def get_config(platform: str, **overrides) -> PRConfig:
    """
    获取平台配置
    
    Args:
        platform: 平台名称
        **overrides: 配置覆盖参数
    
    Returns:
        配置对象
    """
    # 从环境变量加载配置
    env_config = _load_from_env(platform)
    
    # 合并配置
    merged_config = {}
    if env_config:
        merged_config.update(env_config)
    merged_config.update(overrides)
    
    # 验证必需的配置
    if 'token' not in merged_config:
        raise ConfigurationError(f"平台 {platform} 缺少必需的 token 配置")
    
    return PRConfig(platform=PlatformType(platform), **merged_config)


def _load_from_env(platform: str) -> Dict[str, Any]:
    """从环境变量加载配置"""
    env_mappings = {
        'github': {
            'token': 'GITHUB_TOKEN',
            'base_url': 'GITHUB_BASE_URL'
        },
        'gitlab': {
            'token': 'GITLAB_TOKEN',
            'base_url': 'GITLAB_BASE_URL'
        },
        'gitee': {
            'token': 'GITEE_TOKEN',
            'base_url': 'GITEE_BASE_URL'
        },
        'gitcode': {
            'token': 'GITCODE_TOKEN',
            'base_url': 'GITCODE_BASE_URL'
        }
    }
    
    mapping = env_mappings.get(platform, {})
    config = {}
    
    for key, env_var in mapping.items():
        value = os.getenv(env_var)
        if value:
            config[key] = value
    
    return config