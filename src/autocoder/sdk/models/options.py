


"""
Auto-Coder SDK 选项配置模型

定义AutoCodeOptions类，提供完整的配置选项和验证规则。
"""

from dataclasses import dataclass, field
from typing import Optional, List, Union, Dict, Any
from pathlib import Path
import os

from ..constants import (
    DEFAULT_MAX_TURNS,
    DEFAULT_OUTPUT_FORMAT,
    DEFAULT_PERMISSION_MODE,
    OUTPUT_FORMATS,
    PERMISSION_MODES,
    ALLOWED_TOOLS
)
from ..exceptions import ValidationError


@dataclass
class AutoCodeOptions:
    """AutoCoder选项配置类"""
    
    # 基础配置
    max_turns: int = DEFAULT_MAX_TURNS
    system_prompt: Optional[str] = None
    cwd: Optional[Union[str, Path]] = None
    
    # 工具和权限配置
    allowed_tools: List[str] = field(default_factory=list)
    permission_mode: str = DEFAULT_PERMISSION_MODE
    
    # 输出配置
    output_format: str = DEFAULT_OUTPUT_FORMAT
    stream: bool = False
    
    # 会话配置
    session_id: Optional[str] = None
    continue_session: bool = False  # 继续最近的对话
    
    # 模型配置
    model: Optional[str] = None
    temperature: float = 0.7
    
    # 高级配置
    timeout: int = 30
    verbose: bool = False
    include_project_structure: bool = True
    pr: bool = False  # 是否创建 PR
    
    def __post_init__(self):
        """初始化后验证"""
        self._normalize_values()
        self.validate()
    
    def validate(self) -> None:
        """验证配置选项"""
        
        # 验证max_turns（-1表示不限制）
        if self.max_turns <= 0 and self.max_turns != -1:
            raise ValidationError("max_turns", "must be positive integer or -1 (unlimited)")
        
        if self.max_turns > 100 and self.max_turns != -1:
            raise ValidationError("max_turns", "cannot exceed 100 (unless -1 for unlimited)")
        
        # 验证output_format
        if self.output_format not in OUTPUT_FORMATS:
            raise ValidationError(
                "output_format", 
                f"must be one of: {', '.join(OUTPUT_FORMATS.keys())}"
            )
        
        # 验证permission_mode
        if self.permission_mode not in PERMISSION_MODES:
            raise ValidationError(
                "permission_mode",
                f"must be one of: {', '.join(PERMISSION_MODES.keys())}"
            )
        
        # 验证allowed_tools
        if self.allowed_tools:
            invalid_tools = set(self.allowed_tools) - set(ALLOWED_TOOLS)
            if invalid_tools:
                raise ValidationError(
                    "allowed_tools",
                    f"invalid tools: {', '.join(invalid_tools)}. "
                    f"Valid tools: {', '.join(ALLOWED_TOOLS)}"
                )
        
        # 验证temperature
        if not 0.0 <= self.temperature <= 2.0:
            raise ValidationError("temperature", "must be between 0.0 and 2.0")
        
        # 验证timeout
        if self.timeout <= 0:
            raise ValidationError("timeout", "must be positive integer")
        
        # 验证cwd
        if self.cwd is not None:
            cwd_path = Path(self.cwd)
            if not cwd_path.exists():
                raise ValidationError("cwd", f"directory does not exist: {self.cwd}")
            if not cwd_path.is_dir():
                raise ValidationError("cwd", f"path is not a directory: {self.cwd}")
    
    def _normalize_values(self) -> None:
        """标准化配置值"""
        
        # 标准化cwd路径
        if self.cwd is not None:
            self.cwd = str(Path(self.cwd).resolve())
        else:
            self.cwd = os.getcwd()
        
        # 如果没有指定allowed_tools，使用默认值
        if not self.allowed_tools:
            self.allowed_tools = ALLOWED_TOOLS.copy()
        
        # 标准化字符串值
        self.output_format = self.output_format.lower()
        self.permission_mode = self.permission_mode.lower()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "max_turns": self.max_turns,
            "system_prompt": self.system_prompt,
            "cwd": self.cwd,
            "allowed_tools": self.allowed_tools,
            "permission_mode": self.permission_mode,
            "output_format": self.output_format,
            "stream": self.stream,
            "session_id": self.session_id,
            "model": self.model,
            "temperature": self.temperature,
            "timeout": self.timeout,
            "verbose": self.verbose,
            "include_project_structure": self.include_project_structure,
            "pr": self.pr
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AutoCodeOptions":
        """从字典创建实例"""
        # 过滤掉不存在的字段
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered_data = {k: v for k, v in data.items() if k in valid_fields}
        
        return cls(**filtered_data)
    
    def copy(self, **changes) -> "AutoCodeOptions":
        """创建副本并应用更改"""
        data = self.to_dict()
        data.update(changes)
        return self.from_dict(data)
    
    def merge(self, other: "AutoCodeOptions") -> "AutoCodeOptions":
        """合并两个配置对象"""
        # 创建新的配置对象，从当前对象开始
        data = self.to_dict()
        
        # 只覆盖other中明确设置的值（非None且非默认值）
        if other.max_turns != DEFAULT_MAX_TURNS:
            data["max_turns"] = other.max_turns
        if other.system_prompt is not None:
            data["system_prompt"] = other.system_prompt
        if other.output_format != DEFAULT_OUTPUT_FORMAT:
            data["output_format"] = other.output_format
        if other.permission_mode != DEFAULT_PERMISSION_MODE:
            data["permission_mode"] = other.permission_mode
        if other.model is not None:
            data["model"] = other.model
        if other.temperature != 0.7:
            data["temperature"] = other.temperature
        if other.timeout != 30:
            data["timeout"] = other.timeout
        if other.verbose is not False:
            data["verbose"] = other.verbose
        if other.stream is not False:
            data["stream"] = other.stream
        if other.include_project_structure is not True:
            data["include_project_structure"] = other.include_project_structure
        if other.session_id is not None:
            data["session_id"] = other.session_id
        if other.allowed_tools != []:
            data["allowed_tools"] = other.allowed_tools
        
        return self.from_dict(data)


