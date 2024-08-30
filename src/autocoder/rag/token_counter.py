import time
from loguru import logger
from tokenizers import Tokenizer
from multiprocessing import Pool, cpu_count

class TokenCounter:
    def __init__(self, tokenizer_path: str):
        self.tokenizer_path = tokenizer_path
        self.model = None
        self.num_processes = cpu_count() - 1 if cpu_count() > 1 else 1
        self.pool = None

    def initialize_tokenizer(self):
        if not self.model:
            self.model = Tokenizer.from_file(self.tokenizer_path)

    def count_tokens(self, text: str) -> int:
        try:
            start_time = time.time_ns()
            encoded = self.model.encode('{"role":"user","content":"'+text+'"}')
            v = len(encoded.input_ids)
            elapsed_time = time.time_ns() - start_time
            logger.info(f"Token counting took {elapsed_time/1000000} ms")
            return v
        except Exception as e:
            logger.error(f"Error counting tokens: {str(e)}")
            return -1

    def create_pool(self):
        if self.pool is None:
            self.pool = Pool(processes=self.num_processes, initializer=self.initialize_tokenizer)

    def close_pool(self):
        if self.pool is not None:
            self.pool.close()
            self.pool.join()
            self.pool = None

    def parallel_count_tokens(self, text: str) -> int:
        self.create_pool()
        result = self.pool.apply(self.count_tokens, (text,))
        return result

    def __del__(self):
        self.close_pool()