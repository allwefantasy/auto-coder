"""
CLI 选项定义模块

定义命令行接口的选项和结果数据结构。
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any


@dataclass
class CLIOptions:
    """CLI选项数据类，用于配置命令行工具的行为。"""
    
    # 运行模式选项
    print_mode: bool = False  # 单次运行模式，执行一次查询后退出
    continue_session: bool = False  # 继续最近的对话
    resume_session: Optional[str] = None  # 恢复特定会话的ID
    
    # 输入选项
    prompt: Optional[str] = None  # 提示内容，如果为None则从stdin读取
    input_format: str = "text"  # 输入格式，可选值: text, json, stream-json
    
    # 输出选项
    output_format: str = "text"  # 输出格式，可选值: text, json, stream-json
    verbose: bool = False  # 是否输出详细信息
    
    # 高级选项
    max_turns: int = 3  # 最大对话轮数
    system_prompt: Optional[str] = None  # 系统提示
    allowed_tools: list = field(default_factory=list)  # 允许使用的工具列表
    permission_mode: str = "manual"  # 权限模式，可选值: manual, acceptEdits
    
    def validate(self) -> None:
        """验证选项的有效性。"""
        # 验证输出格式
        valid_formats = ["text", "json", "stream-json"]
        if self.output_format not in valid_formats:
            raise ValueError(f"无效的输出格式: {self.output_format}，有效值为: {', '.join(valid_formats)}")
        
        # 验证输入格式
        if self.input_format not in valid_formats:
            raise ValueError(f"无效的输入格式: {self.input_format}，有效值为: {', '.join(valid_formats)}")
        
        # 验证权限模式
        valid_permission_modes = ["manual", "acceptEdits"]
        if self.permission_mode not in valid_permission_modes:
            raise ValueError(f"无效的权限模式: {self.permission_mode}，有效值为: {', '.join(valid_permission_modes)}")
        
        # 验证最大对话轮数
        if self.max_turns <= 0:
            raise ValueError("max_turns必须为正数")
        
        # 验证会话选项的互斥性
        if self.continue_session and self.resume_session:
            raise ValueError("continue_session和resume_session不能同时设置")


@dataclass
class CLIResult:
    """CLI执行结果数据类，用于返回命令执行的结果。"""
    
    success: bool  # 是否成功执行
    output: str = ""  # 输出内容
    error: Optional[str] = None  # 错误信息
    debug_info: Optional[Dict[str, Any]] = None  # 调试信息
