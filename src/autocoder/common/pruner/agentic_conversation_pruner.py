from typing import List, Dict, Any, Union
import json
import re
from pydantic import BaseModel
import byzerllm
from autocoder.common.printer import Printer
from autocoder.rag.token_counter import count_tokens
from loguru import logger
from autocoder.common import AutoCoderArgs

class AgenticPruneStrategy(BaseModel):
    name: str
    description: str
    config: Dict[str, Any] = {"safe_zone_tokens": 0}

class AgenticConversationPruner:
    """
    Specialized conversation pruner for agentic conversations that cleans up tool outputs.
    
    This pruner specifically targets tool result messages (role='user', content contains '<tool_result>')
    and replaces their content with a placeholder message to reduce token usage while maintaining
    conversation flow.
    """
    
    def __init__(self, args: AutoCoderArgs, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        self.args = args
        self.llm = llm
        self.printer = Printer()
        self.replacement_message = "This message has been cleared. If you still want to get this information, you can call the tool again to retrieve it."
        
        self.strategies = {
            "tool_output_cleanup": AgenticPruneStrategy(
                name="tool_output_cleanup",
                description="Clean up tool output results by replacing content with placeholder messages",
                config={"safe_zone_tokens": self.args.conversation_prune_safe_zone_tokens}
            )
        }

    def get_available_strategies(self) -> List[Dict[str, Any]]:
        """Get all available pruning strategies"""
        return [strategy.model_dump() for strategy in self.strategies.values()]

    def prune_conversations(self, conversations: List[Dict[str, Any]], 
                            strategy_name: str = "tool_output_cleanup") -> List[Dict[str, Any]]:
        """
        Prune conversations by cleaning up tool outputs.
        
        Args:
            conversations: Original conversation list            
            strategy_name: Strategy name
            
        Returns:
            Pruned conversation list
        """        
        safe_zone_tokens = self.args.conversation_prune_safe_zone_tokens
        current_tokens = count_tokens(json.dumps(conversations, ensure_ascii=False))
        
        if current_tokens <= safe_zone_tokens:
            return conversations

        strategy = self.strategies.get(strategy_name, self.strategies["tool_output_cleanup"])
        
        if strategy.name == "tool_output_cleanup":
            return self._tool_output_cleanup_prune(conversations, strategy.config)
        else:
            logger.warning(f"Unknown strategy: {strategy_name}, using tool_output_cleanup instead")
            return self._tool_output_cleanup_prune(conversations, strategy.config)

    def _tool_output_cleanup_prune(self, conversations: List[Dict[str, Any]], 
                                   config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Clean up tool outputs by replacing their content with placeholder messages.
        
        This method:
        1. Identifies tool result messages (role='user' with '<tool_result' in content)
        2. Starts from the first tool output and progressively cleans them
        3. Stops when token count is within safe zone
        """
        safe_zone_tokens = config.get("safe_zone_tokens", 50 * 1024)
        processed_conversations = conversations.copy()
        
        # Find all tool result message indices
        tool_result_indices = []
        for i, conv in enumerate(processed_conversations):
            if (conv.get("role") == "user" and 
                isinstance(conv.get("content"), str) and 
                self._is_tool_result_message(conv.get("content", ""))):
                tool_result_indices.append(i)
        
        logger.info(f"Found {len(tool_result_indices)} tool result messages to potentially clean")
        
        # Clean tool outputs one by one, starting from the first one
        for tool_index in tool_result_indices:
            current_tokens = count_tokens(json.dumps(processed_conversations, ensure_ascii=False))
            
            if current_tokens <= safe_zone_tokens:
                logger.info(f"Token count ({current_tokens}) is within safe zone ({safe_zone_tokens}), stopping cleanup")
                break
            
            # Extract tool name for a more specific replacement message
            tool_name = self._extract_tool_name(processed_conversations[tool_index]["content"])
            replacement_content = self._generate_replacement_message(tool_name)
            
            # Replace the content
            original_content = processed_conversations[tool_index]["content"]
            processed_conversations[tool_index]["content"] = replacement_content
            
            logger.info(f"Cleaned tool result at index {tool_index} (tool: {tool_name}), "
                       f"reduced from {len(original_content)} to {len(replacement_content)} characters")
        
        final_tokens = count_tokens(json.dumps(processed_conversations, ensure_ascii=False))
        logger.info(f"Cleanup completed. Token count: {current_tokens} -> {final_tokens}")
        
        return processed_conversations

    def _is_tool_result_message(self, content: str) -> bool:
        """
        Check if a message content contains tool result XML.
        
        Args:
            content: Message content to check
            
        Returns:
            True if content contains tool result format
        """
        return "<tool_result" in content and "tool_name=" in content

    def _extract_tool_name(self, content: str) -> str:
        """
        Extract tool name from tool result XML content.
        
        Args:
            content: Tool result XML content
            
        Returns:
            Tool name or 'unknown' if not found
        """
        # Pattern to match: <tool_result tool_name='...' or <tool_result tool_name="..."
        pattern = r"<tool_result[^>]*tool_name=['\"]([^'\"]+)['\"]"
        match = re.search(pattern, content)
        
        if match:
            return match.group(1)
        return "unknown"

    def _generate_replacement_message(self, tool_name: str) -> str:
        """
        Generate a replacement message for a cleaned tool result.
        
        Args:
            tool_name: Name of the tool that was called
            
        Returns:
            Replacement message string
        """
        if tool_name and tool_name != "unknown":
            return (f"<tool_result tool_name='{tool_name}' success='true'>"
                   f"<message>Content cleared to save tokens</message>"
                   f"<content>{self.replacement_message}</content>"
                   f"</tool_result>")
        else:
            return f"<tool_result success='true'><message>[Content cleared to save tokens, you can call the tool again to get the tool result.]</message><content>{self.replacement_message}</content></tool_result>"

    def get_cleanup_statistics(self, original_conversations: List[Dict[str, Any]], 
                              pruned_conversations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get statistics about the cleanup process.
        
        Args:
            original_conversations: Original conversation list
            pruned_conversations: Pruned conversation list
            
        Returns:
            Dictionary with cleanup statistics
        """
        original_tokens = count_tokens(json.dumps(original_conversations, ensure_ascii=False))
        pruned_tokens = count_tokens(json.dumps(pruned_conversations, ensure_ascii=False))
        
        # Count cleaned tool results
        cleaned_count = 0
        for orig, pruned in zip(original_conversations, pruned_conversations):
            if (orig.get("role") == "user" and 
                self._is_tool_result_message(orig.get("content", "")) and
                orig.get("content") != pruned.get("content")):
                cleaned_count += 1
        
        return {
            "original_tokens": original_tokens,
            "pruned_tokens": pruned_tokens,
            "tokens_saved": original_tokens - pruned_tokens,
            "compression_ratio": pruned_tokens / original_tokens if original_tokens > 0 else 1.0,
            "tool_results_cleaned": cleaned_count,
            "total_messages": len(original_conversations)
        } 