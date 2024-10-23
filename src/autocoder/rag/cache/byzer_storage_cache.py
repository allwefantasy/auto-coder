from .base_cache import BaseCacheManager
from ..simple_directory_reader import AutoCoderSimpleDirectoryReader
from typing import Generator, List, Dict, Any, Optional
from autocoder.common import SourceCode
from loguru import logger
import pathspec
import os
import uuid
import json
from autocoder.rag.utils import process_file_in_multi_process,process_file_local
from byzerllm.apps.byzer_storage.simple_api import (
    ByzerStorage,
    DataType,
    FieldOption,
    SortOption,
)

class ByzerStorageCache(BaseCacheManager):
    def __init__(self, path, ignore_spec, required_exts):
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.storage = ByzerStorage("byzerai_store", "rag", "files")
        self.chunk_size = 1000
        self._init_schema()
        self.file_mtimes = {}  # 存储文件修改时间
        
        # 设置缓存文件路径
        self.cache_dir = os.path.join(self.path, ".cache")
        self.cache_file = os.path.join(self.cache_dir, ".byzer_storage_speedup.jsonl")
        
        # 创建缓存目录
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        # 加载缓存
        self.cache = self._load_cache()

    def _chunk_text(self, text, max_length=1000):
        """Split text into chunks"""
        chunks = []
        current_chunk = []
        current_length = 0

        for line in text.split("\n"):
            if current_length + len(line) > max_length and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(line)
            current_length += len(line)

        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return chunks

    def _init_schema(self):
        """Initialize the Byzer Storage schema"""
        _ = (
            self.storage.schema_builder()
            .add_field("_id", DataType.STRING)
            .add_field("file_path", DataType.STRING)            
            .add_field("content", DataType.STRING, [FieldOption.ANALYZE])
            .add_field("raw_content", DataType.STRING, [FieldOption.NO_INDEX])
            .add_array_field("vector", DataType.FLOAT)
            .add_field("mtime", DataType.DOUBLE, [FieldOption.SORT])
            .execute()
        )

    def _load_cache(self) -> dict:
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r') as f:
                    lines = f.readlines()
                    cache = {}
                    for line in lines:
                        try:
                            data = json.loads(line.strip())
                            if isinstance(data, dict) and 'file_path' in data:
                                cache[data['file_path']] = data
                        except json.JSONDecodeError:
                            continue
                    return cache
            except Exception as e:
                logger.error(f"Error loading cache file: {str(e)}")
                return {}
        return {}

    def _save_cache(self, file_path: str, doc: SourceCode):
        """Save file info to cache"""
        cache_data = {
            'file_path': file_path,
            'content': doc.source_code,
            'mtime': os.path.getmtime(file_path),
            'tokens': doc.tokens
        }
        
        self.cache[file_path] = cache_data
        
        try:
            with open(self.cache_file, 'a') as f:
                f.write(json.dumps(cache_data) + '\n')
        except Exception as e:
            logger.error(f"Error saving to cache file: {str(e)}")

    def build_cache(self):
        """Build the cache by reading files and storing in Byzer Storage"""        
        logger.info(f"Building cache for path: {self.path}")

        # Get list of files to process
        reader = AutoCoderSimpleDirectoryReader(
            self.path,
            recursive=True,
            filename_as_id=True,
            required_exts=self.required_exts,
            exclude=self.ignore_spec,
        )
        files_to_process = [
            (str(f), str(f.relative_to(self.path)), os.path.getmtime(str(f)))
            for f in reader.input_files
        ]

        items = []
        # Process files in parallel and store modification times
        for source_codes in map(process_file_in_multi_process, files_to_process):
            for doc in source_codes:
                logger.info(f"Processing file: {doc.module_name}")
                file_path = str(doc.module_name)[len("##File: "):]
                mtime = os.path.getmtime(file_path)
                self.file_mtimes[file_path] = mtime
                
                chunks = self._chunk_text(doc.source_code, self.chunk_size)                
                for chunk_idx, chunk in enumerate(chunks):                    
                    chunk_item = {
                        "_id": f"{doc.module_name}_{chunk_idx}",
                        "file_path": file_path,                        
                        "content": chunk,
                        "raw_content": chunk,
                        "vector": chunk,
                        "mtime": mtime
                    }
                    items.append(chunk_item)                    
                
                # Save to local cache
                self._save_cache(file_path, doc)

        if items:
            self.storage.write_builder().add_items(
                items, vector_fields=["vector"], search_fields=["content"]
            ).execute()
            self.storage.commit()
    
    def get_cache(
        self, options: Dict[str, Any]
    ) -> Generator[SourceCode, None, None]:
        """Search cached documents using query"""
        query = options.get("query", "")
        if not query:
            for _, data in self.cache.items():
                yield SourceCode(
                    module_name=f"##File: {data['file_path']}",
                    source_code=data['content'],
                    tokens=data['tokens']
                )
            return
        
        self.update_cache()

        # Build query with both vector search and text search
        query_builder = self.storage.query_builder()
        query_builder.set_limit(100)

        # Add vector search if enabled
        if options.get("enable_vector_search", True):
            query_builder.set_vector_query(query, fields=["vector"])

        # Add text search
        if options.get("enable_text_search", True):
            query_builder.set_search_query(query, fields=["content"])

        results = query_builder.execute()

        # Group results by file_path and reconstruct documents
        grouped_results = {}
        for result in results:
            file_path = result["file_path"]
            if file_path not in grouped_results:
                # 收集所有结果中的file_path并去重
                file_paths = list(set([result["file_path"] for result in results]))
                
                # 从缓存中获取文件内容
                for file_path in file_paths:
                    if file_path in self.cache:
                        cached_data = self.cache[file_path]
                        yield SourceCode(
                            module_name=f"##File: {file_path}",
                            source_code=cached_data['content'],
                            tokens=cached_data['tokens']
                        )

    def update_cache(self):
        """Update cache when files are modified"""
        logger.info("Checking for file updates...")
        
        # Get current list of files
        reader = AutoCoderSimpleDirectoryReader(
            self.path,
            recursive=True,
            filename_as_id=True,
            required_exts=self.required_exts,
            exclude=self.ignore_spec,
        )
        
        current_files = {str(f): os.path.getmtime(str(f)) for f in reader.input_files}
        
        # Check for new or modified files
        files_to_update = []
        for file_path, current_mtime in current_files.items():
            cached_info = self.cache.get(file_path)
            if (not cached_info or 
                current_mtime > cached_info['mtime'] or
                file_path not in self.file_mtimes or 
                current_mtime > self.file_mtimes[file_path]):
                files_to_update.append((file_path, file_path, current_mtime))
                logger.info(f"Found modified file: {file_path}")
        
        # Process modified files
        if files_to_update:
            items = []
            for source_codes in map(process_file_in_multi_process, files_to_update):
                for doc in source_codes:
                    logger.info(f"Updating cache for file: {doc.module_name}")
                    file_path = str(doc.module_name)[len("##File: "):]
                    mtime = os.path.getmtime(file_path)
                    
                    # Delete existing entries for this file
                    query = self.storage.query_builder()
                    query.and_filter().add_condition("file_path", file_path).build()
                    results = query.execute()
                    if results:
                        for result in results:
                            self.storage.delete_by_ids([result["_id"]])
                    
                    # Add new entries
                    chunks = self._chunk_text(doc.source_code, self.chunk_size)
                    chunk_items = []
                    for chunk_idx, chunk in enumerate(chunks):                        
                        chunk_item = {
                            "_id": f"{file_path}_{chunk_idx}",
                            "file_path": file_path,                            
                            "content": chunk,
                            "raw_content": chunk,
                            "vector": chunk,
                            "mtime": mtime
                        }
                        items.append(chunk_item)
                        chunk_items.append(chunk_item)
                    
                    # Update local cache
                    self._save_cache(file_path, doc.source_code, chunk_items)
                    self.file_mtimes[file_path] = mtime
            
            if items:
                self.storage.write_builder().add_items(
                    items, vector_fields=["vector"], search_fields=["content"]
                ).execute()
                self.storage.commit()
                logger.info(f"Successfully updated {len(files_to_update)} files in cache")
        else:
            logger.info("No file updates found")
