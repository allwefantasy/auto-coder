from typing import List, Dict, Any, Optional, Set, Tuple
import logging
from enum import Enum
from collections import defaultdict, Counter
from loguru import logger
class MergeStrategy(str, Enum):
    """合并策略枚举类"""
    SIMPLE_EXTEND = "simple_extend"  # 简单扩展（当前实现）
    FREQUENCY_RANK = "frequency_rank"  # 按频率排序
    WEIGHTED_RANK = "weighted_rank"  # 加权排序
    INTERLEAVE = "interleave"  # 交错合并
    DEDUPLICATE = "deduplicate"  # 去重合并
    QUERY_WEIGHTED = "query_weighted"  # 按查询加权


class CacheResultMerger:
    """
    缓存结果合并策略模块

    本模块提供了多种合并搜索结果的策略，用于处理多查询场景下的结果整合。

    主要包括：
    1. 简单扩展 (SIMPLE_EXTEND): 直接合并所有结果列表
    2. 频率排序 (FREQUENCY_RANK): 根据文件路径出现频率排序
    3. 加权排序 (WEIGHTED_RANK): 考虑结果排名位置的加权排序
    4. 交错合并 (INTERLEAVE): 交错合并多个查询结果
    5. 去重合并 (DEDUPLICATE): 合并结果并去除重复文件
    6. 查询加权 (QUERY_WEIGHTED): 考虑查询重要性的加权排序

    使用示例:
    ```python
    from cache_result_merge import CacheResultMerger, MergeStrategy

    # 创建合并器
    merger = CacheResultMerger(max_results=100)

    # 假设有多个查询结果
    query_results = [
        ("query1", [result1, result2, ...]),
        ("query2", [result3, result4, ...])
    ]

    # 使用特定策略合并
    merged_results = merger.merge(
        query_results, 
        strategy=MergeStrategy.WEIGHTED_RANK
    )
    ```
    """
    
    def __init__(self, max_results: int = None):
        """
        初始化结果合并器
        
        Args:
            max_results: 最大结果数，如果为None则不限制
        """
        self.max_results = max_results
    
    def merge(self, query_results: List[Tuple[str, List[Dict[str, Any]]]], 
              strategy: MergeStrategy = MergeStrategy.WEIGHTED_RANK) -> List[Dict[str, Any]]:
        """
        根据指定策略合并查询结果
        
        Args:
            query_results: 查询结果列表，每项为(查询, 结果列表)的元组
            strategy: 合并策略
            
        Returns:
            合并后的结果列表
        """
        if strategy == MergeStrategy.SIMPLE_EXTEND:
            return self._simple_extend_merge(query_results)
        elif strategy == MergeStrategy.FREQUENCY_RANK:
            return self._frequency_rank_merge(query_results)
        elif strategy == MergeStrategy.WEIGHTED_RANK:
            return self._weighted_rank_merge(query_results)
        elif strategy == MergeStrategy.INTERLEAVE:
            return self._interleave_merge(query_results)
        elif strategy == MergeStrategy.DEDUPLICATE:
            return self._deduplicate_merge(query_results)
        elif strategy == MergeStrategy.QUERY_WEIGHTED:
            return self._query_weighted_merge(query_results)
        else:
            logger.warning(f"未知的合并策略: {strategy}，使用简单扩展策略")
            return self._simple_extend_merge(query_results)
    
    def _simple_extend_merge(self, query_results: List[Tuple[str, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        """
        简单扩展策略：将所有结果简单合并
        
        Args:
            query_results: 查询结果列表
            
        Returns:
            合并后的结果列表
        """
        all_results = []
        for query, results in query_results:
            all_results.extend(results)
        
        logger.info(f"简单扩展策略合并结果: 从 {sum(len(r) for _, r in query_results)} 条到 {len(all_results)} 条")
        return all_results[:self.max_results] if self.max_results else all_results
    
    def _frequency_rank_merge(self, query_results: List[Tuple[str, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        """
        频率排序策略：按文件路径出现频率排序
        
        Args:
            query_results: 查询结果列表
            
        Returns:
            合并后的结果列表
        """
        # 合并所有结果
        all_results = []
        for _, results in query_results:
            all_results.extend(results)
        
        # 按文件路径计数
        file_path_counts = Counter(result["file_path"] for result in all_results)
        
        # 建立文件路径到结果的映射，保留每个文件路径的第一个结果
        file_to_result = {}
        for result in all_results:
            file_path = result["file_path"]
            if file_path not in file_to_result:
                file_to_result[file_path] = result
        
        # 按频率排序
        sorted_results = [file_to_result[file_path] for file_path, _ in file_path_counts.most_common()]
        
        logger.info(f"频率排序策略合并结果: 从 {len(all_results)} 条到 {len(sorted_results)} 条，按文件出现频率排序")
        return sorted_results[:self.max_results] if self.max_results else sorted_results
    
    def _weighted_rank_merge(self, query_results: List[Tuple[str, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        """
        加权排序策略：考虑结果位置和频率的加权排序
        
        Args:
            query_results: 查询结果列表
            
        Returns:
            合并后的结果列表
        """
        # 按文件路径评分
        file_path_scores = defaultdict(float)
        file_to_result = {}
        
        for _, results in query_results:
            for rank, result in enumerate(results):
                file_path = result["file_path"]
                # 排名越高，得分越高（排名从0开始，所以用1/(rank+1)）
                rank_score = 1.0 / (rank + 1)
                file_path_scores[file_path] += rank_score
                
                # 保存每个文件路径的第一个结果
                if file_path not in file_to_result:
                    file_to_result[file_path] = result
        
        # 按分数排序
        sorted_results = [file_to_result[file_path] 
                        for file_path, _ in sorted(file_path_scores.items(), key=lambda x: x[1], reverse=True)]
        
        logger.info(f"加权排序策略合并结果: 得到 {len(sorted_results)} 条结果，按位置加权排序")
        return sorted_results[:self.max_results] if self.max_results else sorted_results
    
    def _interleave_merge(self, query_results: List[Tuple[str, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        """
        交错合并策略：交错合并各查询的结果
        
        Args:
            query_results: 查询结果列表
            
        Returns:
            合并后的结果列表
        """
        # 获取每个查询的结果列表
        result_lists = [results for _, results in query_results]
        if not result_lists:
            return []
        
        # 交错合并结果
        interleaved = []
        seen_files = set()
        
        # 找出最长列表长度
        max_len = max(len(results) for results in result_lists)
        
        # 交错合并
        for i in range(max_len):
            for results in result_lists:
                if i < len(results):
                    result = results[i]
                    file_path = result["file_path"]
                    if file_path not in seen_files:
                        seen_files.add(file_path)
                        interleaved.append(result)
        
        logger.info(f"交错合并策略合并结果: 得到 {len(interleaved)} 条唯一结果")
        return interleaved[:self.max_results] if self.max_results else interleaved
    
    def _deduplicate_merge(self, query_results: List[Tuple[str, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        """
        去重合并策略：合并并去除重复的文件路径
        
        Args:
            query_results: 查询结果列表
            
        Returns:
            合并后的结果列表
        """
        all_results = []
        seen_files = set()
        
        for _, results in query_results:
            for result in results:
                file_path = result["file_path"]
                if file_path not in seen_files:
                    seen_files.add(file_path)
                    all_results.append(result)
        
        logger.info(f"去重合并策略合并结果: 从 {sum(len(r) for _, r in query_results)} 条到 {len(all_results)} 条唯一结果")
        return all_results[:self.max_results] if self.max_results else all_results
    
    def _query_weighted_merge(self, query_results: List[Tuple[str, List[Dict[str, Any]]]]) -> List[Dict[str, Any]]:
        """
        查询加权策略：根据查询的重要性加权排序结果
        
        Args:
            query_results: 查询结果列表，包含(查询, 结果)对
            
        Returns:
            合并后的结果列表
        """
        # 按照查询词加权
        file_path_scores = defaultdict(float)
        file_to_result = {}
        query_weights = {}
        
        # 计算每个查询的权重 (可以根据查询的长度、特殊性等调整)
        total_queries = len(query_results)
        for i, (query, _) in enumerate(query_results):
            # 默认权重，可以根据查询特性调整
            query_weights[query] = 1.0
        
        # 计算文件得分
        for query, results in query_results:
            query_weight = query_weights[query]
            for rank, result in enumerate(results):
                file_path = result["file_path"]
                # 排名越高，得分越高
                rank_score = 1.0 / (rank + 1)
                file_path_scores[file_path] += rank_score * query_weight
                
                # 保存每个文件路径的第一个结果
                if file_path not in file_to_result:
                    file_to_result[file_path] = result
        
        # 按分数排序
        sorted_results = [file_to_result[file_path] 
                        for file_path, _ in sorted(file_path_scores.items(), key=lambda x: x[1], reverse=True)]
        
        logger.info(f"查询加权策略合并结果: 得到 {len(sorted_results)} 条结果，按查询加权排序")
        return sorted_results[:self.max_results] if self.max_results else sorted_results 