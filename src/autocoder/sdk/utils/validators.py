




"""
Auto-Coder SDK 验证工具

提供各种数据验证功能。
"""

import re
import uuid
from typing import Any, List, Dict
from pathlib import Path

from ..models.options import AutoCodeOptions
from ..exceptions import ValidationError


def validate_session_id(session_id: str) -> bool:
    """
    验证会话ID格式
    
    Args:
        session_id: 会话ID
        
    Returns:
        bool: 是否有效
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    if not session_id:
        raise ValidationError("session_id", "cannot be empty")
    
    # 检查是否为有效的UUID格式
    try:
        uuid.UUID(session_id)
        return True
    except ValueError:
        pass
    
    # 检查是否为有效的自定义格式（字母数字和连字符）
    if re.match(r'^[a-zA-Z0-9\-_]+$', session_id):
        return True
    
    raise ValidationError(
        "session_id", 
        "must be a valid UUID or alphanumeric string with hyphens/underscores"
    )


def validate_options(options: AutoCodeOptions) -> bool:
    """
    验证AutoCodeOptions对象
    
    Args:
        options: 选项对象
        
    Returns:
        bool: 是否有效
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    if not isinstance(options, AutoCodeOptions):
        raise ValidationError("options", "must be an AutoCodeOptions instance")
    
    # AutoCodeOptions内部已经有验证，这里调用即可
    options.validate()
    return True


def validate_file_path(file_path: str, must_exist: bool = False) -> bool:
    """
    验证文件路径
    
    Args:
        file_path: 文件路径
        must_exist: 是否必须存在
        
    Returns:
        bool: 是否有效
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    if not file_path:
        raise ValidationError("file_path", "cannot be empty")
    
    try:
        path = Path(file_path)
        
        if must_exist and not path.exists():
            raise ValidationError("file_path", f"file does not exist: {file_path}")
        
        # 检查路径是否合法（不包含非法字符）
        if any(char in str(path) for char in ['<', '>', ':', '"', '|', '?', '*']):
            raise ValidationError("file_path", f"contains invalid characters: {file_path}")
        
        return True
    except OSError as e:
        raise ValidationError("file_path", f"invalid path: {str(e)}")


def validate_directory_path(dir_path: str, must_exist: bool = False, create_if_missing: bool = False) -> bool:
    """
    验证目录路径
    
    Args:
        dir_path: 目录路径
        must_exist: 是否必须存在
        create_if_missing: 如果不存在是否创建
        
    Returns:
        bool: 是否有效
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    if not dir_path:
        raise ValidationError("dir_path", "cannot be empty")
    
    try:
        path = Path(dir_path)
        
        if not path.exists():
            if must_exist and not create_if_missing:
                raise ValidationError("dir_path", f"directory does not exist: {dir_path}")
            elif create_if_missing:
                path.mkdir(parents=True, exist_ok=True)
        elif path.exists() and not path.is_dir():
            raise ValidationError("dir_path", f"path exists but is not a directory: {dir_path}")
        
        return True
    except OSError as e:
        raise ValidationError("dir_path", f"invalid directory path: {str(e)}")


def validate_prompt(prompt: str, max_length: int = 10000) -> bool:
    """
    验证提示内容
    
    Args:
        prompt: 提示内容
        max_length: 最大长度
        
    Returns:
        bool: 是否有效
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    if not prompt:
        raise ValidationError("prompt", "cannot be empty")
    
    if not isinstance(prompt, str):
        raise ValidationError("prompt", "must be a string")
    
    if len(prompt.strip()) == 0:
        raise ValidationError("prompt", "cannot be only whitespace")
    
    if len(prompt) > max_length:
        raise ValidationError("prompt", f"exceeds maximum length of {max_length} characters")
    
    return True


def validate_output_format(output_format: str) -> bool:
    """
    验证输出格式
    
    Args:
        output_format: 输出格式
        
    Returns:
        bool: 是否有效
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    from ..constants import OUTPUT_FORMATS
    
    if not output_format:
        raise ValidationError("output_format", "cannot be empty")
    
    if output_format not in OUTPUT_FORMATS:
        raise ValidationError(
            "output_format",
            f"must be one of: {', '.join(OUTPUT_FORMATS.keys())}"
        )
    
    return True


def validate_permission_mode(permission_mode: str) -> bool:
    """
    验证权限模式
    
    Args:
        permission_mode: 权限模式
        
    Returns:
        bool: 是否有效
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    from ..constants import PERMISSION_MODES
    
    if not permission_mode:
        raise ValidationError("permission_mode", "cannot be empty")
    
    if permission_mode not in PERMISSION_MODES:
        raise ValidationError(
            "permission_mode",
            f"must be one of: {', '.join(PERMISSION_MODES.keys())}"
        )
    
    return True


def validate_allowed_tools(allowed_tools: List[str]) -> bool:
    """
    验证允许的工具列表
    
    Args:
        allowed_tools: 工具列表
        
    Returns:
        bool: 是否有效
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    from ..constants import ALLOWED_TOOLS
    
    if not isinstance(allowed_tools, list):
        raise ValidationError("allowed_tools", "must be a list")
    
    if not allowed_tools:
        return True  # 空列表表示使用默认工具
    
    invalid_tools = set(allowed_tools) - set(ALLOWED_TOOLS)
    if invalid_tools:
        raise ValidationError(
            "allowed_tools",
            f"invalid tools: {', '.join(invalid_tools)}. "
            f"Valid tools: {', '.join(ALLOWED_TOOLS)}"
        )
    
    return True


def validate_metadata(metadata: Dict[str, Any], max_size: int = 1000) -> bool:
    """
    验证元数据
    
    Args:
        metadata: 元数据字典
        max_size: 最大键值对数量
        
    Returns:
        bool: 是否有效
        
    Raises:
        ValidationError: 验证失败时抛出
    """
    if not isinstance(metadata, dict):
        raise ValidationError("metadata", "must be a dictionary")
    
    if len(metadata) > max_size:
        raise ValidationError("metadata", f"cannot exceed {max_size} key-value pairs")
    
    # 检查键的有效性
    for key in metadata.keys():
        if not isinstance(key, str):
            raise ValidationError("metadata", "all keys must be strings")
        if len(key) > 100:
            raise ValidationError("metadata", f"key '{key}' exceeds maximum length of 100 characters")
    
    return True




