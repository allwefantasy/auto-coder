from byzerllm import ByzerLLM
from typing import List,Any,Union
from pydantic import BaseModel

class ChatWithContinueResult(BaseModel):
    content: str
    input_tokens_count: int
    generated_tokens_count: int
    

def chat_with_continue(llm: ByzerLLM, conversations: List[dict], llm_config: dict) -> ChatWithContinueResult:
    final_result = ChatWithContinueResult(content="", input_tokens_count=0, generated_tokens_count=0)
    v = llm.chat_oai(
        conversations=conversations, llm_config=llm_config)
                
    single_result = v[0].output
    metadata = v[0].metadata

    final_result.input_tokens_count += metadata.get("input_tokens_count", 0)
    final_result.generated_tokens_count += metadata.get("generated_tokens_count", 0)

    temp_conversations = conversations + \
        [{"role": "assistant", "content": single_result}]
    while (metadata.get("finish_reason", "stop") == "length"):
        v = llm.chat_oai(
            conversations=temp_conversations, llm_config={**llm_config, "gen.response_prefix": True})
        metadata = v[0].metadata
        single_result += v[0].output
        final_result.input_tokens_count += metadata.get("input_tokens_count", 0)
        final_result.generated_tokens_count += metadata.get("generated_tokens_count", 0)

    final_result.content = single_result    
    return final_result
