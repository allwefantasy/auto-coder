"""
GitCode API 提供者实现
"""
from typing import List
from .github_provider import GitHubProvider
from ..models import RepoInfo, PRData, PRResult, PRInfo


class GitCodeProvider(GitHubProvider):
    """GitCode API 提供者（基于GitHub提供者）"""
    
    def _get_auth_header(self) -> str:
        """获取认证头"""
        return f"Bearer {self.config.token}"
    
    def create_pr(self, repo_info: RepoInfo, pr_data: PRData) -> PRResult:
        """创建 Merge Request"""
        # 简化实现，实际应该调用GitCode API
        return super().create_pr(repo_info, pr_data)