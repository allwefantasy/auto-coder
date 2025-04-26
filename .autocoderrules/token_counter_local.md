
---
description: 使用 tokenizers 和 multiprocessing 高效本地统计文本Token数
globs: ["src/utils/token_utils.py", "*/token_counter.py"]
alwaysApply: false
---

# 本地Token计数器 (Local Token Counter)

## 简要说明
提供一个使用 `tokenizers` 库加载本地分词器模型文件，并利用 `multiprocessing` 并行计算文本Token数量的类。适用于需要在本地环境高效处理大量文本Token计数的场景，避免依赖外部API。

## 典型用法
```python
import os
import time
from loguru import logger
from tokenizers import Tokenizer
from multiprocessing import Pool, cpu_count
from typing import Optional

# 全局变量，用于在工作进程中持有分词器模型
tokenizer_model: Optional[Tokenizer] = None

def initialize_tokenizer(tokenizer_path: str):
    """
    初始化工作进程中的分词器模型。
    此函数由 multiprocessing.Pool 在每个工作进程启动时调用。
    """
    global tokenizer_model
    try:
        tokenizer_model = Tokenizer.from_file(tokenizer_path)
        logger.info(f"Worker process {os.getpid()} initialized tokenizer from {tokenizer_path}")
    except Exception as e:
        logger.error(f"Worker process {os.getpid()} failed to initialize tokenizer: {str(e)}")
        tokenizer_model = None # 确保失败时状态清晰

def count_tokens_worker(text: str) -> int:
    """
    在单个工作进程中计算文本的Token数量。
    """
    if tokenizer_model is None:
        logger.error(f"Worker process {os.getpid()}: Tokenizer not initialized.")
        return -1 # 或者抛出异常

    try:
        # 注意：这里的格式化可能需要根据具体模型调整
        # 示例格式：模拟 OpenAI 的 chat 格式输入
        formatted_text = '{"role":"user","content":"' + text + '"}'
        encoded = tokenizer_model.encode(formatted_text)
        return len(encoded.ids)
    except Exception as e:
        logger.error(f"Worker process {os.getpid()} error counting tokens: {str(e)}")
        return -1

class LocalTokenCounter:
    """
    使用多进程并行计算Token数量的计数器。
    """
    def __init__(self, tokenizer_path: str):
        """
        初始化Token计数器。

        Args:
            tokenizer_path (str): 本地分词器模型文件的路径 (例如: tokenizer.json)。
        """
        if not os.path.exists(tokenizer_path):
            raise FileNotFoundError(f"Tokenizer file not found at: {tokenizer_path}")

        self.tokenizer_path = tokenizer_path
        # 根据CPU核心数设置进程数，留一个核心给主进程或其他任务
        self.num_processes = max(1, cpu_count() - 1)
        self.pool = None
        self._initialize_pool()

    def _initialize_pool(self):
        """初始化进程池"""
        logger.info(f"Initializing multiprocessing pool with {self.num_processes} processes...")
        try:
            # initializer 在每个工作进程启动时调用 initialize_tokenizer
            # initargs 将 tokenizer_path 传递给 initializer
            self.pool = Pool(
                processes=self.num_processes,
                initializer=initialize_tokenizer,
                initargs=(self.tokenizer_path,),
            )
            logger.info("Multiprocessing pool initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize multiprocessing pool: {str(e)}")
            raise

    def count_tokens(self, text: str) -> int:
        """
        使用进程池计算单个文本的Token数量。

        Args:
            text (str): 需要计算Token的文本。

        Returns:
            int: Token数量，如果出错则返回-1。
        """
        if self.pool is None:
            logger.error("Processing pool is not initialized.")
            return -1 # 或者重新尝试初始化

        try:
            # 使用 apply_async 或 map 处理单个或多个任务
            # apply 在这里更简单，等待结果返回
            result = self.pool.apply(count_tokens_worker, (text,))
            return result
        except Exception as e:
            logger.error(f"Error during token counting task execution: {str(e)}")
            return -1

    def count_tokens_batch(self, texts: list[str]) -> list[int]:
        """
        使用进程池并行计算一批文本的Token数量。

        Args:
            texts (list[str]): 需要计算Token的文本列表。

        Returns:
            list[int]: 每个文本对应的Token数量列表，出错的位置为-1。
        """
        if self.pool is None:
            logger.error("Processing pool is not initialized.")
            return [-1] * len(texts)

        try:
            # 使用 map 并行处理列表中的所有文本
            results = self.pool.map(count_tokens_worker, texts)
            return results
        except Exception as e:
            logger.error(f"Error during batch token counting task execution: {str(e)}")
            return [-1] * len(texts)

    def shutdown(self):
        """关闭并清理进程池"""
        if self.pool:
            logger.info("Shutting down multiprocessing pool...")
            self.pool.close() # 不再接受新任务
            self.pool.join()  # 等待所有工作进程完成
            self.pool = None
            logger.info("Multiprocessing pool shut down.")

    def __del__(self):
        """确保在对象销毁时关闭进程池"""
        self.shutdown()

# --- 使用示例 ---
if __name__ == "__main__":
    # 假设在项目根目录下有一个名为 'tokenizer.json' 的分词器模型文件
    # 请替换为实际的分词器文件路径
    tokenizer_file = "path/to/your/tokenizer.json" # <--- 修改这里

    if not os.path.exists(tokenizer_file):
         logger.error(f"示例需要一个分词器文件，请将 '{tokenizer_file}' 替换为有效路径。")
         # 你可能需要下载一个分词器模型文件，例如从Hugging Face Hub
         # exit() # 如果没有分词器文件，可以退出或跳过示例
         # 为了演示，我们创建一个虚拟文件（实际使用中需要真实文件）
         try:
             os.makedirs(os.path.dirname(tokenizer_file), exist_ok=True)
             with open(tokenizer_file, "w") as f:
                 # 注意：这是一个无效的tokenizer内容，仅用于文件存在性检查
                 f.write('{"version": "1.0", "truncation": null, "padding": null, "added_tokens": [], "normalizer": null, "pre_tokenizer": null, "post_processor": null, "decoder": null, "model": {"type": "WordLevel", "vocab": {"[UNK]": 0, "hello": 1, "world": 2}, "unk_token": "[UNK]"}}')
             logger.warning(f"创建了一个虚拟的 tokenizer 文件于 {tokenizer_file} 供演示。请替换为真实的模型文件。")
         except Exception as e:
             logger.error(f"无法创建虚拟 tokenizer 文件: {e}")
             exit()

    try:
        logger.info("初始化 LocalTokenCounter...")
        counter = LocalTokenCounter(tokenizer_path=tokenizer_file)

        # 示例 1: 计算单个文本
        text1 = "这是一个用于测试的示例文本。"
        start_time = time.time()
        token_count1 = counter.count_tokens(text1)
        end_time = time.time()
        logger.info(f"文本: '{text1}'")
        logger.info(f"Token 数量: {token_count1} (耗时: {end_time - start_time:.4f} 秒)")

        # 示例 2: 计算一批文本
        texts_batch = [
            "这是第一个句子。",
            "这是第二个稍微长一点的句子。",
            "第三个句子来了。",
            "最后是一个非常非常非常非常长的句子，用来测试性能和并行处理的效果，看看多进程是否能带来速度提升。"
        ]
        start_time = time.time()
        token_counts_batch = counter.count_tokens_batch(texts_batch)
        end_time = time.time()
        logger.info("\n批量处理文本:")
        for i, text in enumerate(texts_batch):
            logger.info(f" - '{text[:30]}...' : {token_counts_batch[i]} Tokens")
        logger.info(f"批量处理耗时: {end_time - start_time:.4f} 秒")

        # 示例 3: 处理包含错误的文本（假设 worker 函数能捕获）
        # text_error = None # 传递 None 可能导致 worker 内部错误
        # token_count_error = counter.count_tokens(text_error)
        # logger.info(f"\n处理错误输入:")
        # logger.info(f"Token 数量 (错误): {token_count_error}")

        # 关闭进程池 (也可以依赖 __del__，但显式关闭更好)
        counter.shutdown()

    except FileNotFoundError as e:
        logger.error(e)
    except Exception as e:
        logger.error(f"运行示例时发生错误: {str(e)}")

    # [可选] 清理虚拟文件
    # if os.path.exists(tokenizer_file) and "虚拟" in open(tokenizer_file).read(100):
    #     os.remove(tokenizer_file)
```

## 依赖说明
-   `tokenizers`: 用于加载和使用本地分词器模型。 (`pip install tokenizers`)
-   `loguru` (可选, 用于示例日志): 提供更友好的日志记录。 (`pip install loguru`)
-   Python 标准库: `multiprocessing`, `os`, `time`, `typing`。
-   **环境要求**:
    -   需要一个有效的、由 `tokenizers` 库支持的本地分词器模型文件（通常是 `.json` 格式）。可以从 Hugging Face Hub 等来源下载。
    -   运行环境需要支持 `multiprocessing`。
-   **初始化流程**:
    -   创建 `LocalTokenCounter` 实例时，需要提供有效的分词器模型文件路径。
    -   进程池会在实例化时自动创建。
    -   建议在使用完毕后调用 `shutdown()` 方法显式关闭进程池，或依赖对象的垃圾回收自动关闭。

## 学习来源
从 `/Users/allwefantasy/projects/auto-coder/src/autocoder/rag/token_counter.py` 文件中的 `TokenCounter` 类、`initialize_tokenizer` 全局函数 和 `count_tokens_worker` 全局函数提取并整合优化。
