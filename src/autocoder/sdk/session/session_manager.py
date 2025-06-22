"""
Auto-Coder SDK 会话管理器

负责会话的创建、管理和存储。
"""

import os
from typing import List, Optional
from pathlib import Path

from ..models.options import AutoCodeOptions
from ..models.responses import SessionInfo
from ..exceptions import SessionNotFoundError
from .session import Session


class SessionManager:
    """简化的会话管理器"""
    
    def __init__(self, storage_path: str = None):
        """
        初始化会话管理器
        
        Args:
            storage_path: 存储路径，如果为None则使用默认路径
        """
        self.storage_path = storage_path or os.getcwd()
    
    def create_session(self, options: AutoCodeOptions = None) -> Session:
        """
        创建新会话
        
        Args:
            options: 配置选项
            
        Returns:
            Session: 新创建的会话
        """
        if options is None:
            options = AutoCodeOptions(cwd=self.storage_path)
        return Session(options=options)















