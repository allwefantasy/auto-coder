"""
Pull Request 平台提供者模块
"""
from .github_provider import GitHubProvider
from .gitlab_provider import GitLabProvider
from .gitee_provider import GiteeProvider
from .gitcode_provider import GitCodeProvider

# 提供者映射
PROVIDERS = {
    'github': GitHubProvider,
    'gitlab': GitLabProvider,
    'gitee': GiteeProvider,
    'gitcode': GitCodeProvider
}

__all__ = [
    'GitHubProvider',
    'GitLabProvider', 
    'GiteeProvider',
    'GitCodeProvider',
    'PROVIDERS'
]