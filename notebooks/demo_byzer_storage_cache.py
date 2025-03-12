import os
import shutil
from typing import List
import time
from pathlib import Path
from loguru import logger

from autocoder.common import AutoCoderArgs
from autocoder.rag.cache.local_byzer_storage_cache import LocalByzerStorageCache
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
    """创建示例代码文件用于演示"""
    # 创建目录
    os.makedirs(base_dir, exist_ok=True)
    
    # 示例文件1 - 计算器类
    calculator_content = """
class Calculator:
    def __init__(self):
        self.history = []
        
    def add(self, a: int, b: int) -> int:
        '''加法函数'''
        result = a + b
        self.history.append(f"{a} + {b} = {result}")
        return result
        
    def subtract(self, a: int, b: int) -> int:
        '''减法函数'''
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
"""
    
    # 示例文件2 - 字符串处理类
    string_processor_content = """
class StringProcessor:
    @staticmethod
    def reverse(text: str) -> str:
        '''反转字符串'''
        return text[::-1]
    
    @staticmethod
    def capitalize(text: str) -> str:
        '''首字母大写'''
        return text.capitalize()
    
    @staticmethod
    def count_words(text: str) -> int:
        '''计算单词数量'''
        return len(text.split())
    
    @staticmethod
    def format_name(first_name: str, last_name: str) -> str:
        '''格式化姓名'''
        return f"{last_name}, {first_name}"
"""
    
    # 示例文件3 - 数据处理类
    data_processor_content = """
import statistics
from typing import List, Dict, Any

class DataProcessor:
    @staticmethod
    def calculate_average(numbers: List[float]) -> float:
        '''计算平均值'''
        return sum(numbers) / len(numbers)
    
    @staticmethod
    def find_median(numbers: List[float]) -> float:
        '''计算中位数'''
        sorted_numbers = sorted(numbers)
        n = len(sorted_numbers)
        if n % 2 == 0:
            return (sorted_numbers[n//2-1] + sorted_numbers[n//2]) / 2
        else:
            return sorted_numbers[n//2]
    
    @staticmethod
    def find_mode(numbers: List[float]) -> List[float]:
        '''查找众数'''
        try:
            return statistics.mode(numbers)
        except statistics.StatisticsError:
            # 没有唯一众数的情况
            count_dict = {}
            for num in numbers:
                if num in count_dict:
                    count_dict[num] += 1
                else:
                    count_dict[num] = 1
            max_count = max(count_dict.values())
            return [num for num, count in count_dict.items() if count == max_count]
"""
    
    # 写入文件
    with open(os.path.join(base_dir, "calculator.py"), "w", encoding="utf-8") as f:
        f.write(calculator_content)
    
    with open(os.path.join(base_dir, "string_processor.py"), "w", encoding="utf-8") as f:
        f.write(string_processor_content)
    
    with open(os.path.join(base_dir, "data_processor.py"), "w", encoding="utf-8") as f:
        f.write(data_processor_content)
    
    logger.info(f"示例代码文件已创建在: {base_dir}")


def main():
    # 设置基本目录
    base_dir = "sample_code_byzer"    
    
    # 创建示例代码文件
    create_sample_files(base_dir)
    
    # 配置参数
    args = AutoCoderArgs(
        source_dir=base_dir,
        conversation_prune_safe_zone_tokens=4000,
        rag_build_name="demo_cache",  # Byzer Storage需要的索引名称
        hybrid_index_max_output_tokens=10000,  # 最大输出token数        
    )
    
    # 获取LLM实例
    logger.info("初始化LLM...")
    llm = get_single_llm("v3_chat", product_mode="lite")
    emb_llm = get_single_llm("emb2", product_mode="lite")
    
    # 创建忽略规则    
    required_exts = [".py"]  # 只处理Python文件
    
    # 初始化缓存管理器
    logger.info(f"初始化Byzer Storage缓存管理器...")
    host = "127.0.0.1"  # Byzer Storage服务地址
    port = 33333        # Byzer Storage服务端口
    
    cache_manager = LocalByzerStorageCache(
        path=base_dir,
        ignore_spec=None,
        required_exts=required_exts,
        extra_params=args,
        emb_llm=emb_llm,
        host=host,
        port=port
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
    
    # 单个查询示例
    for query in queries:
        logger.info(f"\n开始单个查询: '{query}'")
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
    
    # 多查询合并示例
    logger.info("\n开始多查询合并测试...")
    multi_query_results = cache_manager.get_cache({
        "queries": ["计算平均值和中位数", "字符串处理函数"],
        "merge_strategy": "WEIGHTED_RANK",  # 使用加权排名策略合并结果
        "max_results": 5,  # 限制返回结果数量
        "enable_vector_search": True
    })
    
    logger.info(f"多查询合并返回了 {len(multi_query_results)} 个结果:")
    for file_path, file_info in multi_query_results.items():
        logger.info(f"文件: {file_path}")
        for doc in file_info['content']:
            source_code = doc['source_code']
            # 只显示前200个字符作为预览
            preview = source_code[:200] + ('...' if len(source_code) > 200 else '')
            logger.info(f"代码预览: {preview}")
    
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
    logger.info("等待更新处理完成...")
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
    
    # 演示结合文本搜索和向量搜索
    logger.info("\n测试混合搜索功能...")
    hybrid_results = cache_manager.get_cache({
        "queries": ["计算功能"],
        "enable_vector_search": True,
        "enable_text_search": True
    })
    
    logger.info(f"混合搜索返回了 {len(hybrid_results)} 个结果:")
    for file_path, file_info in hybrid_results.items():
        logger.info(f"文件: {file_path}")
        for doc in file_info['content']:
            source_code = doc['source_code']
            # 只显示前200个字符作为预览
            preview = source_code[:200] + ('...' if len(source_code) > 200 else '')
            logger.info(f"代码预览: {preview}")
    
    # 不清理测试文件，以便查看结果
    # logger.info("\n清理测试文件...")
    # if os.path.exists(base_dir):
    #     shutil.rmtree(base_dir)
    
    logger.info("演示完成!")


if __name__ == "__main__":
    main() 