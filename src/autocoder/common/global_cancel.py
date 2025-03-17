import threading
from typing import Dict, Optional, Any

class CancelRequestedException(Exception):
    """当取消请求被触发时抛出的异常"""
    def __init__(self, token: Optional[str] = None, message: str = "Operation was cancelled"):
        self.token = token
        self.message = message
        super().__init__(self.message)

class GlobalCancel:
    def __init__(self):
        self._global_flag = False
        self._token_flags: Dict[str, bool] = {}
        self._lock = threading.Lock()
        self._context: Dict[str, Any] = {}  # 存储与取消相关的上下文信息
    
    @property
    def requested(self) -> bool:
        """检查是否请求了全局取消（向后兼容）"""
        with self._lock:
            return self._global_flag
    
    def is_requested(self, token: Optional[str] = None) -> bool:
        """检查是否请求了特定token或全局的取消"""
        with self._lock:
            # 全局标志总是优先
            if self._global_flag:
                return True
            # 如果提供了token，检查该token的标志
            if token is not None and token in self._token_flags:
                return self._token_flags[token]
            return False
    
    def set(self, token: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> None:
        """设置特定token或全局的取消标志"""
        with self._lock:
            if token is None:
                self._global_flag = True
            else:
                self._token_flags[token] = True
            
            # 存储上下文
            if context:
                if token is None:
                    self._context.update(context)
                else:
                    if "tokens" not in self._context:
                        self._context["tokens"] = {}
                    self._context["tokens"][token] = context
    
    def reset(self, token: Optional[str] = None) -> None:
        """重置特定token或全局的取消标志"""
        with self._lock:
            if token is None:
                # 全局重置
                self._global_flag = False
                self._token_flags.clear()
                self._context.clear()
            else:
                # 特定token重置
                if token in self._token_flags:
                    del self._token_flags[token]
                if "tokens" in self._context and token in self._context["tokens"]:
                    del self._context["tokens"][token]
    
    def get_context(self, token: Optional[str] = None) -> Dict[str, Any]:
        """获取与取消相关的上下文信息"""
        with self._lock:
            if token is None:
                return self._context.copy()
            if "tokens" in self._context and token in self._context["tokens"]:
                return self._context["tokens"][token].copy()
            return {}
    
    def check_and_raise(self, token: Optional[str] = None) -> None:
        """检查是否请求了取消，如果是则抛出异常"""
        if self.is_requested(token):
            context = self.get_context(token)
            raise CancelRequestedException(token, context.get("message", "Operation was cancelled"))

global_cancel = GlobalCancel()