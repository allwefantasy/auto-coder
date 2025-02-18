from typing import List, Dict, Any
import json
from pydantic import BaseModel
import byzerllm
from autocoder.common.printer import Printer
from autocoder.utils.llms import count_tokens
from loguru import logger

class PruneStrategy(BaseModel):
    name: str
    description: str
    config: Dict[str, Any] = {}

class ConversationPruner:
    def __init__(self, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        self.llm = llm
        self.printer = Printer()
        self.strategies = {
            "summarize": PruneStrategy(
                name="summarize",
                description="对早期对话进行摘要，保留关键信息",
                config={"keep_recent": 3}
            ),
            "truncate": PruneStrategy(
                name="truncate",
                description="直接截断最早的部分对话",
                config={}
            ),
            "hybrid": PruneStrategy(
                name="hybrid",
                description="先尝试摘要，如果仍超限则截断",
                config={"keep_recent": 3}
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
        keep_recent = config.get("keep_recent", 3)
        recent_conversations = conversations[-keep_recent:]
        early_conversations = conversations[:-keep_recent]

        if not early_conversations:
            return recent_conversations

        # 生成摘要
        summary = self._generate_summary(early_conversations)
        
        # 重组对话历史
        return [
            {"role": "system", "content": f"历史对话摘要：{summary}"}
        ] + recent_conversations

    def _generate_summary(self, conversations: List[Dict[str, Any]]) -> str:
        """生成对话摘要"""
        summary_prompt = f"请用中文将以下对话浓缩为要点，保留关键决策和技术细节：\n{conversations}"
        return self.llm.chat_oai([{"role": "user", "content": summary_prompt}])[0].output

    def _truncate_prune(self, conversations: List[Dict[str, Any]], max_tokens: int) -> List[Dict[str, Any]]:
        """截断式剪枝"""
        removed_tokens = 0
        new_conversations = []
        
        # 从最早的消息开始移除
        for conv in reversed(conversations):
            conv_tokens = count_tokens(conv["content"])
            if removed_tokens + conv_tokens <= max_tokens:
                removed_tokens += conv_tokens
                new_conversations.insert(0, conv)
            else:
                break
        
        return new_conversations