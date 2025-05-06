from datetime import datetime
import typing

if typing.TYPE_CHECKING:
    from .agent_hub import Group
import byzerllm
from typing import Union,List
from concurrent.futures import ThreadPoolExecutor
from pydantic import BaseModel
import threading
from loguru import logger
class GroupMember(BaseModel):
    member: str
    reason: str

class GroupMemberResponse(BaseModel):
    group_name: str
    members: List[GroupMember]

class GroupUtils:
    _executor = ThreadPoolExecutor(max_workers=8)
    _executor_lock = threading.Lock()

    def __init__(self, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        self.llm = llm

    def auto_select_group(self, content: str, groups: List['Group']) -> List[GroupMemberResponse]:
        futures = []
        with self._executor_lock:
            for group in groups:
                future = self._executor.submit(
                    self._safe_select_group,
                    content,
                    group
                )
                futures.append((group.name, future))

        results = []
        for group_name, future in futures:
            try:
                members = future.result()
                if members and len(members) > 0:
                    results.append(GroupMemberResponse(
                        group_name=group_name,
                        members=members
                    ))
            except Exception as e:
                import traceback
                traceback.print_exc()
                logger.error(f"Failed to select group {group_name}: {str(e)}")
        
        return results

    def _safe_select_group(self, content: str, group: 'Group') -> List[GroupMember]:
        try:
            return self.select_group.with_llm(self.llm).with_return_type(List[GroupMember]).run(content=content, group=group)
        except Exception as e:
            logger.error(f"Error in select_group: {str(e)}")
            return []
    
    @byzerllm.prompt()
    def select_group(self, content: str, group: 'Group') -> List[GroupMember]:
        '''
        当前时间: {{ time }}
        用户发来了如下问题:
        <user_question>
        {{ content }}
        </user_question>

        下面是群组 {{ group_name }} 所有成员及其对应的角色：
        {% for member_info in members_info %}
        ===== {{ member_info[0] }} =====
        <who_are_you>
        {{ member_info[1] }}
        </who_are_you>
        {% endfor %}

        请分析该群组中的成员是否有人可以回答用户的问题。

        请生成 JSON 格式回复：

        ```json
        [
            {
                "member": "可以回答用户问题的用户名",
                "reason": "选择这些用户的原因"
            }
        ]
        ```
        如果群组中没有合适的成员可以回答问题，请返回空列表。
        请严格按照 JSON 格式输出，不要有任何多余的内容。
        '''
        members_info = [(member.name, member.system_prompt) for member in group.members]
        
        context = {
            "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),            
            "group_name": group.name,
            "members_info": members_info
        }
        return context