"""
PersistConversationManager 异常类定义
"""


class ConversationManagerError(Exception):
    """对话管理器基础异常类"""
    
    def __init__(self, message="对话管理器发生错误", error_code="GENERAL_ERROR"):
        super().__init__(message)
        self.error_code = error_code


class ConversationNotFoundError(ConversationManagerError):
    """对话不存在异常"""
    
    def __init__(self, conversation_id):
        # 检查是否是类似ID的字符串（不包含中文等）
        if (isinstance(conversation_id, str) and len(conversation_id) > 0 and 
            not any(ord(c) > 127 or c.isspace() for c in conversation_id)):
            message = f"对话未找到: {conversation_id}"
        else:
            message = conversation_id  # 自定义消息
        super().__init__(message, error_code="CONVERSATION_NOT_FOUND")


class MessageNotFoundError(ConversationManagerError):
    """消息不存在异常"""
    
    def __init__(self, message_id):
        # 检查是否是类似ID的字符串（不包含中文等）
        if (isinstance(message_id, str) and len(message_id) > 0 and 
            not any(ord(c) > 127 or c.isspace() for c in message_id)):
            message = f"消息未找到: {message_id}"
        else:
            message = message_id  # 自定义消息
        super().__init__(message, error_code="MESSAGE_NOT_FOUND")


class ConcurrencyError(ConversationManagerError):
    """并发访问异常"""
    
    def __init__(self, message="并发访问冲突"):
        super().__init__(message, error_code="CONCURRENCY_ERROR")


class DataIntegrityError(ConversationManagerError):
    """数据完整性异常"""
    
    def __init__(self, message="数据完整性检查失败"):
        super().__init__(message, error_code="DATA_INTEGRITY_ERROR")


class LockTimeoutError(ConversationManagerError):
    """锁超时异常"""
    
    def __init__(self, message="锁获取超时"):
        super().__init__(message, error_code="LOCK_TIMEOUT_ERROR")


class BackupError(ConversationManagerError):
    """备份操作异常"""
    
    def __init__(self, message="备份操作失败"):
        super().__init__(message, error_code="BACKUP_ERROR")


class RestoreError(ConversationManagerError):
    """恢复操作异常"""
    
    def __init__(self, message="恢复操作失败"):
        super().__init__(message, error_code="RESTORE_ERROR") 