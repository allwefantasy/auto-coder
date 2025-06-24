"""
Pull Request 平台提供者基类
"""
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any, List
import requests
import time
from loguru import logger

from .models import RepoInfo, PRData, PRResult, PRInfo, PRConfig
from .exceptions import (
    PRError, NetworkError, AuthenticationError, RateLimitError,
    RepositoryNotFoundError, ValidationError
)


class BasePlatformProvider(ABC):
    """平台提供者基类，定义统一接口"""
    
    def __init__(self, config: PRConfig):
        self.config = config
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """创建HTTP会话"""
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'AutoCoder-PR/1.0',
            'Authorization': self._get_auth_header(),
            'Accept': 'application/json',
            'Content-Type': 'application/json'
        })
        session.verify = self.config.verify_ssl
        return session
    
    @abstractmethod
    def _get_auth_header(self) -> str:
        """获取认证头"""
        pass
    
    def _make_request(
        self, 
        method: str, 
        url: str, 
        data: Optional[Dict[str, Any]] = None,
        params: Optional[Dict[str, str]] = None,
        retry_count: Optional[int] = None
    ) -> requests.Response:
        """发送HTTP请求，包含重试逻辑"""
        
        if retry_count is None:
            retry_count = self.config.retry_count
        
        last_exception = None
        
        for attempt in range(retry_count + 1):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=data,
                    params=params,
                    timeout=self.config.timeout
                )
                
                if response.status_code == 401:
                    raise AuthenticationError("认证失败，请检查token是否正确")
                elif response.status_code == 404:
                    raise RepositoryNotFoundError("仓库或资源不存在")
                elif response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    raise RateLimitError(f"API限流，请等待{retry_after}秒后重试", retry_after=retry_after)
                elif response.status_code == 422:
                    # 422 通常是验证错误，尝试解析响应内容获取详细错误信息
                    try:
                        error_data = response.json()
                        if 'errors' in error_data:
                            errors = error_data['errors']
                            error_msgs = []
                            for error in errors:
                                if isinstance(error, dict):
                                    field = error.get('field', '')
                                    code = error.get('code', '')
                                    message = error.get('message', str(error))
                                    if field and code:
                                        error_msgs.append(f"{field}: {message} (code: {code})")
                                    else:
                                        error_msgs.append(message)
                                else:
                                    error_msgs.append(str(error))
                            raise ValidationError(f"请求验证失败: {'; '.join(error_msgs)}")
                        elif 'message' in error_data:
                            raise ValidationError(f"请求验证失败: {error_data['message']}")
                        else:
                            raise ValidationError(f"请求验证失败: {response.text}")
                    except (ValueError, KeyError):
                        raise ValidationError(f"请求验证失败: HTTP 422 - {response.text}")
                elif response.status_code >= 400:
                    try:
                        error_data = response.json()
                        if 'message' in error_data:
                            raise PRError(f"API请求失败: HTTP {response.status_code} - {error_data['message']}")
                        else:
                            raise PRError(f"API请求失败: HTTP {response.status_code} - {response.text}")
                    except (ValueError, KeyError):
                        raise PRError(f"API请求失败: HTTP {response.status_code} - {response.text}")
                
                return response
                
            except (requests.exceptions.RequestException, ConnectionError) as e:
                last_exception = NetworkError(f"网络请求失败: {str(e)}")
                
                if attempt < retry_count:
                    delay = 2 ** attempt
                    logger.warning(f"请求失败，{delay}秒后重试")
                    time.sleep(delay)
                    continue
                
            except RateLimitError as e:
                if attempt < retry_count:
                    logger.warning(f"遇到限流，等待{e.retry_after}秒后重试")
                    time.sleep(e.retry_after)
                    continue
                raise
        
        if last_exception:
            raise last_exception
        
        raise PRError("请求失败，已达到最大重试次数")
    
    def _validate_pr_data(self, pr_data: PRData) -> None:
        """验证PR数据"""
        if not pr_data.title.strip():
            raise ValidationError("PR标题不能为空")
        if not pr_data.source_branch.strip():
            raise ValidationError("源分支不能为空")
        if not pr_data.target_branch.strip():
            raise ValidationError("目标分支不能为空")
        if pr_data.source_branch == pr_data.target_branch:
            raise ValidationError("源分支和目标分支不能相同")
    
    def _validate_repo_info(self, repo_info: RepoInfo) -> None:
        """验证仓库信息"""
        if not repo_info.owner.strip():
            raise ValidationError("仓库所有者不能为空")
        if not repo_info.name.strip():
            raise ValidationError("仓库名称不能为空")
    
    @abstractmethod
    def create_pr(self, repo_info: RepoInfo, pr_data: PRData) -> PRResult:
        """创建 Pull Request"""
        pass
    
    @abstractmethod
    def get_pr(self, repo_info: RepoInfo, pr_number: int) -> PRResult:
        """获取 PR 信息"""
        pass
    
    @abstractmethod
    def update_pr(self, repo_info: RepoInfo, pr_number: int, **kwargs) -> PRResult:
        """更新 PR"""
        pass
    
    @abstractmethod
    def close_pr(self, repo_info: RepoInfo, pr_number: int) -> PRResult:
        """关闭 PR"""
        pass
    
    @abstractmethod
    def merge_pr(self, repo_info: RepoInfo, pr_number: int, **kwargs) -> PRResult:
        """合并 PR"""
        pass
    
    @abstractmethod
    def list_prs(
        self, 
        repo_info: RepoInfo, 
        state: str = "open",
        per_page: int = 30,
        page: int = 1
    ) -> List[PRInfo]:
        """列出仓库的PR"""
        pass
    
    def health_check(self) -> bool:
        """检查连接和认证状态"""
        try:
            response = self._make_request('GET', f"{self.config.base_url}/user")
            return response.status_code == 200
        except Exception:
            return False