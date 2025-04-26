
---
description: Token计数服务实现标准
globs: ["**/token_*.py"]
alwaysApply: false
---

# Token计数服务标准实现

## 简要说明
提供多种Token计数实现方案，包括本地计数、远程计数和多进程计数。适用于需要精确计算文本token数量的场景，如LLM API调用成本控制、文本处理长度限制等。

## 典型用法

```python
# 基础实现
from tokenizers import Tokenizer
from loguru import logger

def initialize_tokenizer(tokenizer_path):
    """初始化全局tokenizer"""
    global tokenizer_model    
    tokenizer_model = Tokenizer.from_file(tokenizer_path)

def count_tokens(text: str) -> int:       
    """基础token计数实现"""
    try:
        encoded = tokenizer_model.encode(text)
        return len(encoded.ids)
    except Exception as e:        
        logger.error(f"Token计数错误: {str(e)}")
        return -1

# 远程计数服务
class RemoteTokenCounter:
    def __init__(self, llm_client) -> None:
        """通过LLM客户端远程计数"""
        self.llm_client = llm_client

    def count_tokens(self, text: str) -> int:
        try:
            response = self.llm_client.chat_oai(
                conversations=[{"role": "user", "content": text}]
            )
            return int(response[0].output)
        except Exception as e:
            logger.error(f"远程Token计数错误: {str(e)}")
            return -1

# 多进程计数服务
from multiprocessing import Pool, cpu_count

class TokenCounter:
    def __init__(self, tokenizer_path: str):
        """多进程token计数"""
        self.tokenizer_path = tokenizer_path
        self.num_processes = max(1, cpu_count() - 1)
        self.pool = Pool(
            processes=self.num_processes,
            initializer=initialize_tokenizer,
            initargs=(self.tokenizer_path,),
        )

    def count_tokens(self, text: str) -> int:
        """多进程计数入口"""
        return self.pool.apply(_count_tokens_worker, (text,))

def _count_tokens_worker(text: str) -> int:
    """多进程工作函数"""
    try:
        encoded = tokenizer_model.encode(text)
        return len(encoded.ids)
    except Exception as e:
        logger.error(f"多进程Token计数错误: {str(e)}")
        return -1
```

## 依赖说明
- `tokenizers`: 核心token计数库 (`pip install tokenizers`)
- `loguru`: 日志记录 (`pip install loguru`)
- 多进程版本需要Python标准库`multiprocessing`
- 远程计数版本需要LLM客户端配置

## 最佳实践
1. 对于高频小文本，使用基础实现
2. 对于大文本批量处理，使用多进程版本
3. 需要与LLM服务token计数一致时，使用远程版本
4. 生产环境建议添加性能监控:
```python
start = time.time()
token_count = counter.count_tokens(text)
logger.info(f"计数耗时: {time.time()-start:.2f}s, tokens: {token_count}")
```

## 学习来源
从`/Users/allwefantasy/projects/auto-coder/src/autocoder/rag/token_counter.py`模块提取，参考了quick_filter.py中的使用方式。
