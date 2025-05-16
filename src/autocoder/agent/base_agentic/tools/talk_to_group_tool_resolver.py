from typing import Optional, Dict, Any
import os
from loguru import logger
from datetime import datetime
import typing

from ..types import TalkToGroupTool, ToolResult
from ..tools.base_tool_resolver import BaseToolResolver
from ..agent_hub import AgentHub, Group
from autocoder.common import AutoCoderArgs

if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent


class TalkToGroupToolResolver(BaseToolResolver):
    """
    处理talk_to_group工具的解析器
    """
    
    def resolve(self) -> ToolResult:
        """
        解析和执行talk_to_group工具
        
        Returns:
            ToolResult: 工具执行结果
        """
        try:
            # 获取参数
            group_name = self.tool.group_name
            content = self.tool.content
            mentions_names = self.tool.mentions or []
            print_conversation = self.tool.print_conversation
            
            # 获取目标群组
            groups = AgentHub.get_all_groups()
            target_group = None
            for group in groups:
                if group.name == group_name:
                    target_group = group
                    break
                    
            if not target_group:
                return ToolResult(
                    success=False,
                    message=f"找不到名为 '{group_name}' 的群组",
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
            
            # 执行talk_to_group操作
            self.agent.talk_to_group(
                group=target_group, 
                content=content, 
                mentions=mentions, 
                print_conversation=print_conversation
            )
            
            # 获取群组消息历史
            with target_group._history_lock:
                group_history = target_group.history.copy()
            
            # 获取群组成员
            with target_group._members_lock:
                members = [member.name for member in target_group.members]
            
            # 格式化群组历史
            formatted_history = f"群组：{group_name}\n"
            formatted_history += f"成员：{', '.join(members)}\n\n"
            formatted_history += "对话历史：\n\n"
            
            for msg in group_history:
                sender_display = "你" if msg.sender == self.agent.name else msg.sender
                mention_text = ""
                if msg.mentions:
                    mention_display = ["你" if m == self.agent.name else m for m in msg.mentions]
                    mention_text = f" @{' @'.join(mention_display)}"
                formatted_history += f"[{sender_display}]{mention_text}: {msg.content}\n\n"
            
            # 返回结果
            return ToolResult(
                success=True,
                message=f"已向群组 '{group_name}' 探讨",
                content=formatted_history
            )
            
        except Exception as e:
            logger.exception(f"执行talk_to_group工具时出错: {e}")
            return ToolResult(
                success=False,
                message=f"执行talk_to_group工具时出错: {str(e)}",
                content=None
            ) 