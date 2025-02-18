from typing import List, Dict, Any, Union
import json
from pydantic import BaseModel
import byzerllm
from autocoder.common.printer import Printer
from autocoder.utils.llms import count_tokens
from loguru import logger

class PruneStrategy(BaseModel):
    name: str
    description: str
    config: Dict[str, Any] = {"safe_zone_tokens": 0, "group_size": 4}

class ConversationPruner:
    def __init__(self, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        self.llm = llm
        self.printer = Printer()
        self.strategies = {
            "summarize": PruneStrategy(
                name="summarize",
                description="对早期对话进行分组摘要，保留关键信息",
                config={"safe_zone_tokens": 500, "group_size": 4}
            ),
            "truncate": PruneStrategy(
                name="truncate",
                description="分组截断最早的部分对话",
                config={"safe_zone_tokens": 500, "group_size": 4}
            ),
            "hybrid": PruneStrategy(
                name="hybrid",
                description="先尝试分组摘要，如果仍超限则分组截断",
                config={"safe_zone_tokens": 500, "group_size": 4}
            )
        }

    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """获取所有可用策略"""
        return [strategy.dict() for strategy in self.strategies.values()]

    def prune_conversations(self, conversations: List[Dict[str, Any]], 
                          max_tokens: int, strategy_name: str = "summarize") -> List[Dict[str, Any]]:
        """
        根据策略修剪对话
        Args:
            conversations: 原始对话列表
            max_tokens: 最大token数
            strategy_name: 策略名称
        Returns:
            修剪后的对话列表
        """
        current_tokens = count_tokens(json.dumps(conversations, ensure_ascii=False))
        if current_tokens <= max_tokens:
            return conversations

        strategy = self.strategies.get(strategy_name, self.strategies["summarize"])
        
        if strategy.name == "summarize":
            return self._summarize_prune(conversations, max_tokens, strategy.config)
        elif strategy.name == "truncate":
            return self._truncate_prune(conversations, max_tokens)
        elif strategy.name == "hybrid":
            pruned = self._summarize_prune(conversations, max_tokens, strategy.config)
            if count_tokens(json.dumps(pruned, ensure_ascii=False)) > max_tokens:
                return self._truncate_prune(pruned, max_tokens)
            return pruned
        else:
            logger.warning(f"Unknown strategy: {strategy_name}, using summarize instead")
            return self._summarize_prune(conversations, max_tokens, strategy.config)

    def _summarize_prune(self, conversations: List[Dict[str, Any]], 
                        max_tokens: int, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """摘要式剪枝"""
        safe_zone_tokens = config.get("safe_zone_tokens", 0)
        group_size = config.get("group_size", 4)
        processed_conversations = conversations.copy()
        
        while True:
            current_tokens = count_tokens(json.dumps(processed_conversations, ensure_ascii=False))
            if current_tokens <= max_tokens - safe_zone_tokens:
                break
                
            # 找到要处理的对话组
            early_conversations = processed_conversations[:-group_size]
            recent_conversations = processed_conversations[-group_size:]
            
            if not early_conversations:
                break
                
            # 生成当前组的摘要
            group_summary = self._generate_summary(early_conversations[-group_size:])
            
            # 更新对话历史
            processed_conversations = early_conversations[:-group_size] + [
                {"role": "system", "content": f"历史对话摘要：{group_summary}"}
            ] + recent_conversations
            
        return processed_conversations

    def _generate_summary(self, conversations: List[Dict[str, Any]]) -> str:
        """生成对话摘要"""
        summary_prompt = f"请用中文将以下对话浓缩为要点，保留关键决策和技术细节：\n{conversations}"
        return self.llm.chat_oai([{"role": "user", "content": summary_prompt}])[0].output

    def _truncate_prune(self, conversations: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
        """截断式剪枝"""
        safe_zone_tokens = self.strategies["truncate"].config.get("safe_zone_tokens", 0)
        group_size = self.strategies["truncate"].config.get("group_size", 4)
        processed_conversations = conversations.copy()
        
        while True:
            current_tokens = count_tokens(json.dumps(processed_conversations, ensure_ascii=False))
            if current_tokens <= max_tokens - safe_zone_tokens:
                break
                
            # 如果剩余对话不足一组，直接返回
            if len(processed_conversations) <= group_size:
                return []
                
            # 移除最早的一组对话
            processed_conversations = processed_conversations[group_size:]
            
        return processed_conversations