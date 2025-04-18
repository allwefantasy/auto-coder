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
        self._active_tokens: set[str] = set() # 存储当前正在运行的token
    
    def register_token(self, token: str) -> None:
        """注册一个 token，表示一个操作开始，但尚未请求取消"""
        with self._lock:            
            self._token_flags[token] = False            
            self._active_tokens.add(token)

    def get_active_tokens(self) -> set[str]:
        """获取当前正在运行的token"""
        with self._lock:
            return self._active_tokens.copy()
    
    def is_requested(self, token: Optional[str] = None) -> bool:
        """检查是否请求了特定token或全局的取消"""                  
        if token is not None and token in self._token_flags:
            return self._token_flags[token]
        
        if self._global_flag:
            return True
        return False 

    def set_active_tokens(self) -> None:
        """启用所有活跃的token"""        
        for token in self._active_tokens:
            self.set(token)            

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
    
    def reset_global(self) -> None:
        """重置全局取消标志"""
        with self._lock:
            self._global_flag = False 

    def reset_token(self, token: str) -> None:
        """重置特定token的取消标志"""
        with self._lock:
            if token in self._token_flags:
                del self._token_flags[token]
            if "tokens" in self._context and token in self._context["tokens"]:
                del self._context["tokens"][token]
            if token:    
                self._active_tokens.discard(token) # 从活跃集合中移除

    def reset(self, token: Optional[str] = None) -> None:
        """重置特定token或全局的取消标志"""
        with self._lock:
            if token is None:
                # 全局重置
                self._global_flag = False
                self._token_flags.clear()
                self._context.clear()
                self._active_tokens.clear() # 清空活跃集合
            else:
                # 特定token重置
                if token in self._token_flags:
                    del self._token_flags[token]
                if "tokens" in self._context and token in self._context["tokens"]:
                    del self._context["tokens"][token]
                if token:
                    self._active_tokens.discard(token) # 从活跃集合中移除
    
    def reset_active_tokens(self) -> None:
        """重置所有活跃的token"""
        with self._lock:
            for token in self._active_tokens.copy():
                self.reset_token(token)            
    
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
            if token:
                self.reset_token(token)
            else:
                self.reset_global()
            raise CancelRequestedException(token, context.get("message", "Operation was cancelled"))

global_cancel = GlobalCancel()