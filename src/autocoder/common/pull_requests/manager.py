"""
Pull Request 主管理器
"""
from typing import Optional, List, Dict, Any
from loguru import logger

from .models import PRConfig, PRData, PRResult, PRInfo, RepoInfo, PlatformType, DEFAULT_TEMPLATES
from .providers import PROVIDERS
from .utils import detect_platform_from_repo, get_repo_info_from_path, validate_repo_path
from .exceptions import (
    PRError, PlatformNotSupportedError, ConfigurationError, ValidationError
)
from .config import get_config


class PullRequestManager:
    """Pull Request 主管理器"""
    
    def __init__(self, config: Optional[PRConfig] = None):
        self.config = config
        self._provider = None
        self._templates = DEFAULT_TEMPLATES.copy()
    
    def _get_provider(self, platform: Optional[str] = None, repo_path: Optional[str] = None):
        """获取平台提供者"""
        if self.config and not platform:
            platform = self.config.platform.value
        elif not platform and repo_path:
            # 自动检测平台
            detected_platform = detect_platform_from_repo(repo_path)
            if not detected_platform:
                raise PlatformNotSupportedError("无法从仓库路径检测平台类型")
            platform = detected_platform.value
        elif not platform:
            raise ValidationError("必须指定平台类型或提供仓库路径")
        
        if platform not in PROVIDERS:
            raise PlatformNotSupportedError(f"不支持的平台: {platform}")
        
        # 使用现有配置或创建新配置
        if self.config and self.config.platform.value == platform:
            config = self.config
        else:
            try:
                config = get_config(platform)
            except ConfigurationError:
                raise ConfigurationError(f"平台 {platform} 的配置未找到")
        
        provider_class = PROVIDERS[platform]
        return provider_class(config)
    
    def create_pull_request(
        self,
        repo_path: str,
        source_branch: str,
        target_branch: str,
        title: str,
        description: str = "",
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None,
        reviewers: Optional[List[str]] = None,
        draft: bool = False,
        template_type: Optional[str] = None,
        template_vars: Optional[Dict[str, str]] = None,
        platform: Optional[str] = None,
        **kwargs
    ) -> PRResult:
        """创建 Pull Request"""
        try:
            # 验证仓库路径
            repo_path = validate_repo_path(repo_path)
            
            # 获取仓库信息
            repo_info = get_repo_info_from_path(repo_path)
            if not repo_info:
                raise ValidationError("无法获取仓库信息")
            
            # 获取提供者
            provider = self._get_provider(platform, repo_path)
            
            # 创建PR数据
            pr_data = PRData(
                title=title,
                description=description,
                source_branch=source_branch,
                target_branch=target_branch,
                labels=labels or [],
                assignees=assignees or [],
                reviewers=reviewers or [],
                draft=draft,
                template_type=template_type,
                template_vars=template_vars or {}
            )
            
            # 创建PR
            result = provider.create_pr(repo_info, pr_data)
            
            return result
            
        except Exception as e:
            logger.error(f"创建PR失败: {e}")
            return PRResult(
                success=False,
                error_message=str(e),
                platform=PlatformType(platform) if platform else None
            )
    
    def get_pull_request(
        self,
        repo_path: str,
        pr_number: int,
        platform: Optional[str] = None
    ) -> PRResult:
        """获取 Pull Request 信息"""
        try:
            repo_path = validate_repo_path(repo_path)
            repo_info = get_repo_info_from_path(repo_path)
            if not repo_info:
                raise ValidationError("无法获取仓库信息")
            
            provider = self._get_provider(platform, repo_path)
            return provider.get_pr(repo_info, pr_number)
            
        except Exception as e:
            logger.error(f"获取PR失败: {e}")
            return PRResult(
                success=False,
                error_message=str(e),
                platform=PlatformType(platform) if platform else None
            )
    
    def update_pull_request(
        self,
        repo_path: str,
        pr_number: int,
        platform: Optional[str] = None,
        **kwargs
    ) -> PRResult:
        """更新 Pull Request"""
        try:
            repo_path = validate_repo_path(repo_path)
            repo_info = get_repo_info_from_path(repo_path)
            if not repo_info:
                raise ValidationError("无法获取仓库信息")
            
            provider = self._get_provider(platform, repo_path)
            return provider.update_pr(repo_info, pr_number, **kwargs)
            
        except Exception as e:
            logger.error(f"更新PR失败: {e}")
            return PRResult(
                success=False,
                error_message=str(e),
                platform=PlatformType(platform) if platform else None
            )
    
    def list_pull_requests(
        self,
        repo_path: str,
        state: str = "open",
        per_page: int = 30,
        page: int = 1,
        platform: Optional[str] = None
    ) -> List[PRInfo]:
        """列出 Pull Requests"""
        try:
            repo_path = validate_repo_path(repo_path)
            repo_info = get_repo_info_from_path(repo_path)
            if not repo_info:
                raise ValidationError("无法获取仓库信息")
            
            provider = self._get_provider(platform, repo_path)
            return provider.list_prs(repo_info, state, per_page, page)
            
        except Exception as e:
            logger.error(f"列出PR失败: {e}")
            return []
    
    def health_check(self, platform: Optional[str] = None, repo_path: Optional[str] = None) -> bool:
        """健康检查"""
        try:
            provider = self._get_provider(platform, repo_path)
            return provider.health_check()
        except Exception as e:
            logger.error(f"健康检查失败: {e}")
            return False


# 全局管理器实例
_global_manager = PullRequestManager()


def set_global_config(config: PRConfig) -> None:
    """设置全局配置"""
    global _global_manager
    _global_manager = PullRequestManager(config)


def get_global_manager() -> PullRequestManager:
    """获取全局管理器"""
    return _global_manager