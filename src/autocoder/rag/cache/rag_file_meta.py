import os
from typing import Dict, Any, Optional, Union, List, Tuple, Dict
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import glob
import json
from datetime import datetime
import time

import byzerllm

from autocoder.common import SourceCode
from autocoder.rag.token_counter import count_tokens
from pydantic import BaseModel

logger = logging.getLogger(__name__)

class FileUsage(BaseModel):
    description: str


class FileMetaItem(BaseModel):
    file_path:str
    usage:str
    md5:str
    timestamp:float

class RAGFileMeta:
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

def build_meta(doc_path: str, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM], batch_size: int = 10, max_workers: Optional[int] = None) -> str:
    """
    构建文件元数据信息，支持增量更新。
    
    此函数会：
    1. 查找 doc 目录下 .cache 目录中文件名包含 cache 的 jsonl 文件
    2. 找出最新的文件并读取内容
    3. 如果 meta.jsonl 已存在，会读取其中已有的元数据
    4. 只对 MD5 发生变化或新文件生成新的用途描述
    5. 将结果保存到 meta.jsonl 文件
    
    参数:
        doc_path: 文档根目录路径
        llm: ByzerLLM 实例，用于生成文件描述
        batch_size: 批处理大小，默认为 10
        max_workers: 最大线程数，默认为 None（使用 ThreadPoolExecutor 的默认值）
        
    返回:
        生成的元数据文件路径
    """
    # 确保 .cache 目录存在
    cache_dir = os.path.join(doc_path, ".cache")
    if not os.path.exists(cache_dir):
        logger.warning(f"Cache directory not found: {cache_dir}")
        return ""
    
    # 查找文件名包含 cache 的 jsonl 文件
    cache_files = glob.glob(os.path.join(cache_dir, "*cache*.jsonl"))
    if not cache_files:
        logger.warning(f"No cache files found in {cache_dir}")
        return ""
    
    # 根据修改时间排序，找出最新的文件
    latest_cache_file = max(cache_files, key=os.path.getmtime)
    logger.info(f"Using latest cache file: {latest_cache_file}")
    
    # 读取缓存文件内容
    file_contents = []
    file_md5_map = {}  # 用于存储文件路径到MD5的映射
    file_mtime_map = {}  # 用于存储文件路径到修改时间的映射
    current_files = set()  # 用于跟踪当前存在的文件
    
    try:
        with open(latest_cache_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line.strip())
                    file_path = data.get("file_path", "")
                    if not file_path:
                        continue
                    
                    # 标准化文件路径
                    file_path = os.path.normpath(file_path)
                    current_files.add(file_path)
                    
                    # 提取MD5值
                    file_md5 = data.get("md5", "")
                    if file_path and file_md5:
                        file_md5_map[file_path] = file_md5
                    
                    # 提取修改时间
                    modify_time = data.get("modify_time", 0.0)
                    if modify_time:
                        file_mtime_map[file_path] = float(modify_time)
                    
                    if "content" in data:
                        # 先将内容解析为 SourceCode 对象
                        source_codes = []
                        try:
                            source_codes = [SourceCode.model_validate(item) for item in data["content"]]
                            
                            # 从 SourceCode 对象中提取文本内容
                            file_content = ""
                            for source_code in source_codes:
                                if hasattr(source_code, "source_code") and source_code.source_code:
                                    file_content += source_code.source_code + "\n"
                            
                            if file_content:
                                file_contents.append((file_path, file_content))
                        except Exception as e:
                            logger.warning(f"Error parsing SourceCode for {file_path}: {str(e)}")
                            # 兼容旧格式：直接从 content_item 中提取 source_code
                            file_content = ""
                            for content_item in data["content"]:
                                if "source_code" in content_item:
                                    file_content += content_item["source_code"] + "\n"
                            
                            if file_content:
                                file_contents.append((file_path, file_content))
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON line in {latest_cache_file}")
                    continue
                except Exception as e:
                    logger.warning(f"Error processing line in cache file: {str(e)}")
                    continue
    except Exception as e:
        logger.error(f"Error reading cache file {latest_cache_file}: {str(e)}")
        return ""
    
    if not file_contents:
        logger.warning(f"No valid file contents found in {latest_cache_file}")
        return ""
    
    # 检查是否存在 meta.jsonl 文件，如果存在则读取以支持增量更新
    meta_file_path = os.path.join(cache_dir, "meta.jsonl")
    existing_meta = {}
    if os.path.exists(meta_file_path):
        try:
            with open(meta_file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        # 使用 FileMetaItem 解析元数据
                        meta_item = FileMetaItem.model_validate_json(line.strip())
                        file_path = meta_item.file_path
                        
                        if not file_path:
                            continue
                            
                        # 标准化文件路径
                        file_path = os.path.normpath(file_path)
                        existing_meta[file_path] = meta_item
                    except json.JSONDecodeError:
                        logger.warning(f"Invalid JSON line in {meta_file_path}")
                        continue
                    except Exception as e:
                        logger.warning(f"Error processing line in meta file: {str(e)}")
                        continue
            logger.info(f"Loaded {len(existing_meta)} entries from existing meta file")
        except Exception as e:
            logger.warning(f"Error reading existing meta file {meta_file_path}: {str(e)}")
    
    # 分类文件：哪些需要重新生成描述，哪些可以复用
    files_to_process = []
    reused_meta = {}
    
    for file_path, content in file_contents:
        current_md5 = file_md5_map.get(file_path, "")
        
        # 如果文件在现有元数据中存在，且MD5未变化，则复用
        # 注意：只有当缓存中和元数据中都有MD5，且相等时才复用
        if (file_path in existing_meta and 
            existing_meta[file_path].md5 and 
            current_md5 and 
            existing_meta[file_path].md5 == current_md5):
            reused_meta[file_path] = existing_meta[file_path]
            logger.debug(f"Reusing metadata for unchanged file: {file_path}")
        else:
            # 否则需要重新处理
            files_to_process.append((file_path, content))
            logger.debug(f"Need to process file: {file_path}, md5 changed or new file")
    
    # 使用 RAGFileMeta 生成新的文件描述
    new_file_usages = {}
    if files_to_process:
        logger.info(f"Processing {len(files_to_process)} files with changed content or new files")
        rag_file_meta = RAGFileMeta(llm)
        try:
            new_file_usages = rag_file_meta.describe_files_batch(
                files=files_to_process, 
                batch_size=batch_size,
                max_workers=max_workers
            )
        except Exception as e:
            logger.error(f"Error during batch processing of files: {str(e)}")
            # 继续执行，使用已处理的文件
    else:
        logger.info("No files need to be processed, all files unchanged")
    
    # 合并新旧元数据，只包含当前存在的文件
    all_meta_items = []
    
    # 添加复用的元数据
    for file_path, meta_item in reused_meta.items():
        if file_path in current_files:  # 只包含当前存在的文件
            all_meta_items.append(meta_item)
    
    # 添加新生成的元数据
    current_time = time.time()  # 获取当前时间戳（浮点数秒）
    for file_path, file_usage in new_file_usages.items():
        if file_path in current_files:  # 只包含当前存在的文件
            # 优先使用文件的实际修改时间，若不可用则使用当前时间
            file_timestamp = file_mtime_map.get(file_path, current_time)
            
            # 使用 FileMetaItem 模型创建新的元数据条目
            new_meta_item = FileMetaItem(
                file_path=file_path,
                usage=file_usage.description,
                md5=file_md5_map.get(file_path, ""),
                timestamp=file_timestamp  # 使用 float 类型的时间戳
            )
            all_meta_items.append(new_meta_item)
    
    # 保存元数据到 meta.jsonl 文件
    try:
        with open(meta_file_path, 'w', encoding='utf-8') as f:
            for meta_item in all_meta_items:
                f.write(json.dumps(meta_item.model_dump(), ensure_ascii=False) + "\n")
        
        removed_count = len(existing_meta) - len(reused_meta)
        logger.info(
            f"Metadata saved to {meta_file_path}, "
            f"total {len(all_meta_items)} entries "
            f"(reused: {len(reused_meta)}, new: {len(new_file_usages)}, removed: {removed_count})"
        )
    except Exception as e:
        logger.error(f"Error writing metadata file {meta_file_path}: {str(e)}")
        return ""
    
    return meta_file_path
