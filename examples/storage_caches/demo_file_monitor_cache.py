

import os
import time
from loguru import logger
from autocoder.common import AutoCoderArgs
from autocoder.rag.cache.file_monitor_cache import AutoCoderRAGDocListener
from autocoder.utils.llms import get_single_llm
from autocoder.rag.variable_holder import VariableHolder
from tokenizers import Tokenizer
import pkg_resources

# 初始化tokenizer
try:
    tokenizer_path = pkg_resources.resource_filename(
        "autocoder", "data/tokenizer.json"
    )
    VariableHolder.TOKENIZER_PATH = tokenizer_path
    VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(tokenizer_path)
except FileNotFoundError:
    logger.error("Tokenizer文件未找到，请确保autocoder正确安装")
    tokenizer_path = None


def create_sample_files(base_dir: str):
    os.makedirs(base_dir, exist_ok=True)
    
    calculator_content = """
class Calculator:
    def __init__(self):
        self.history = []
        
    def add(self, a: int, b: int) -> int:
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
        
    def subtract(self, a: int, b: int) -> int:
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        return result
        
    def multiply(self, a: int, b: int) -> int:
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
        
    def divide(self, a: int, b: int) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result
"""
    with open(os.path.join(base_dir, "calculator.py"), "w", encoding="utf-8") as f:
        f.write(calculator_content)

def main():
    base_dir = "sample_code_file_monitor_cache"
    create_sample_files(base_dir)
    
    args = AutoCoderArgs(
        source_dir=base_dir,
        conversation_prune_safe_zone_tokens=4000,
        rag_duckdb_vector_dim=None,
        rag_duckdb_query_similarity=0.1,
        rag_duckdb_query_top_k=20,
        hybrid_index_max_output_tokens=10000,
    )
    
    llm = get_single_llm("quasar-alpha", product_mode="lite")
    
    required_exts = [".py"]
    
    logger.info("初始化FileMonitorCache缓存管理器...")
    cache_manager = AutoCoderRAGDocListener(
        path=base_dir,
        ignore_spec=None,
        required_exts=required_exts,
        args=args,
        llm=llm
    )
    
    logger.info("等待缓存初始化...")
    time.sleep(2)
    
    logger.info("开始查询缓存内容...")
    cache = cache_manager.get_cache()
    logger.info(f"缓存中文件数: {len(cache)}")
    for file_path, file_info in cache.items():
        logger.info(f"文件: {file_path}")
        contents = file_info.get('content', [])
        for content in contents:
            preview = content.get('source_code', '')[:200]
            logger.info(f"代码预览: {preview}")
    
    # 测试更新
    updated_content = """
class Calculator:
    def __init__(self):
        self.history = []
        self.version = "2.0"
        
    def add(self, a: int, b: int) -> int:
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
        
    def subtract(self, a: int, b: int) -> int:
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        return result
        
    def multiply(self, a: int, b: int) -> int:
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
        
    def divide(self, a: int, b: int) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result

    def power(self, a: int, b: int) -> int:
        result = a ** b
        self.history.append(f"{a} ** {b} = {result}")
        return result
"""
    with open(os.path.join(base_dir, "calculator.py"), "w", encoding="utf-8") as f:
        f.write(updated_content)
    
    logger.info("已更新文件，等待监控线程自动更新缓存...")
    time.sleep(5)
    
    cache = cache_manager.get_cache()
    logger.info(f"增量更新后缓存文件数: {len(cache)}")
    for file_path, file_info in cache.items():
        logger.info(f"文件: {file_path}")
        contents = file_info.get('content', [])
        for content in contents:
            preview = content.get('source_code', '')[:200]
            logger.info(f"代码预览: {preview}")

    logger.info("FileMonitorCache演示完成。")

if __name__ == "__main__":
    main()

