import os
from typing import Dict, Any, Optional, Union, List, Tuple, Dict
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import byzerllm

from autocoder.common import SourceCode
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class FileUsage(BaseModel):
    description: str

class FileMeta:
    """
    A class that generates short descriptions for files.
    """
    
    def __init__(self, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
        """
        Initialize the FileMeta with a ByzerLLM instance.
        
        Args:
            llm: The ByzerLLM instance to use for generating descriptions.
        """
        self.llm = llm
    
    @byzerllm.prompt()
    def generate_file_description(self, file_path: str, content: str) -> str:
        """
        分析文件内容，生成一个简洁的描述，概括文件的核心功能和用途。
        
        参数:
            file_path: 文件路径
            content: 文件内容
            
        返回:
            文件用途的简短描述（10个汉字左右）
        
        任务说明:
        你的目标是根据文档生成一个简短而精准的描述，帮助用户快速理解该文件的主要用途。
        
        要求:
        1. 生成的描述必须简洁，控制在10个汉字左右
        2. 描述应直接反映文件的核心功能，而非技术细节
        3. 使用专业且准确的术语
        4. 如果文件包含类，重点描述类的主要功能
        5. 如果文件包含多个函数，提炼出它们的共同目的
        6. 避免过于宽泛的描述，如"工具类"、"辅助函数"等
        
        优秀示例:
        - 数据库连接池管理 (对于实现数据库连接管理的文件)
        - 用户认证中间件 (对于处理用户身份验证的文件)
        - 日志记录格式化器 (对于定义日志格式的文件)
        - 图像缩放处理器 (对于处理图像大小的文件)
        - 配置文件解析器 (对于解析配置文件的代码)
        - 缓存失效策略 (对于处理缓存过期的文件)
        
        ---
        
        文件路径: <path>{{ file_path }}</path>
        
        文件内容:
        <document>
        {{ content }}
        </document>
        
        请分析上述文档，提供一个简洁的描述（10个汉字左右），准确概括该文件的核心功能。输出格式为

        ```json
        {
            "description": "文件描述"
        }
        ```
        """

        
        
    def describe_file(self, file_path: str, content: str) -> FileUsage:
        """
        Generate a description for a file.
        
        Args:
            file_path: The path to the file.
            content: The content of the file.
            
        Returns:
            A short description of the file.
        """
        try:
            response = self.generate_file_description.with_llm(self.llm).with_return_type(FileUsage).run(file_path=file_path, content=content)
            return response
        except Exception as e:
            logger.error(f"Error generating description for {file_path}: {str(e)}")
            return FileUsage(description="未知用途文件")
    
    def describe_files(self, files: List[Tuple[str, str]], max_workers: Optional[int] = None) -> Dict[str, FileUsage]:
        """
        使用多线程并发处理多个文件，为每个文件生成描述。
        
        Args:
            files: 包含文件路径和内容的元组列表，格式为 [(file_path1, content1), (file_path2, content2), ...]
            max_workers: 最大线程数，默认为 None（使用 ThreadPoolExecutor 的默认值）
            
        Returns:
            一个字典，键为文件路径，值为对应的 FileUsage 对象
        """
        results = {}
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 创建 Future 对象的字典，键为文件路径
            future_to_path = {
                executor.submit(self.describe_file, file_path, content): file_path
                for file_path, content in files
            }
            
            # 处理完成的任务
            for future in as_completed(future_to_path):
                file_path = future_to_path[future]
                try:
                    file_usage = future.result()
                    results[file_path] = file_usage
                except Exception as e:
                    logger.error(f"处理文件 {file_path} 时发生错误: {str(e)}")
                    results[file_path] = FileUsage(description="处理失败")
        
        return results
    
    def describe_files_batch(self, files: List[Tuple[str, str]], batch_size: int = 10, max_workers: Optional[int] = None) -> Dict[str, FileUsage]:
        """
        分批次使用多线程处理文件，适用于大量文件场景，避免创建过多线程。
        
        Args:
            files: 包含文件路径和内容的元组列表，格式为 [(file_path1, content1), (file_path2, content2), ...]
            batch_size: 每批处理的文件数量
            max_workers: 每批次的最大线程数
            
        Returns:
            一个字典，键为文件路径，值为对应的 FileUsage 对象
        """
        all_results = {}
        
        # 将文件列表分成批次
        for i in range(0, len(files), batch_size):
            batch = files[i:i + batch_size]
            # 处理当前批次
            batch_results = self.describe_files(batch, max_workers=max_workers)
            # 合并结果
            all_results.update(batch_results)
            
        return all_results
