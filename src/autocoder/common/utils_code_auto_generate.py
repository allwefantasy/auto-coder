from byzerllm import ByzerLLM,SimpleByzerLLM
from typing import List,Any,Union
from pydantic import BaseModel
from loguru import logger
class ChatWithContinueResult(BaseModel):
    content: str
    input_tokens_count: int
    generated_tokens_count: int
    

def chat_with_continue(llm: Union[ByzerLLM,SimpleByzerLLM], conversations: List[dict], llm_config: dict) -> ChatWithContinueResult:
    final_result = ChatWithContinueResult(content="", input_tokens_count=0, generated_tokens_count=0)
    v = llm.chat_oai(
        conversations=conversations, llm_config=llm_config)
                
    single_result = v[0].output
    metadata = v[0].metadata

    final_result.input_tokens_count += metadata.get("input_tokens_count", 0)
    final_result.generated_tokens_count += metadata.get("generated_tokens_count", 0)

    temp_conversations = conversations + \
        [{"role": "assistant", "content": single_result}]
    
    count = 1
    while (metadata.get("finish_reason", "stop") == "length" and count < 6):        
        v = llm.chat_oai(
            conversations=temp_conversations, llm_config={**llm_config, "gen.response_prefix": True})
        metadata = v[0].metadata
        single_result += v[0].output
        final_result.input_tokens_count += metadata.get("input_tokens_count", 0)
        final_result.generated_tokens_count += metadata.get("generated_tokens_count", 0)
        count += 1
    
    # if count >= 2:
    #   logger.info(f"The code generation is exceed the max length, continue to generate the code {count -1 } times")
    final_result.content = single_result    
    return final_result
