import os
import shutil
from typing import List
import time
from pathlib import Path
from loguru import logger

from autocoder.common import AutoCoderArgs
from autocoder.rag.cache.local_duckdb_storage_cache import LocalDuckDBStorageCache
from autocoder.utils.llms import get_single_llm
from autocoder.rag.variable_holder import VariableHolder
from tokenizers import Tokenizer
import pkg_resources

from autocoder.helper.rag_doc_creator import create_sample_files

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


def main():
    # 设置基本目录
    base_dir = "sample_code"    
    
    # 创建示例代码文件
    create_sample_files(base_dir)
    
    # 配置参数
    args = AutoCoderArgs(
        source_dir=base_dir,
        conversation_prune_safe_zone_tokens=4000,
        rag_duckdb_vector_dim=None,  # 使用默认的嵌入维度
        rag_duckdb_query_similarity=0.1,  # 向量搜索相似度阈值
        rag_duckdb_query_top_k=20,        # 返回的最多相似文档数
        hybrid_index_max_output_tokens=10000,  # 最大输出token数        
    )
    
    # 获取LLM实例
    logger.info("初始化LLM...")
    llm = get_single_llm("quasar-alpha", product_mode="lite")

    emb_llm = get_single_llm("emb2", product_mode="lite")
    
    # 创建忽略规则    
    required_exts = [".py"]  # 只处理Python文件
    
    # 初始化缓存管理器
    logger.info(f"初始化DuckDB缓存管理器...")
    cache_manager = LocalDuckDBStorageCache(
        args=args,
        llm = llm,
        path=base_dir,
        ignore_spec=None,
        required_exts=required_exts,
        extra_params=args,
        emb_llm=emb_llm
    )
    
    # 构建缓存
    logger.info("开始构建缓存...")
    cache_manager.build_cache()
    
    # 执行查询示例
    queries = [
        "如何计算数字的平均值",
        "如何处理字符串反转",
        "计算器中的加法和减法函数"
    ]
    
    for query in queries:
        logger.info(f"\n开始查询: '{query}'")
        results = cache_manager.get_cache({"queries": [query], "enable_vector_search": True})
        
        logger.info(f"查询 '{query}' 返回了 {len(results)} 个结果:")
        for file_path, file_info in results.items():
            logger.info(f"文件: {file_path}")
            for doc in file_info['content']:
                source_code = doc['source_code']
                # 只显示前200个字符作为预览
                preview = source_code[:200] + ('...' if len(source_code) > 200 else '')
                logger.info(f"代码预览: {preview}")
        
        time.sleep(1)  # 间隔查询
    
    # 测试文件更新
    logger.info("\n测试文件更新功能...")
    updated_content = """
class Calculator:
    def __init__(self):
        self.history = []
        self.version = "2.0"  # 添加了版本信息
        
    def add(self, a: int, b: int) -> int:
        '''改进的加法函数'''
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
        
    def subtract(self, a: int, b: int) -> int:
        '''改进的减法函数'''
        result = a - b
        self.history.append(f"{a} - {b} = {result}")
        return result
        
    def multiply(self, a: int, b: int) -> int:
        '''乘法函数'''
        result = a * b
        self.history.append(f"{a} * {b} = {result}")
        return result
        
    def divide(self, a: int, b: int) -> float:
        '''除法函数'''
        if b == 0:
            raise ValueError("Cannot divide by zero")
        result = a / b
        self.history.append(f"{a} / {b} = {result}")
        return result
        
    def power(self, a: int, b: int) -> int:
        '''新增: 幂运算'''
        result = a ** b
        self.history.append(f"{a} ** {b} = {result}")
        return result
"""
    
    # 更新计算器文件
    with open(os.path.join(base_dir, "calculator.py"), "w", encoding="utf-8") as f:
        f.write(updated_content)
    
    logger.info("已更新计算器文件，触发缓存更新...")
    # 触发更新
    cache_manager.trigger_update()
    
    # 等待更新完成
    time.sleep(2)
    
    # 再次查询
    query = "计算器中的幂运算功能"
    logger.info(f"\n测试更新后查询: '{query}'")
    results = cache_manager.get_cache({"queries": [query], "enable_vector_search": True})
    
    logger.info(f"查询 '{query}' 返回了 {len(results)} 个结果:")
    for file_path, file_info in results.items():
        logger.info(f"文件: {file_path}")
        for doc in file_info['content']:
            source_code = doc['source_code']
            # 只显示前200个字符作为预览
            preview = source_code[:200] + ('...' if len(source_code) > 200 else '')
            logger.info(f"代码预览: {preview}")
    
    # 清理测试文件
    # logger.info("\n清理测试文件...")
    # if os.path.exists(base_dir):
    #     shutil.rmtree(base_dir)
    
    logger.info("演示完成!")


if __name__ == "__main__":
    main() 