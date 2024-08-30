import time
from loguru import logger
from byzerllm import ByzerLLM

def count_tokens(text: str, tokenizer: ByzerLLM) -> int:
    if tokenizer is None:
        return -1
    try:
        start_time = time.time_ns()
        v = tokenizer.chat_oai(
            conversations=[{"role": "user", "content": text}]
        )
        elapsed_time = time.time_ns() - start_time
        logger.info(f"Token counting took {elapsed_time/1000000} ms")
        return int(v[0].output)
    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}")
        return -1