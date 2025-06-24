"""
Pull Request 模块自定义异常类
"""
from typing import Optional

class PRError(Exception):
    """Pull Request 操作基础异常"""
    def __init__(self, message: str, error_code: Optional[str] = None, platform: Optional[str] = None):
        self.message = message
        self.error_code = error_code
        self.platform = platform
        super().__init__(message)

class AuthenticationError(PRError):
    """认证失败异常"""
    pass

class RepositoryNotFoundError(PRError):
    """仓库不存在异常"""
    pass

class BranchNotFoundError(PRError):
    """分支不存在异常"""
    pass

class NetworkError(PRError):
    """网络错误异常"""
    pass

class RateLimitError(PRError):
    """API 限流异常"""
    def __init__(self, message: str, retry_after: int = 60, **kwargs):
        self.retry_after = retry_after
        super().__init__(message, **kwargs)

class ValidationError(PRError):
    """参数验证错误异常"""
    pass

class PlatformNotSupportedError(PRError):
    """平台不支持异常"""
    pass

class ConfigurationError(PRError):
    """配置错误异常"""
    pass