from byzerllm import ByzerLLM
from typing import List


def chat_with_continue(llm: ByzerLLM, conversations: List[dict], llm_config: dict) -> str:
    v = llm.chat_oai(
        conversations=conversations, llm_config=llm_config)

    single_result = v[0].output
    metadata = v[0].metadata
    temp_conversations = conversations + \
        [{"role": "assistant", "content": single_result}]
    while (metadata.get("finish_reason", "stop") == "length"):
        v = llm.chat_oai(
            conversations=temp_conversations, llm_config={**llm_config, "gen.response_prefix": True})
        metadata = v[0].metadata
        single_result += v[0].output

    return single_result
