import typing
import byzerllm
from typing import List, Dict, Optional, Literal, Any, Union
from pydantic import BaseModel
from loguru import logger
import threading
from concurrent.futures import ThreadPoolExecutor
import os
from datetime import datetime
from .types import Message, ReplyDecision
from .utils import GroupUtils,GroupMemberResponse

if typing.TYPE_CHECKING:
    from .base_agent import BaseAgent

class AgentHub:
    """管理所有Agent实例的全局中心"""
    _instance = None
    agents: Dict[str, 'BaseAgent'] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register_agent(cls, agent: 'BaseAgent'):
        """注册一个新的Agent"""
        if agent.name in cls.agents:
            raise ValueError(f"Agent with name {agent.name} already exists")
        cls.agents[agent.name] = agent

    @classmethod
    def get_agent(cls, name: str) -> Optional['BaseAgent']:
        """根据名称获取Agent"""
        return cls.agents.get(name)

    @classmethod
    def list_agents(cls) -> List[str]:
        """获取所有Agent名称"""
        return list(cls.agents.keys())

    @classmethod
    def get_all_groups(cls) -> List['Group']:
        """获取所有群组实例"""
        return list(GroupHub.groups.values())

class GroupHub:
    """管理所有Group实例的全局中心"""
    _instance = None
    groups: Dict[str, 'Group'] = {}
    _groups_lock = threading.RLock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def register_group(cls, group: 'Group'):
        """注册一个新的Group"""
        with cls._groups_lock:
            if group.name in cls.groups:
                raise ValueError(f"Group with name {group.name} already exists")
            cls.groups[group.name] = group

    @classmethod
    def get_group(cls, name: str) -> Optional['Group']:
        """根据名称获取Group"""
        with cls._groups_lock:
            return cls.groups.get(name)

    @classmethod
    def list_groups(cls) -> List[str]:
        """获取所有Group名称"""
        with cls._groups_lock:
            return list(cls.groups.keys())



class Group:
    # 类级线程池（所有 Group 实例共享）
    _executor = ThreadPoolExecutor(max_workers=min(32, (os.cpu_count() or 1) * 4 + 4))
    
    def __init__(self, name: str):
        self.name = name
        self.members: List[Agent] = []
        self.history: List[Message] = []
        # 成员列表和消息历史的读写锁
        self._members_lock = threading.RLock()
        self._history_lock = threading.RLock()
        # 自动注册到GroupHub
        GroupHub.register_group(self)
        
    def add_member(self, agent: 'Agent'):
        with self._members_lock:
            if agent not in self.members:
                self.members.append(agent)
                with agent._group_lock:  # 访问 Agent 的锁
                    agent.joined_groups[self.name] = self
    
    def _safe_send_message(self, member: 'Agent', message: Message, print_conversation: bool):
        try:                        
            # 调用 Agent 的线程安全接收方法
            member.threadsafe_receive(message,print_conversation=print_conversation)
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Message delivery failed to {member.name}: {str(e)}")

    def _handle_send_result(self, future):
        try:
            future.result()
        except Exception as e:            
            logger.error(f"Message delivery error: {str(e)}")
            
    def broadcast(self, message: Message, print_conversation: bool = False):
        # 消息历史写入需要同步
        with self._history_lock:
            self.history.append(message)
        
        # 使用线程池并行发送
        futures = []
        with self._members_lock:  # 保护成员列表遍历
            current_members = self.members.copy()
        
        for member in current_members:
            if member.name == message.sender:
                continue
                
            futures.append(
                self._executor.submit(
                    self._safe_send_message,
                    member, message, print_conversation
                )
            )

        # 异步等待所有任务完成（可选）
        for future in futures:
            future.add_done_callback(self._handle_send_result)

        if print_conversation:
            with self._history_lock:  # 同步打印
                print(f"[Group Broadcast End] {message.sender} finished broadcasting to {self.name} group")                


class GroupMembership:
    def __init__(self, agent: 'BaseAgent', group: 'Group'):
        self.agent = agent
        self.group = group
        
    def talk_to_all(self, content: str):
        message = Message(
            sender=self.agent.name,
            content=content,
            is_group=True,
            group_name=self.group.name
        )
        self.group.broadcast(message)
        
    def talk_to(self, content: str, mentions: List['BaseAgent']):
        message = Message(
            sender=self.agent.name,
            content=f"@{' @'.join([a.name for a in mentions])} {content}",
            is_group=True,
            group_name=self.group.name,
            mentions=[a.name for a in mentions]
        )
        self.group.broadcast(message)