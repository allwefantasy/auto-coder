from typing import List, Dict, Any, Union
import json
from pydantic import BaseModel
import byzerllm
from autocoder.common.printer import Printer
from autocoder.rag.token_counter import count_tokens
from loguru import logger
from autocoder.common import AutoCoderArgs

class PruneStrategy(BaseModel):
    name: str
    description: str
    config: Dict[str, Any] = {"safe_zone_tokens": 0, "group_size": 4}

class ConversationPruner:
    def __init__(self, args: AutoCoderArgs, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        self.args = args
        self.llm = llm
        self.printer = Printer()
        self.strategies = {
            "summarize": PruneStrategy(
                name="summarize",
                description="对早期对话进行分组摘要，保留关键信息",
                config={"safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens, "group_size": self.args.conversation_prune_group_size}
            ),
            "truncate": PruneStrategy(
                name="truncate",
                description="分组截断最早的部分对话",
                config={"safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens, "group_size": self.args.conversation_prune_group_size}
            ),
            "hybrid": PruneStrategy(
                name="hybrid",
                description="先尝试分组摘要，如果仍超限则分组截断",
                config={"safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens, "group_size": self.args.conversation_prune_group_size}
            )
        }

    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """获取所有可用策略"""
        return [strategy.dict() for strategy in self.strategies.values()]

    def prune_conversations(self, conversations: List[Dict[str, Any]], 
                            strategy_name: str = "summarize") -> List[Dict[str, Any]]:
        """
        根据策略修剪对话
        Args:
            conversations: 原始对话列表            
            strategy_name: 策略名称
        Returns:
            修剪后的对话列表
        """        
        current_tokens = count_tokens(json.dumps(conversations, ensure_ascii=False))
        if current_tokens <= self.args.conversation_prune_safe_zone_tokens:
            return conversations

        strategy = self.strategies.get(strategy_name, self.strategies["summarize"])
        
        if strategy.name == "summarize":
            return self._summarize_prune(conversations, strategy.config)
        elif strategy.name == "truncate":
            return self._truncate_prune(conversations)
        elif strategy.name == "hybrid":
            pruned = self._summarize_prune(conversations, strategy.config)
            if count_tokens(json.dumps(pruned, ensure_ascii=False)) > self.args.conversation_prune_safe_zone_tokens:
                return self._truncate_prune(pruned)
            return pruned
        else:
            logger.warning(f"Unknown strategy: {strategy_name}, using summarize instead")
            return self._summarize_prune(conversations, strategy.config)

    def _summarize_prune(self, conversations: List[Dict[str, Any]], 
                         config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """摘要式剪枝"""
        safe_zone_tokens = config.get("safe_zone_tokens", 50*1024)
        group_size = config.get("group_size", 4)
        processed_conversations = conversations.copy()
        
        while True:
            current_tokens = count_tokens(json.dumps(processed_conversations, ensure_ascii=False))
            if current_tokens <= safe_zone_tokens:
                break
                
            # 找到要处理的对话组
            early_conversations = processed_conversations[:group_size]
            recent_conversations = processed_conversations[group_size:]
            
            if not early_conversations:
                break
                
            # 生成当前组的摘要
            group_summary = self._generate_summary.with_llm(self.llm).run(early_conversations[-group_size:])
            
            # 更新对话历史
            processed_conversations =  [
                {"role": "user", "content": f"历史对话摘要：\n{group_summary}"},
                {"role": "assistant", "content": f"收到"}
            ] + recent_conversations
            
        return processed_conversations

    @byzerllm.prompt()
    def _generate_summary(self, conversations: List[Dict[str, Any]]) -> str:
        '''
        请用中文将以下对话浓缩为要点，保留关键决策和技术细节：
        
        <history_conversations>
        {{conversations}}
        </history_conversations>
        '''    
        return {
            "conversations": json.dumps(conversations, ensure_ascii=False)
        }    

    def _truncate_prune(self, conversations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """截断式剪枝"""
        safe_zone_tokens = self.strategies["truncate"].config.get("safe_zone_tokens", 0)
        group_size = self.strategies["truncate"].config.get("group_size", 4)
        processed_conversations = conversations.copy()
        
        while True:
            current_tokens = count_tokens(json.dumps(processed_conversations, ensure_ascii=False))
            if current_tokens <= safe_zone_tokens:
                break
                
            # 如果剩余对话不足一组，直接返回
            if len(processed_conversations) <= group_size:
                return []
                
            # 移除最早的一组对话
            processed_conversations = processed_conversations[group_size:]
            
        return processed_conversations