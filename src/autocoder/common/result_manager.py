import os
import json
import time
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ResultItem(BaseModel):
    """单条结果记录的数据模型"""
    content: str = Field(..., description="结果内容")
    meta: Dict[str, Any] = Field(default_factory=dict, description="元数据信息")
    time: int = Field(default_factory=lambda: int(time.time()), description="记录时间戳")

    class Config:
        arbitrary_types_allowed = True

class ResultManager:
    """结果管理器，用于维护一个追加写入的jsonl文件"""
    
    def __init__(self, source_dir: Optional[str] = None, event_file: Optional[str] = None):
        """
        初始化结果管理器
        
        Args:
            source_dir: 可选的源目录，如果不提供则使用当前目录
            event_file: 可选的事件文件路径，用于生成结果文件名
        """
        self.source_dir = source_dir or os.getcwd()
        self.result_dir = os.path.join(self.source_dir, ".auto-coder", "results")
        
        if event_file:
            # 获取文件名并去掉后缀
            event_file_name = os.path.splitext(os.path.basename(event_file))[0]
            self.result_file = os.path.join(self.result_dir, f"{event_file_name}.jsonl")
        else:
            self.result_file = os.path.join(self.result_dir, "results.jsonl")
            
        os.makedirs(self.result_dir, exist_ok=True)

    def append(self, content: str, meta: Optional[Dict[str, Any]] = None) -> ResultItem:
        """
        追加一条新的结果记录
        
        Args:
            content: 结果内容
            meta: 可选的元数据信息
            
        Returns:
            ResultItem: 新创建的结果记录
        """
        result_item = ResultItem(
            content=content,
            meta=meta or {},
        )
        
        with open(self.result_file, "a", encoding="utf-8") as f:
            f.write(result_item.model_dump_json() + "\n")
            
        return result_item
    
    def add_result(self, content: str, meta: Optional[Dict[str, Any]] = None) -> ResultItem:
        return self.append(content, meta)
        
    def get_last(self) -> Optional[ResultItem]:
        """
        获取最后一条记录
        
        Returns:
            Optional[ResultItem]: 最后一条记录，如果文件为空则返回None
        """
        if not os.path.exists(self.result_file):
            return None
            
        with open(self.result_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
            if not lines:
                return None
            last_line = lines[-1].strip()
            return ResultItem.model_validate_json(last_line)

    def get_all(self) -> List[ResultItem]:
        """
        获取所有记录
        
        Returns:
            List[ResultItem]: 所有记录的列表
        """
        if not os.path.exists(self.result_file):
            return []
            
        results = []
        with open(self.result_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:  # 跳过空行
                    results.append(ResultItem.model_validate_json(line))
        return results

    def get_by_time_range(self, 
                         start_time: Optional[int] = None, 
                         end_time: Optional[int] = None) -> List[ResultItem]:
        """
        获取指定时间范围内的记录
        
        Args:
            start_time: 开始时间戳
            end_time: 结束时间戳
            
        Returns:
            List[ResultItem]: 符合时间范围的记录列表
        """
        results = []
        for item in self.get_all():
            if start_time and item.time < start_time:
                continue
            if end_time and item.time > end_time:
                continue
            results.append(item)
        return results

    def clear(self) -> None:
        """清空所有记录"""
        if os.path.exists(self.result_file):
            os.remove(self.result_file)