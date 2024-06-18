from byzerllm.utils.client import EventCallbackResult,EventName
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import FormattedText
from typing import List,Dict,Any
from loguru import logger
from autocoder.db.store import Store


def token_counter_interceptor(llm,model,response) -> EventCallbackResult: 
    store = Store()
    v = response[0]     
    if "metadata" in v:
        metadata = v["metadata"]
        input_tokens_count = metadata.get("input_tokens_count",0)
        generated_tokens_count = metadata.get("generated_tokens_count",0)
        # logger.info(f"{model} consume Input tokens count: {input_tokens_count}, Generated tokens count: {generated_tokens_count}")
        store.update_token_counter(project=None,input_tokens_count=input_tokens_count,generated_tokens_count = generated_tokens_count)
    return True,None    
        
                        

    