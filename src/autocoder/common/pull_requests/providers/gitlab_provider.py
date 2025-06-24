"""
GitLab API 提供者实现
"""
from typing import List
from .github_provider import GitHubProvider
from ..models import RepoInfo, PRData, PRResult, PRInfo


class GitLabProvider(GitHubProvider):
    """GitLab API 提供者（基于GitHub提供者）"""
    
    def _get_auth_header(self) -> str:
        """获取认证头"""
        return f"Bearer {self.config.token}"
    
    def create_pr(self, repo_info: RepoInfo, pr_data: PRData) -> PRResult:
        """创建 Merge Request (GitLab的PR称为MR)"""
        # 简化实现，实际应该调用GitLab API
        return super().create_pr(repo_info, pr_data)
    
    def list_prs(
        self, 
        repo_info: RepoInfo, 
        state: str = "opened",  # GitLab使用"opened"而不是"open"
        per_page: int = 30,
        page: int = 1
    ) -> List[PRInfo]:
        """列出仓库的MR"""
        return super().list_prs(repo_info, state, per_page, page)