from byzerllm import ByzerLLM,SimpleByzerLLM
from typing import Generator, List, Any, Union
from pydantic import BaseModel
from loguru import logger

class StreamChatWithContinueResult(BaseModel):
    content: str
    input_tokens_count: int
    generated_tokens_count: int
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

def stream_chat_with_continue(
    llm: Union[ByzerLLM, SimpleByzerLLM], 
    conversations: List[dict], 
    llm_config: dict
) -> Generator[StreamChatWithContinueResult, None, None]:
    """
    流式处理并继续生成内容，直到完成。
    
    Args:
        llm (Union[ByzerLLM, SimpleByzerLLM]): LLM实例
        conversations (List[dict]): 对话历史
        llm_config (dict): LLM配置参数
        
    Yields:
        StreamChatWithContinueResult: 包含当前生成的内容和元数据的结果对象
    """
    final_result = {
        "content": "",
        "input_tokens_count": 0,
        "generated_tokens_count": 0
    }
    
    count = 0
    temp_conversations = conversations
    
    while True:
        # 使用流式接口获取生成内容
        stream_generator = llm.stream_chat_oai(
            conversations=temp_conversations,
            llm_config={**llm_config, "gen.response_prefix": True if count > 0 else False}
        )
        
        current_content = ""
        for res in stream_generator:
            content = res[0]
            current_content += content
            
            # 更新最终结果
            final_result["content"] += content
            metadata = getattr(stream_generator, 'metadata', {})
            final_result["input_tokens_count"] += metadata.get("input_tokens_count", 0)
            final_result["generated_tokens_count"] += metadata.get("generated_tokens_count", 0)
            
            # Yield 当前的 StreamChatWithContinueResult
            yield StreamChatWithContinueResult(
                content=final_result["content"],
                input_tokens_count=final_result["input_tokens_count"],
                generated_tokens_count=final_result["generated_tokens_count"]
            )
        
        # 更新对话历史
        temp_conversations.append({"role": "assistant", "content": current_content})
        
        # 检查是否需要继续生成
        metadata = getattr(stream_generator, 'metadata', {})
        if metadata.get("finish_reason", "stop") != "length" or count >= 5:
            break
        
        count += 1
