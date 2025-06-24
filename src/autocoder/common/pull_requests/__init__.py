"""
Pull Request 统一管理模块

统一的 Pull Request 创建和管理模块，支持 GitHub、GitLab、Gitee、GitCode 四大代码托管平台的 PR 操作。
"""
from typing import Optional, List, Dict, Any
from loguru import logger

from .models import (
    PRConfig, PRResult, PRInfo, PRData, RepoInfo, PlatformType, 
    DEFAULT_TEMPLATES
)
from .manager import PullRequestManager, get_global_manager, set_global_config
from .exceptions import (
    PRError, AuthenticationError, RepositoryNotFoundError, 
    BranchNotFoundError, NetworkError, RateLimitError, 
    ValidationError, PlatformNotSupportedError, ConfigurationError
)
from .config import get_config
from .utils import (
    parse_git_url, detect_platform_from_repo, get_repo_info_from_path,
    get_current_branch, branch_exists, is_git_repo, get_default_remote_branch,
    ensure_branch_exists_remotely, is_main_branch, create_and_checkout_branch,
    generate_auto_branch_name
)


def create_pull_request(
    repo_path: str,
    title: str,
    source_branch: Optional[str] = None,
    target_branch: Optional[str] = None,
    description: str = "",
    labels: Optional[List[str]] = None,
    assignees: Optional[List[str]] = None,
    reviewers: Optional[List[str]] = None,
    draft: bool = False,
    template_type: Optional[str] = None,
    template_vars: Optional[Dict[str, str]] = None,
    platform: Optional[str] = None,
    token: Optional[str] = None,
    **kwargs
) -> PRResult:
    """
    创建 Pull Request（主要接口函数）
    
    Args:
        repo_path: 仓库路径
        title: PR标题
        source_branch: 源分支（可选，默认为当前分支）
        target_branch: 目标分支（可选，默认为远程默认分支或main）
        description: PR描述
        labels: 标签列表
        assignees: 负责人列表
        reviewers: 审查者列表
        draft: 是否为草稿PR
        template_type: 模板类型
        template_vars: 模板变量
        platform: 平台类型（可选，会自动检测）
        token: 访问令牌（可选）
        **kwargs: 其他配置参数
    
    Returns:
        PR创建结果
    """
    # 处理可选的分支参数
    if source_branch is None:
        source_branch = get_current_branch(repo_path)
        if not source_branch:
            raise ValidationError("无法获取当前分支，请指定source_branch参数")
    
    # 从当前分支，自动创建新分支
    auto_branch_name = generate_auto_branch_name()
    logger.info(f"检测到当前分支 '{source_branch}' 为主分支，自动创建新分支: {auto_branch_name}")
    
    if not create_and_checkout_branch(repo_path, auto_branch_name):
        raise ValidationError(f"无法从主分支 '{source_branch}' 创建新分支 '{auto_branch_name}'")
    
    source_branch = auto_branch_name
    logger.info(f"已切换到新分支: {source_branch}")
    
    if target_branch is None:
        target_branch = get_default_remote_branch(repo_path)
        if not target_branch:
            target_branch = "main"  # 默认值
    
    # 验证仓库是否为Git仓库
    if not is_git_repo(repo_path):
        raise ValidationError(f"路径 {repo_path} 不是一个有效的Git仓库")
    
    # 检查源分支和目标分支是否相同
    if source_branch == target_branch:
        raise ValidationError(f"源分支和目标分支不能相同: {source_branch}")
    
    # 确保源分支存在于远程仓库，如果不存在则自动推送
    if not ensure_branch_exists_remotely(repo_path, source_branch):
        raise BranchNotFoundError(
            f"源分支 '{source_branch}' 在本地不存在或推送失败。"
            f"请检查分支是否存在或网络连接是否正常。"
        )
    
    # 检查目标分支是否存在于远程仓库
    if not branch_exists(repo_path, target_branch, remote=True):
        raise BranchNotFoundError(
            f"目标分支 '{target_branch}' 在远程仓库中不存在。"
        )
    
    # 如果提供了token，创建临时配置
    manager = get_global_manager()
    
    if token:
        # 自动检测平台或使用指定平台
        if not platform:
            detected_platform = detect_platform_from_repo(repo_path)
            if detected_platform:
                platform = detected_platform.value
            else:
                raise ValidationError("无法检测平台类型，请指定platform参数")
        
        # 创建临时配置
        temp_config = PRConfig(platform=PlatformType(platform), token=token)
        temp_manager = PullRequestManager(temp_config)
        
        return temp_manager.create_pull_request(
            repo_path=repo_path,
            source_branch=source_branch,
            target_branch=target_branch,
            title=title,
            description=description,
            labels=labels,
            assignees=assignees,
            reviewers=reviewers,
            draft=draft,
            template_type=template_type,
            template_vars=template_vars,
            platform=platform
        )
    else:
        # 使用全局管理器
        return manager.create_pull_request(
            repo_path=repo_path,
            source_branch=source_branch,
            target_branch=target_branch,
            title=title,
            description=description,
            labels=labels,
            assignees=assignees,
            reviewers=reviewers,
            draft=draft,
            template_type=template_type,
            template_vars=template_vars,
            platform=platform
        )


def get_pull_request(
    repo_path: str,
    pr_number: int,
    platform: Optional[str] = None,
    token: Optional[str] = None,
    **kwargs
) -> PRResult:
    """获取 Pull Request 信息"""
    manager = get_global_manager()
    
    if token:
        if not platform:
            detected_platform = detect_platform_from_repo(repo_path)
            if detected_platform:
                platform = detected_platform.value
            else:
                raise ValidationError("无法检测平台类型，请指定platform参数")
        
        config_data = {"token": token}
        config_data.update(kwargs)
        temp_config = PRConfig(platform=platform, **config_data)
        temp_manager = PullRequestManager(temp_config)
        
        return temp_manager.get_pull_request(repo_path, pr_number, platform)
    else:
        return manager.get_pull_request(repo_path, pr_number, platform)


def list_pull_requests(
    repo_path: str,
    state: str = "open",
    per_page: int = 30,
    page: int = 1,
    platform: Optional[str] = None,
    token: Optional[str] = None,
    **kwargs
) -> List[PRInfo]:
    """列出 Pull Requests"""
    manager = get_global_manager()
    
    if token:
        if not platform:
            detected_platform = detect_platform_from_repo(repo_path)
            if detected_platform:
                platform = detected_platform.value
            else:
                raise ValidationError("无法检测平台类型，请指定platform参数")
        
        config_data = {"token": token}
        config_data.update(kwargs)
        temp_config = PRConfig(platform=platform, **config_data)
        temp_manager = PullRequestManager(temp_config)
        
        return temp_manager.list_pull_requests(repo_path, state, per_page, page, platform)
    else:
        return manager.list_pull_requests(repo_path, state, per_page, page, platform)


# 导出所有公共接口
__all__ = [
    # 主要函数
    'create_pull_request',
    'get_pull_request', 
    'list_pull_requests',
    
    # 类和模型
    'PullRequestManager',
    'PRConfig',
    'PRResult',
    'PRInfo',
    'PRData',
    'RepoInfo',
    'PlatformType',
    
    # 异常
    'PRError',
    'AuthenticationError',
    'RepositoryNotFoundError',
    'BranchNotFoundError',
    'NetworkError',
    'RateLimitError',
    'ValidationError',
    'PlatformNotSupportedError',
    'ConfigurationError',
    
    # 工具函数
    'parse_git_url',
    'detect_platform_from_repo',
    'get_repo_info_from_path',
    'get_current_branch',
    'branch_exists',
    'is_git_repo',
    
    # 配置函数
    'get_config',
    'set_global_config',
    'get_global_manager',
    
    # 模板
    'DEFAULT_TEMPLATES'
]