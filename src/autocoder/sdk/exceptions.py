
"""
Auto-Coder SDK 异常定义

定义所有自定义异常类，提供错误码和异常的映射关系，统一异常处理策略。
"""

class AutoCoderSDKError(Exception):
    """SDK基础异常类"""
    
    def __init__(self, message: str, error_code: str = None):
        super().__init__(message)
        self.message = message
        self.error_code = error_code or "SDK_ERROR"
    
    def __str__(self):
        return f"[{self.error_code}] {self.message}"


class SessionNotFoundError(AutoCoderSDKError):
    """会话未找到异常"""
    
    def __init__(self, session_id: str):
        super().__init__(
            f"Session '{session_id}' not found",
            error_code="SESSION_NOT_FOUND"
        )
        self.session_id = session_id


class InvalidOptionsError(AutoCoderSDKError):
    """无效选项异常"""
    
    def __init__(self, message: str):
        super().__init__(
            f"Invalid options: {message}",
            error_code="INVALID_OPTIONS"
        )


class BridgeError(AutoCoderSDKError):
    """桥接层异常"""
    
    def __init__(self, message: str, original_error: Exception = None):
        super().__init__(
            f"Bridge error: {message}",
            error_code="BRIDGE_ERROR"
        )
        self.original_error = original_error


class CLIError(AutoCoderSDKError):
    """CLI异常"""
    
    def __init__(self, message: str, exit_code: int = 1):
        super().__init__(
            f"CLI error: {message}",
            error_code="CLI_ERROR"
        )
        self.exit_code = exit_code


class ValidationError(AutoCoderSDKError):
    """验证错误异常"""
    
    def __init__(self, field: str, message: str):
        super().__init__(
            f"Validation error for '{field}': {message}",
            error_code="VALIDATION_ERROR"
        )
        self.field = field

