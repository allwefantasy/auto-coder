import time
from loguru import logger
from tokenizers import Tokenizer
from multiprocessing import Pool, cpu_count
from functools import partial

def initialize_tokenizer(tokenizer_path: str):
    global model
    model = Tokenizer.from_file(tokenizer_path)

def count_tokens(text: str) -> int:
    try:
        start_time = time.time_ns()
        encoded = model.encode('{"role":"user","content":"'+text+'"}')
        v = len(encoded.input_ids)
        elapsed_time = time.time_ns() - start_time
        logger.info(f"Token counting took {elapsed_time/1000000} ms")
        return v
    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}")
        return -1

def parallel_count_tokens(texts: list[str], tokenizer_path: str) -> list[int]:
    num_processes = cpu_count()-1 if cpu_count() > 1 else 1
    with Pool(processes=num_processes, initializer=initialize_tokenizer, initargs=(tokenizer_path,)) as pool:
        results = pool.map(count_tokens, texts)
    return results