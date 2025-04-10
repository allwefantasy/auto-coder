
import os
from loguru import logger

def create_sample_files(base_dir: str):
    """创建示例代码文件用于演示"""
    os.makedirs(base_dir, exist_ok=True)

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

    with open(os.path.join(base_dir, "calculator.py"), "w", encoding="utf-8") as f:
        f.write(calculator_content)

    with open(os.path.join(base_dir, "string_processor.py"), "w", encoding="utf-8") as f:
        f.write(string_processor_content)

    with open(os.path.join(base_dir, "data_processor.py"), "w", encoding="utf-8") as f:
        f.write(data_processor_content)

    logger.info(f"示例代码文件已创建在: {base_dir}")


def update_sample_file(base_dir: str, filename: str, content: str):
    """更新指定示例文件内容"""
    file_path = os.path.join(base_dir, filename)
    if not os.path.exists(file_path):
        logger.warning(f"文件 {file_path} 不存在，无法更新")
        return
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"已更新文件: {file_path}")


def add_sample_file(base_dir: str, filename: str, content: str):
    """新增示例文件，若存在则覆盖"""
    file_path = os.path.join(base_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    logger.info(f"已新增文件: {file_path}")


def delete_sample_file(base_dir: str, filename: str):
    """删除指定示例文件"""
    file_path = os.path.join(base_dir, filename)
    try:
        os.remove(file_path)
        logger.info(f"已删除文件: {file_path}")
    except FileNotFoundError:
        logger.warning(f"文件 {file_path} 不存在，无法删除")
    except Exception as e:
        logger.error(f"删除文件 {file_path} 失败: {e}")
