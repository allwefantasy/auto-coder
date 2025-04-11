
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
