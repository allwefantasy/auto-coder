
from typing import List, Dict, Any
import byzerllm

def chat_with_prefix_completion(llm: byzerllm.ByzerLLM, conversations: List[Dict[str, Any]], 
                               llm_config: Dict[str, Any] = None) -> List[str]:
    """
    使用 Chat Prefix Completion 功能与 LLM 交互
    Args:
        llm: ByzerLLM 实例
        conversations: 对话历史
        llm_config: LLM 配置
    Returns:
        模型输出列表
    """
    if llm_config is None:
        llm_config = {}
    
    # 确保启用 response_prefix
    llm_config["gen.response_prefix"] = True
    
    results = []
    if not llm_config.get("human_as_model", False):
        with ThreadPoolExecutor(max_workers=len(llm.get_sub_client("code_model") or [llm])) as executor:
            futures = []
            for _ in range(llm_config.get("generate_times_same_model", 1)):
                futures.append(executor.submit(
                    llm.chat_oai, conversations=conversations, llm_config=llm_config))
            results = [future.result()[0].output for future in futures]
    else:
        for _ in range(llm_config.get("human_model_num", 1)):
            v = llm.chat_oai(conversations=conversations, llm_config=llm_config)
            single_result = v[0].output
            metadata = v[0].metadata
            temp_conversations = conversations + [{"role": "assistant", "content": single_result}]
            while metadata.get("finish_reason", "stop") == "length":
                v = llm.chat_oai(
                    conversations=temp_conversations, 
                    llm_config={**llm_config, "gen.response_prefix": True}
                )
                metadata = v[0].metadata
                single_result += v[0].output
            results.append(single_result)
    
    return results