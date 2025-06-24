"""
GitHub API 提供者实现
"""
from typing import List, Dict, Any
from loguru import logger

from ..base_provider import BasePlatformProvider
from ..models import RepoInfo, PRData, PRResult, PRInfo
from ..utils import build_pr_url


class GitHubProvider(BasePlatformProvider):
    """GitHub API 提供者"""
    
    def _get_auth_header(self) -> str:
        """获取认证头"""
        return f"token {self.config.token}"
    
    def create_pr(self, repo_info: RepoInfo, pr_data: PRData) -> PRResult:
        """创建 Pull Request"""
        self._validate_repo_info(repo_info)
        self._validate_pr_data(pr_data)
        
        url = f"{self.config.base_url}/repos/{repo_info.full_name}/pulls"
        
        payload = {
            "title": pr_data.title,
            "body": pr_data.description,
            "head": pr_data.source_branch,
            "base": pr_data.target_branch,
            "draft": pr_data.draft or self.config.draft,
            "maintainer_can_modify": self.config.maintainer_can_modify
        }
        
        try:
            response = self._make_request('POST', url, data=payload)
            data = response.json()
            
            pr_url = build_pr_url(self.config.platform, repo_info, data['number'])
            
            result = PRResult(
                success=True,
                pr_number=data['number'],
                pr_url=pr_url,
                pr_id=str(data['id']),
                platform=self.config.platform,
                raw_response=data
            )
            
            logger.info(f"GitHub PR 创建成功: {pr_url}")
            return result
            
        except Exception as e:
            logger.error(f"创建 GitHub PR 失败: {e}")
            return PRResult(
                success=False,
                error_message=str(e),
                platform=self.config.platform
            )
    
    def get_pr(self, repo_info: RepoInfo, pr_number: int) -> PRResult:
        """获取 PR 信息"""
        url = f"{self.config.base_url}/repos/{repo_info.full_name}/pulls/{pr_number}"
        
        try:
            response = self._make_request('GET', url)
            data = response.json()
            
            pr_info = PRInfo(
                number=data['number'],
                title=data['title'],
                description=data.get('body', ''),
                state=data['state'],
                source_branch=data['head']['ref'],
                target_branch=data['base']['ref'],
                author=data['user']['login'],
                created_at=data['created_at'],
                updated_at=data['updated_at'],
                merged_at=data.get('merged_at'),
                pr_url=data['html_url'],
                labels=[label['name'] for label in data.get('labels', [])],
                assignees=[assignee['login'] for assignee in data.get('assignees', [])],
                mergeable=data.get('mergeable'),
                draft=data.get('draft', False),
                raw_data=data
            )
            
            return PRResult(
                success=True,
                pr_number=pr_info.number,
                pr_url=pr_info.pr_url,
                platform=self.config.platform,
                raw_response=data
            )
            
        except Exception as e:
            logger.error(f"获取 GitHub PR 失败: {e}")
            return PRResult(
                success=False,
                error_message=str(e),
                platform=self.config.platform
            )
    
    def update_pr(self, repo_info: RepoInfo, pr_number: int, **kwargs) -> PRResult:
        """更新 PR"""
        url = f"{self.config.base_url}/repos/{repo_info.full_name}/pulls/{pr_number}"
        
        payload = {}
        if 'title' in kwargs:
            payload['title'] = kwargs['title']
        if 'description' in kwargs:
            payload['body'] = kwargs['description']
        if 'state' in kwargs:
            payload['state'] = kwargs['state']
        
        try:
            response = self._make_request('PATCH', url, data=payload)
            data = response.json()
            
            return PRResult(
                success=True,
                pr_number=data['number'],
                pr_url=data['html_url'],
                platform=self.config.platform,
                raw_response=data
            )
            
        except Exception as e:
            logger.error(f"更新 GitHub PR 失败: {e}")
            return PRResult(
                success=False,
                error_message=str(e),
                platform=self.config.platform
            )
    
    def close_pr(self, repo_info: RepoInfo, pr_number: int) -> PRResult:
        """关闭 PR"""
        return self.update_pr(repo_info, pr_number, state='closed')
    
    def merge_pr(self, repo_info: RepoInfo, pr_number: int, **kwargs) -> PRResult:
        """合并 PR"""
        url = f"{self.config.base_url}/repos/{repo_info.full_name}/pulls/{pr_number}/merge"
        
        payload = {
            'commit_title': kwargs.get('commit_title', ''),
            'commit_message': kwargs.get('commit_message', ''),
            'merge_method': kwargs.get('merge_method', 'merge')
        }
        
        try:
            response = self._make_request('PUT', url, data=payload)
            data = response.json()
            
            return PRResult(
                success=True,
                pr_number=pr_number,
                platform=self.config.platform,
                raw_response=data
            )
            
        except Exception as e:
            logger.error(f"合并 GitHub PR 失败: {e}")
            return PRResult(
                success=False,
                error_message=str(e),
                platform=self.config.platform
            )
    
    def list_prs(
        self, 
        repo_info: RepoInfo, 
        state: str = "open",
        per_page: int = 30,
        page: int = 1
    ) -> List[PRInfo]:
        """列出仓库的PR"""
        url = f"{self.config.base_url}/repos/{repo_info.full_name}/pulls"
        params = {
            'state': state,
            'per_page': str(per_page),
            'page': str(page)
        }
        
        try:
            response = self._make_request('GET', url, params=params)
            data = response.json()
            
            prs = []
            for pr_data in data:
                pr_info = PRInfo(
                    number=pr_data['number'],
                    title=pr_data['title'],
                    description=pr_data.get('body', ''),
                    state=pr_data['state'],
                    source_branch=pr_data['head']['ref'],
                    target_branch=pr_data['base']['ref'],
                    author=pr_data['user']['login'],
                    created_at=pr_data['created_at'],
                    updated_at=pr_data['updated_at'],
                    merged_at=pr_data.get('merged_at'),
                    pr_url=pr_data['html_url'],
                    labels=[label['name'] for label in pr_data.get('labels', [])],
                    assignees=[assignee['login'] for assignee in pr_data.get('assignees', [])],
                    mergeable=pr_data.get('mergeable'),
                    draft=pr_data.get('draft', False),
                    raw_data=pr_data
                )
                prs.append(pr_info)
            
            return prs
            
        except Exception as e:
            logger.error(f"列出 GitHub PR 失败: {e}")
            return []