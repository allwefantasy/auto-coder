"""
Gitee API 提供者实现
"""
from typing import List
from .github_provider import GitHubProvider
from ..models import RepoInfo, PRData, PRResult, PRInfo


class GiteeProvider(GitHubProvider):
    """Gitee API 提供者（基于GitHub提供者）"""
    
    def _get_auth_header(self) -> str:
        """获取认证头"""
        # Gitee 使用 token 参数而不是 Authorization 头
        return ""
    
    def create_pr(self, repo_info: RepoInfo, pr_data: PRData) -> PRResult:
        """创建 Pull Request"""
        # 简化实现，实际应该调用Gitee API
        return super().create_pr(repo_info, pr_data)