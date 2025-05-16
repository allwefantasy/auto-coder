from typing import Optional, Dict, Any
import os
from loguru import logger
from datetime import datetime
import typing

from ..types import TalkToTool, ToolResult
from ..tools.base_tool_resolver import BaseToolResolver
from ..agent_hub import AgentHub
from autocoder.common import AutoCoderArgs

if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent


class TalkToToolResolver(BaseToolResolver):
    """
    处理talk_to工具的解析器
    """
    
    def resolve(self) -> ToolResult:
        """
        解析和执行talk_to工具
        
        Returns:
            ToolResult: 工具执行结果
        """
        try:
            # 获取参数
            agent_name = self.tool.agent_name
            content = self.tool.content
            mentions_names = self.tool.mentions or []
            print_conversation = self.tool.print_conversation
            
            # 获取目标代理
            target_agent = AgentHub.get_agent(agent_name)
            if not target_agent:
                return ToolResult(
                    success=False,
                    message=f"找不到名为 '{agent_name}' 的代理",
                    content=None
                )
            
            # 解析提及的代理
            mentions = []
            for name in mentions_names:
                agent = AgentHub.get_agent(name)
                if agent:
                    mentions.append(agent)
                else:
                    logger.warning(f"找不到提及的代理: {name}")
            
            # 执行talk_to操作
            self.agent.talk_to(
                other=target_agent, 
                content=content, 
                mentions=mentions, 
                print_conversation=print_conversation
            )
            
            # 获取对话历史记录，格式化为易读的形式
            with self.agent._chat_lock:
                chat_history = self.agent.private_chats.get(agent_name, [])
            
            # 格式化聊天历史
            formatted_history = "对话历史：\n\n"
            for msg in chat_history:
                sender_display = "你" if msg.sender == self.agent.name else msg.sender
                formatted_history += f"[{sender_display}]: {msg.content}\n\n"
            
            # 返回结果
            return ToolResult(
                success=True,
                message=f"已向Agent '{agent_name}' 讨论",
                content=formatted_history
            )
            
        except Exception as e:
            logger.exception(f"执行talk_to工具时出错: {e}")
            return ToolResult(
                success=False,
                message=f"执行talk_to工具时出错: {str(e)}",
                content=None
            ) 