from byzerllm import ByzerLLM,SimpleByzerLLM
from typing import Generator, List, Any, Union, Optional, Callable
from pydantic import BaseModel
from loguru import logger
from autocoder.common import AutoCoderArgs
from autocoder.common.auto_coder_lang import get_message_with_format

class ChatWithContinueResult(BaseModel):
    content: str
    input_tokens_count: int
    generated_tokens_count: int
    

def chat_with_continue(
        llm: Union[ByzerLLM,SimpleByzerLLM], 
        conversations: List[dict], 
        llm_config: dict,
        args: AutoCoderArgs
    ) -> ChatWithContinueResult:
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

    if count >= args.generate_max_rounds:
        warning_message = get_message_with_format(
            "generate_max_rounds_reached",
            count=count,
            max_rounds=args.generate_max_rounds,
            generated_tokens=final_result.generated_tokens_count
        )
        logger.warning(warning_message)        
    
    # if count >= 2:
    #   logger.info(f"The code generation is exceed the max length, continue to generate the code {count -1 } times")
    final_result.content = single_result    
    return final_result

def stream_chat_with_continue(
    llm: Union[ByzerLLM, SimpleByzerLLM], 
    conversations: List[dict], 
    llm_config: dict,
    args: AutoCoderArgs
) -> Generator[Any, None, None]:
    """
    流式处理并继续生成内容，直到完成。
    
    Args:
        llm (Union[ByzerLLM, SimpleByzerLLM]): LLM实例
        conversations (List[dict]): 对话历史
        llm_config (dict): LLM配置参数
        

    """
    
    count = 0
    temp_conversations = [] + conversations
    current_metadata = None
    metadatas = {}
    while True:
        # 使用流式接口获取生成内容
        stream_generator = llm.stream_chat_oai(
            conversations=temp_conversations,
            delta_mode=True,
            llm_config={**llm_config, "gen.response_prefix": True if count > 0 else False}
        )
        
        current_content = ""        
        
        for res in stream_generator:
            content = res[0]
            current_content += content 
            if current_metadata is None:
                current_metadata = res[1]      
                metadatas[count] = res[1]      
            else:
                metadatas[count] = res[1]                
                current_metadata.finish_reason = res[1].finish_reason     
                current_metadata.reasoning_content = res[1].reasoning_content           
            
            # Yield 当前的 StreamChatWithContinueResult
            current_metadata.generated_tokens_count = sum([v.generated_tokens_count for _, v in metadatas.items()])
            current_metadata.input_tokens_count = sum([v.input_tokens_count for _, v in metadatas.items()])            
            yield (content,current_metadata)
        
        # 更新对话历史
        temp_conversations.append({"role": "assistant", "content": current_content})
        
        # 检查是否需要继续生成
        if current_metadata.finish_reason != "length" or count >= args.generate_max_rounds:
            if count >= args.generate_max_rounds:
                warning_message = get_message_with_format(
                    "generate_max_rounds_reached",
                    count=count,
                    max_rounds=args.generate_max_rounds,
                    generated_tokens=current_metadata.generated_tokens_count
                )
                logger.warning(warning_message)
            break
        
        
        count += 1
