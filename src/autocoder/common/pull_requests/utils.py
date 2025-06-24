"""
Pull Request 模块工具函数
"""
import re
import os
import subprocess
from typing import Optional, Tuple
from urllib.parse import urlparse
from pathlib import Path
from loguru import logger

from .models import PlatformType, RepoInfo
from .exceptions import ValidationError


def parse_git_url(url: str) -> Tuple[Optional[PlatformType], Optional[str], Optional[str]]:
    """
    解析Git URL，提取平台类型、所有者和仓库名
    
    Returns:
        Tuple[平台类型, 所有者, 仓库名]
    """
    if not url:
        return None, None, None
    
    platform_domains = {
        'github.com': PlatformType.GITHUB,
        'gitlab.com': PlatformType.GITLAB,
        'gitee.com': PlatformType.GITEE,
        'gitcode.net': PlatformType.GITCODE
    }
    
    # SSH URL 格式: git@domain:owner/repo.git
    ssh_pattern = r'^git@([^:]+):([^/]+)/([^/]+?)(?:\.git)?/?$'
    ssh_match = re.match(ssh_pattern, url)
    
    if ssh_match:
        domain, owner, repo = ssh_match.groups()
        platform = platform_domains.get(domain)
        return platform, owner, repo
    
    # HTTPS URL 格式: https://domain/owner/repo.git
    try:
        parsed = urlparse(url)
        domain = parsed.netloc
        platform = platform_domains.get(domain)
        
        if not platform:
            return None, None, None
        
        path_parts = [p for p in parsed.path.split('/') if p]
        if len(path_parts) >= 2:
            owner = path_parts[0]
            repo = path_parts[1]
            if repo.endswith('.git'):
                repo = repo[:-4]
            return platform, owner, repo
    
    except Exception as e:
        logger.error(f"解析Git URL失败: {e}")
    
    return None, None, None


def get_repo_remote_url(repo_path: str, remote_name: str = 'origin') -> Optional[str]:
    """获取仓库的远程URL"""
    try:
        result = subprocess.run(
            ['git', 'remote', 'get-url', remote_name],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def detect_platform_from_repo(repo_path: str) -> Optional[PlatformType]:
    """从仓库路径自动检测平台类型"""
    remote_url = get_repo_remote_url(repo_path)
    if not remote_url:
        return None
    
    platform, _, _ = parse_git_url(remote_url)
    return platform


def get_repo_info_from_path(repo_path: str) -> Optional[RepoInfo]:
    """从仓库路径获取仓库信息"""
    remote_url = get_repo_remote_url(repo_path)
    if not remote_url:
        return None
    
    platform, owner, name = parse_git_url(remote_url)
    if not all([platform, owner, name]):
        return None
    
    return RepoInfo(
        platform=platform,  # type: ignore
        owner=owner,  # type: ignore
        name=name  # type: ignore
    )


def get_current_branch(repo_path: str) -> Optional[str]:
    """获取当前分支名"""
    try:
        result = subprocess.run(
            ['git', 'branch', '--show-current'],
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return None


def branch_exists(repo_path: str, branch_name: str, remote: bool = False) -> bool:
    """检查分支是否存在"""
    try:
        if remote:
            result = subprocess.run(
                ['git', 'ls-remote', '--heads', 'origin', branch_name],
                cwd=repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return bool(result.stdout.strip())
        else:
            result = subprocess.run(
                ['git', 'show-ref', '--verify', '--quiet', f'refs/heads/{branch_name}'],
                cwd=repo_path,
                capture_output=True
            )
            return result.returncode == 0
    except subprocess.CalledProcessError:
        return False


def is_git_repo(path: str) -> bool:
    """检查路径是否为Git仓库"""
    git_dir = Path(path) / '.git'
    return git_dir.exists() or git_dir.is_file()


def validate_repo_path(repo_path: str) -> str:
    """验证并规范化仓库路径"""
    if not repo_path:
        raise ValidationError("仓库路径不能为空")
    
    path = Path(repo_path).resolve()
    
    if not path.exists():
        raise ValidationError(f"仓库路径不存在: {path}")
    
    if not path.is_dir():
        raise ValidationError(f"仓库路径不是目录: {path}")
    
    if not is_git_repo(str(path)):
        raise ValidationError(f"路径不是Git仓库: {path}")
    
    return str(path)


def build_pr_url(platform: PlatformType, repo_info: RepoInfo, pr_number: int) -> str:
    """构建PR的Web URL"""
    base_urls = {
        PlatformType.GITHUB: "https://github.com",
        PlatformType.GITLAB: "https://gitlab.com",
        PlatformType.GITEE: "https://gitee.com",
        PlatformType.GITCODE: "https://gitcode.net"
    }
    
    base_url = base_urls.get(platform)
    if not base_url:
        return ""
    
    if platform == PlatformType.GITLAB or platform == PlatformType.GITCODE:
        return f"{base_url}/{repo_info.full_name}/-/merge_requests/{pr_number}"
    else:
        return f"{base_url}/{repo_info.full_name}/pull/{pr_number}"