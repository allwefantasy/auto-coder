"""
Pull Request 数据模型定义
"""
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import os
import json
from pathlib import Path


class PlatformType(str, Enum):
    """支持的代码托管平台类型"""
    GITHUB = "github"
    GITLAB = "gitlab" 
    GITEE = "gitee"
    GITCODE = "gitcode"


@dataclass
class PRConfig:
    """Pull Request 配置类"""
    platform: PlatformType
    token: str
    base_url: Optional[str] = None
    timeout: int = 30
    verify_ssl: bool = True
    retry_count: int = 3
    default_labels: List[str] = field(default_factory=list)
    default_assignees: List[str] = field(default_factory=list)
    
    # 平台特定配置
    draft: bool = False
    maintainer_can_modify: bool = True
    remove_source_branch: bool = False
    squash: bool = False
    
    def __post_init__(self):
        if isinstance(self.platform, str):
            self.platform = PlatformType(self.platform)
        if self.base_url is None:
            self.base_url = self._get_default_base_url()
    
    def _get_default_base_url(self) -> str:
        default_urls = {
            PlatformType.GITHUB: "https://api.github.com",
            PlatformType.GITLAB: "https://gitlab.com/api/v4",
            PlatformType.GITEE: "https://gitee.com/api/v5",
            PlatformType.GITCODE: "https://gitcode.net/api/v4"
        }
        return default_urls.get(self.platform, "")
    
    @classmethod
    def from_env(cls, platform: str) -> 'PRConfig':
        env_mappings = {
            PlatformType.GITHUB: "GITHUB_TOKEN",
            PlatformType.GITLAB: "GITLAB_TOKEN", 
            PlatformType.GITEE: "GITEE_TOKEN",
            PlatformType.GITCODE: "GITCODE_TOKEN"
        }
        platform_type = PlatformType(platform)
        token_env = env_mappings.get(platform_type)
        if not token_env:
            raise ValueError(f"不支持的平台类型: {platform}")
        token = os.getenv(token_env)
        if not token:
            raise ValueError(f"环境变量 {token_env} 未设置")
        return cls(platform=platform_type, token=token)


@dataclass
class RepoInfo:
    """仓库信息"""
    owner: str
    name: str
    platform: PlatformType
    full_name: str = field(init=False)
    
    def __post_init__(self):
        self.full_name = f"{self.owner}/{self.name}"


@dataclass 
class PRData:
    """Pull Request 数据"""
    title: str
    description: str
    source_branch: str
    target_branch: str
    labels: List[str] = field(default_factory=list)
    assignees: List[str] = field(default_factory=list)
    reviewers: List[str] = field(default_factory=list)
    draft: bool = False
    template_type: Optional[str] = None
    template_vars: Dict[str, str] = field(default_factory=dict)


@dataclass
class PRResult:
    """Pull Request 操作结果"""
    success: bool
    pr_number: Optional[int] = None
    pr_url: Optional[str] = None
    pr_id: Optional[str] = None
    error_message: Optional[str] = None
    error_code: Optional[str] = None
    platform: Optional[PlatformType] = None
    raw_response: Optional[Dict[str, Any]] = None
    retry_after: Optional[int] = None


@dataclass
class PRInfo:
    """Pull Request 详细信息"""
    number: int
    title: str
    description: str
    state: str
    source_branch: str
    target_branch: str
    author: str
    created_at: str
    updated_at: str
    merged_at: Optional[str] = None
    pr_url: str = ""
    labels: List[str] = field(default_factory=list)
    assignees: List[str] = field(default_factory=list)
    reviewers: List[str] = field(default_factory=list)
    mergeable: Optional[bool] = None
    draft: bool = False
    raw_data: Optional[Dict[str, Any]] = None


# 默认模板配置
DEFAULT_TEMPLATES = {
    "bug_fix": {
        "title_prefix": "🐛 Bug Fix:",
        "description_template": """
## 问题描述
{problem_description}

## 解决方案
{solution_description}

## 测试
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] 手动测试验证
        """
    },
    "feature": {
        "title_prefix": "✨ Feature:",
        "description_template": """
## 新功能说明
{feature_description}

## 实现细节
{implementation_details}

## 使用示例
{usage_examples}
        """
    }
}