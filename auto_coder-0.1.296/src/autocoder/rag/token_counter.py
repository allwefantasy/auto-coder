import time
from loguru import logger
from tokenizers import Tokenizer
from multiprocessing import Pool, cpu_count
from autocoder.rag.variable_holder import VariableHolder


class RemoteTokenCounter:
    def __init__(self, tokenizer) -> None:
        self.tokenizer = tokenizer

    def count_tokens(self, text: str) -> int:
        try:
            v = self.tokenizer.chat_oai(
                conversations=[{"role": "user", "content": text}]
            )
            return int(v[0].output)
        except Exception as e:
            logger.error(f"Error counting tokens: {str(e)}")
            return -1


def initialize_tokenizer(tokenizer_path):
    global tokenizer_model    
    tokenizer_model = Tokenizer.from_file(tokenizer_path)


def count_tokens(text: str) -> int:       
    try:
        # start_time = time.time_ns()
        encoded = VariableHolder.TOKENIZER_MODEL.encode('{"role":"user","content":"' + text + '"}')
        v = len(encoded.ids)
        # elapsed_time = time.time_ns() - start_time
        # logger.info(f"Token counting took {elapsed_time/1000000} ms")
        return v
    except Exception as e:        
        logger.error(f"Error counting tokens: {str(e)}")
        return -1


def count_tokens_worker(text: str) -> int:
    try:
        # start_time = time.time_ns()
        encoded = tokenizer_model.encode('{"role":"user","content":"' + text + '"}')
        v = len(encoded.ids)
        # elapsed_time = time.time_ns() - start_time
        # logger.info(f"Token counting took {elapsed_time/1000000} ms")
        return v
    except Exception as e:
        logger.error(f"Error counting tokens: {str(e)}")
        return -1


class TokenCounter:
    def __init__(self, tokenizer_path: str):
        self.tokenizer_path = tokenizer_path
        self.num_processes = cpu_count() - 1 if cpu_count() > 1 else 1
        self.pool = Pool(
            processes=self.num_processes,
            initializer=initialize_tokenizer,
            initargs=(self.tokenizer_path,),
        )

    def count_tokens(self, text: str) -> int:
        return self.pool.apply(count_tokens_worker, (text,))
