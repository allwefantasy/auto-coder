"""
BaseRunner 提供了所有运行器的基础实现和接口定义。

这个模块定义了代理运行的核心流程，包括请求处理、事件流生成和变更应用等。
各种具体运行器通过继承 BaseRunner 并实现特定的运行逻辑来提供不同的运行模式。
"""

import logging
from typing import Generator, Any, Dict, Optional, Callable, List

from autocoder.common.v2.agent.agentic_edit_types import (
    AgenticEditRequest, AgentEvent, CompletionEvent, 
    AgenticEditConversationConfig, CommandConfig
)
from autocoder.common.v2.memory_config import MemoryConfig
from autocoder.common import AutoCoderArgs
from autocoder.common.v2.source_code_list import SourceCodeList
from autocoder.common.v2.agent.agentic_edit import AgenticEdit

logger = logging.getLogger(__name__)

class BaseRunner:
    """
    代理运行器的基类，定义了运行代理的核心流程和接口。
    
    所有具体的运行器实现（终端、事件系统、SDK）都应该继承这个类，
    并根据特定需求实现 run 方法。
    """
    
    def __init__(
        self,
        llm: Any,
        conversation_history: List[Dict[str, Any]],
        files: SourceCodeList,
        args: AutoCoderArgs,
        memory_config: MemoryConfig,
        command_config: Optional[CommandConfig] = None,
        conversation_name: str = "current",
        conversation_config: Optional[AgenticEditConversationConfig] = None
    ):
        """
        初始化代理运行器。
        
        Args:
            llm: 大语言模型实例
            conversation_history: 对话历史
            files: 源代码文件列表
            args: 自动编码器参数
            memory_config: 内存配置
            command_config: 命令配置（可选）
            conversation_name: 会话名称（默认为"current"）
            conversation_config: 会话配置（可选）
        """
        self.llm = llm
        self.conversation_history = conversation_history
        self.files = files
        self.args = args
        self.memory_config = memory_config
        self.command_config = command_config
        self.conversation_name = conversation_name
        self.conversation_config = conversation_config                
        
        self.agent = AgenticEdit(
            llm=llm,
            conversation_history=conversation_history,
            files=files,
            args=args,
            memory_config=memory_config,
            command_config=command_config,
            conversation_name=conversation_name,
            conversation_config=conversation_config
        )
    
    def run(self, request: AgenticEditRequest) -> Any:
        """
        运行代理处理请求。
        
        这是一个抽象方法，需要由子类实现。
        
        Args:
            request: 代理编辑请求
            
        Returns:
            根据具体实现返回不同类型的结果
        """
        raise NotImplementedError("子类必须实现run方法")
    
    def apply_pre_changes(self) -> None:
        """应用预处理变更"""
        self.agent.apply_pre_changes()
    
    def apply_changes(self) -> None:
        """应用代理执行后的变更"""
        self.agent.apply_changes()
    
    def analyze(self, request: AgenticEditRequest) -> Generator[AgentEvent, None, None]:
        """
        分析请求并生成事件流。
        
        Args:
            request: 代理编辑请求
            
        Returns:
            事件生成器
        """
        return self.agent.analyze(request)
