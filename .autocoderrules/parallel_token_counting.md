
---
description: 使用 multiprocessing.Pool 并行计算 Token 数量
globs: ["src/utils/token_utils.py", "*/token_counter.py"]
alwaysApply: false
---

# 使用 multiprocessing.Pool 并行化 Token 计算

## 简要说明
本规则展示了如何使用 Python 的 `multiprocessing.Pool` 结合 `tokenizers` 库来并行计算文本的 Token 数量。通过初始化函数在每个工作进程中加载 Tokenizer 模型，避免了重复加载的开销，适用于需要高效处理大量文本 Token 计算的场景。

## 典型用法
```python
import os
from multiprocessing import Pool, cpu_count
from tokenizers import Tokenizer
from loguru import logger

# 全局变量，用于在工作进程中存储 Tokenizer 模型
tokenizer_model = None

def initialize_worker_tokenizer(tokenizer_path: str):
    """
    工作进程初始化函数：加载 Tokenizer 模型。
    确保只在每个子进程启动时加载一次。
    """
    global tokenizer_model
    try:
        # 检查 tokenizer_path 是否为有效文件
        if not os.path.isfile(tokenizer_path):
            raise ValueError(f"Tokenizer file not found at path: {tokenizer_path}")
        tokenizer_model = Tokenizer.from_file(tokenizer_path)
        logger.info(f"Worker process {os.getpid()} initialized tokenizer.")
    except Exception as e:
        logger.error(f"Failed to initialize tokenizer in worker {os.getpid()}: {e}")
        # 如果初始化失败，可以选择设置 tokenizer_model 为 None 或引发异常
        tokenizer_model = None


def count_tokens_in_worker(text: str) -> int:
    """
    在工作进程中执行的 Token 计算函数。
    使用已初始化的全局 tokenizer_model。
    """
    global tokenizer_model
    if tokenizer_model is None:
        logger.error(f"Tokenizer not initialized in worker {os.getpid()}. Cannot count tokens.")
        return -1 # 或者抛出异常

    try:
        # 实际的 Token 计算逻辑 (根据需要调整，例如是否需要添加特殊标记)
        # encoded = tokenizer_model.encode('{"role":"user","content":"' + text + '"}') # 示例：特定格式
        encoded = tokenizer_model.encode(text) # 示例：通用格式
        return len(encoded.ids)
    except Exception as e:
        logger.error(f"Error counting tokens in worker {os.getpid()}: {e}")
        return -1


class ParallelTokenCounter:
    """
    使用 multiprocessing.Pool 并行计算 Token 的类。
    """
    def __init__(self, tokenizer_path: str, num_processes: int = None):
        """
        初始化 ParallelTokenCounter。

        Args:
            tokenizer_path (str): Tokenizer 模型文件的路径。
            num_processes (int, optional): 要使用的进程数。默认为 cpu_count() - 1。
        """
        if not os.path.isfile(tokenizer_path):
            raise ValueError(f"Invalid tokenizer file path: {tokenizer_path}")
        self.tokenizer_path = tokenizer_path

        # 合理设置进程数，避免超过CPU核心数过多
        max_processes = cpu_count()
        if num_processes is None:
            self.num_processes = max(1, max_processes - 1)
        else:
            self.num_processes = min(max(1, num_processes), max_processes)

        logger.info(f"Initializing multiprocessing pool with {self.num_processes} processes.")
        # 创建进程池，并指定初始化函数和参数
        self.pool = Pool(
            processes=self.num_processes,
            initializer=initialize_worker_tokenizer,
            initargs=(self.tokenizer_path,),
        )
        logger.info("Multiprocessing pool initialized.")

    def count_tokens_parallel(self, texts: list[str]) -> list[int]:
        """
        并行计算多个文本的 Token 数量。

        Args:
            texts (list[str]): 待计算的文本列表。

        Returns:
            list[int]: 每个文本对应的 Token 数量列表，顺序与输入一致。
                       如果某个文本计算出错，对应位置可能为 -1。
        """
        if not self.pool:
            raise RuntimeError("Processing pool is not initialized or has been closed.")

        try:
            # 使用 map 方法将任务分配给工作进程
            # map 会阻塞直到所有结果返回，并保持原始顺序
            results = self.pool.map(count_tokens_in_worker, texts)
            return results
        except Exception as e:
            logger.error(f"Error during parallel token counting: {e}")
            # 可以选择返回部分结果或全部标记为错误
            return [-1] * len(texts)

    def count_single_token(self, text: str) -> int:
        """
        计算单个文本的 Token 数量（利用进程池中的一个进程）。

        Args:
            text (str): 待计算的文本。

        Returns:
            int: Token 数量，出错时为 -1。
        """
        if not self.pool:
             raise RuntimeError("Processing pool is not initialized or has been closed.")
        # 使用 apply_async 或 map 都可以，这里用 map 保持接口一致性
        result = self.pool.map(count_tokens_in_worker, [text])
        return result[0] if result else -1


    def close_pool(self):
        """
        关闭进程池，释放资源。
        """
        if self.pool:
            logger.info("Closing multiprocessing pool.")
            self.pool.close() # 阻止新任务提交
            self.pool.join()  # 等待所有任务完成
            self.pool = None
            logger.info("Multiprocessing pool closed.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close_pool()

# --- 调用示例 ---
if __name__ == "__main__":
    # 配置日志
    logger.add("parallel_token_counter.log", rotation="10 MB")

    # 假设 tokenizer 模型文件存在于 'path/to/your/tokenizer.json'
    # 请替换为实际路径
    tokenizer_file = "path/to/your/tokenizer.json" # <--- 修改这里

    if not os.path.exists(tokenizer_file):
         logger.error(f"Tokenizer file '{tokenizer_file}' not found. Please provide a valid path.")
         # 可以尝试创建虚拟文件用于测试，但实际使用需要真实模型
         # os.makedirs(os.path.dirname(tokenizer_file), exist_ok=True)
         # with open(tokenizer_file, "w") as f:
         #     f.write('{"version": "1.0", "truncation": null, "padding": null, "added_tokens": [], "normalizer": null, "pre_tokenizer": null, "post_processor": null, "decoder": null, "model": {"type": "WordLevel", "vocab": {"[UNK]": 0, "hello": 1, "world": 2}, "unk_token": "[UNK]"}}')
         # logger.warning("Created a dummy tokenizer file for demonstration.")
    else:
        texts_to_count = [
            "This is the first document.",
            "这是一个示例文档。",
            "A slightly longer document with more words.",
            "エラーが発生しました。",
            "Short one.",
        ] * 10 # 模拟大量文本

        try:
            # 使用 'with' 语句确保进程池被正确关闭
            with ParallelTokenCounter(tokenizer_path=tokenizer_file) as counter:
                logger.info("Starting parallel token counting...")
                start_time = time.time()
                token_counts = counter.count_tokens_parallel(texts_to_count)
                end_time = time.time()
                logger.info(f"Parallel counting took {end_time - start_time:.4f} seconds.")

                # 打印部分结果
                for i in range(min(5, len(texts_to_count))):
                    logger.info(f"Text: '{texts_to_count[i]}' - Tokens: {token_counts[i]}")

                # 测试单个文本计数
                single_text = "Count this single text."
                single_count = counter.count_single_token(single_text)
                logger.info(f"Single Text: '{single_text}' - Tokens: {single_count}")

        except ValueError as ve:
             logger.error(f"Initialization failed: {ve}")
        except RuntimeError as re:
             logger.error(f"Runtime error: {re}")
        except Exception as e:
             logger.error(f"An unexpected error occurred: {e}")
```

## 依赖说明
- `tokenizers`: Hugging Face 的 Tokenizers 库。(`pip install tokenizers`)
- `loguru`: 用于日志记录 (推荐)。(`pip install loguru`)
- Python 标准库: `multiprocessing`, `os`, `time`
- 需要一个有效的 `tokenizers` 模型文件 (例如 `.json` 格式)。

## 学习来源
从 `/Users/allwefantasy/projects/auto-coder/src/autocoder/rag/token_counter.py` 文件中的 `TokenCounter` 类、`initialize_tokenizer` 和 `count_tokens_worker` 函数提取。该实现展示了如何通过 `multiprocessing.Pool` 和 `initializer` 有效地并行化 Token 计算任务。
