from autocoder.rag.cache.base_cache import (
    BaseCacheManager,
    DeleteEvent,
    AddOrUpdateEvent,
    FileInfo,
    CacheItem
)
from typing import Generator, List, Dict, Any, Optional, Tuple
from autocoder.common import SourceCode
from loguru import logger
import functools
import pathspec
import os
import uuid
import json
from autocoder.rag.utils import process_file_in_multi_process, process_file_local
from byzerllm.apps.byzer_storage.local_simple_api import (
    LocalByzerStorage,
    DataType,
    FieldOption,
    SortOption,
)
from autocoder.common import AutoCoderArgs
import threading
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor, as_completed
from autocoder.rag.variable_holder import VariableHolder
import platform
import hashlib
from typing import Union
from byzerllm import SimpleByzerLLM, ByzerLLM
from autocoder.rag.cache.cache_result_merge import CacheResultMerger, MergeStrategy
import time
from typing import Optional,Union
from .failed_files_utils import save_failed_files, load_failed_files
from autocoder.utils.llms import get_llm_names

if platform.system() != "Windows":
    import fcntl
else:
    fcntl = None


def generate_file_md5(file_path: str) -> str:
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


def generate_content_md5(content: Union[str, bytes]) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    md5_hash = hashlib.md5()
    md5_hash.update(content)
    return md5_hash.hexdigest()


default_ignore_dirs = [
    "__pycache__",
    "node_modules",
    "_images"
]


class LocalByzerStorageCache(BaseCacheManager):
    def __init__(
        self,
        path,
        ignore_spec,
        required_exts,
        extra_params: Optional[AutoCoderArgs] = None,
        emb_llm: Union[ByzerLLM, SimpleByzerLLM] = None,
        host: str = "127.0.0.1",
        port: int = 33333,
        args:Optional[AutoCoderArgs]=None,
        llm:Optional[Union[ByzerLLM,SimpleByzerLLM,str]]=None,
    ):
        """
        初始化基于 Byzer Storage 的 RAG 缓存管理器。
        """
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.args = args
        self.llm = llm
        self.rag_build_name = extra_params.rag_build_name
        self.storage = LocalByzerStorage("byzerai_store",
            "rag_test", self.rag_build_name, host=host, port=port,emb_llm=emb_llm)
        self.queue = []
        self.chunk_size = 1000
        self._init_schema()

        if not extra_params:
            raise ValueError("extra_params is required for ByzerStorageCache")

        self.max_output_tokens = extra_params.hybrid_index_max_output_tokens

        # 设置缓存文件路径
        self.cache_dir = os.path.join(self.path, ".cache")
        self.cache_file = os.path.join(
            self.cache_dir, "byzer_storage_speedup.jsonl")
        self.cache: Dict[str, CacheItem] = {}

        # 创建缓存目录
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        # failed files support
        self.failed_files_path = os.path.join(self.cache_dir, "failed_files.json")
        self.failed_files = load_failed_files(self.failed_files_path)

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.process_queue)
        self.thread.daemon = True
        self.thread.start()

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

    def _load_cache(self) -> Dict[str, CacheItem]:
        """Load cache from file"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    cache = {}
                    for line in lines:
                        try:
                            data = json.loads(line.strip())
                            if isinstance(data, dict) and "file_path" in data:
                                # 转换为 CacheItem 对象
                                cache_item = CacheItem.model_validate(data)
                                cache[data["file_path"]] = cache_item
                        except json.JSONDecodeError:
                            continue
                    return cache
            except Exception as e:
                logger.error(f"Error loading cache file: {str(e)}")
                return {}
        return {}

    def write_cache(self):
        cache_file = self.cache_file

        if not fcntl:
            try:
                with open(cache_file, "w", encoding="utf-8") as f:
                    for cache_item in self.cache.values():
                        # 确保序列化 Pydantic 模型
                        json.dump(cache_item.model_dump(),
                                  f, ensure_ascii=False)
                        f.write("\n")
            except IOError as e:
                logger.error(f"Error writing cache file: {str(e)}")
        else:
            lock_file = cache_file + ".lock"
            with open(lock_file, "w", encoding="utf-8") as lockf:
                try:
                    # 获取文件锁
                    fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # 写入缓存文件
                    with open(cache_file, "w", encoding="utf-8") as f:
                        for cache_item in self.cache.values():
                            # 确保序列化 Pydantic 模型
                            json.dump(cache_item.model_dump(),
                                      f, ensure_ascii=False)
                            f.write("\n")

                finally:
                    # 释放文件锁
                    fcntl.flock(lockf, fcntl.LOCK_UN)

    def fileinfo_to_tuple(self, file_info: FileInfo) -> Tuple[str, str, float, str]:
        return (file_info.file_path, file_info.relative_path, file_info.modify_time, file_info.file_md5)

    def build_cache(self):
        """Build the cache by reading files and storing in Byzer Storage"""
        logger.info(f"[BUILD CACHE] Starting cache build for path: {self.path}")

        files_to_process = []
        for file_info in self.get_all_files():
            if (
                file_info.file_path not in self.cache
                or self.cache[file_info.file_path].md5 != file_info.file_md5
            ):
                files_to_process.append(file_info)

        logger.info(f"[BUILD CACHE] Found {len(files_to_process)} files to process")
        if not files_to_process:
            logger.info("[BUILD CACHE] No files to process, cache build completed")
            return

        from autocoder.rag.token_counter import initialize_tokenizer

        logger.info("[BUILD CACHE] Starting parallel file processing...")
        llm_name = get_llm_names(self.llm)[0] if self.llm else None
        product_mode = self.args.product_mode
        start_time = time.time()
        with Pool(
            processes=os.cpu_count(),
            initializer=initialize_tokenizer,
            initargs=(VariableHolder.TOKENIZER_PATH,),
        ) as pool:
            target_files_to_process = []
            for file_info in files_to_process:
                target_files_to_process.append(
                    self.fileinfo_to_tuple(file_info))
            worker_func = functools.partial(process_file_in_multi_process, llm=llm_name, product_mode=product_mode)
            results = pool.map(worker_func, target_files_to_process)
        
        processing_time = time.time() - start_time
        logger.info(f"[BUILD CACHE] File processing completed, time elapsed: {processing_time:.2f}s")

        items = []
        for file_info, result in zip(files_to_process, results):
            content: List[SourceCode] = result
            self.cache[file_info.file_path] = CacheItem(
                file_path=file_info.file_path,
                relative_path=file_info.relative_path,
                content=[c.model_dump() for c in content],
                modify_time=file_info.modify_time,
                md5=file_info.file_md5,
            )

            for doc in content:
                logger.info(f"[BUILD CACHE] Processing file: {doc.module_name}")
                doc.module_name
                chunks = self._chunk_text(doc.source_code, self.chunk_size)
                logger.info(f"[BUILD CACHE] File {doc.module_name} chunking completed, total chunks: {len(chunks)}")
                # 可能chunk 会超出 chunk size, 为了防止出现问题，我们会做截断
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_item = {
                        "_id": f"{doc.module_name}_{chunk_idx}",
                        "file_path": file_info.file_path,
                        "content": chunk[0:self.chunk_size*2],
                        "raw_content": chunk[0:self.chunk_size*2],
                        "vector": chunk[0:self.args.rag_emb_text_size],
                        "mtime": file_info.modify_time,
                    }
                    items.append(chunk_item)

        # Save to local cache
        logger.info("[BUILD CACHE] Saving cache to local file")
        self.write_cache()        

        if items:            
            logger.info("[BUILD CACHE] Clearing existing cache from Byzer Storage")
            self.storage.truncate_table()        
            logger.info(f"[BUILD CACHE] Preparing to write to Byzer Storage, total chunks: {len(items)}, total files: {len(files_to_process)}")
            
            # Use a fixed optimal batch size instead of dividing by worker count
            batch_size = 100  # Optimal batch size for Byzer Storage
            item_batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
            
            total_batches = len(item_batches)
            completed_batches = 0

            logger.info(f"[BUILD CACHE] Starting to write to Byzer Storage using {batch_size} items per batch, "
                       f"total batches: {total_batches}")
            start_time = time.time()

            # Use more workers to process the smaller batches efficiently
            max_workers = min(self.extra_params.rag_index_build_workers, total_batches)  # Cap at 10 workers or total batch count
            logger.info(f"[BUILD CACHE] Using {max_workers} parallel workers for processing")

            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                # Submit all batches to the executor upfront (non-blocking)
                for batch in item_batches:
                    futures.append(
                        executor.submit(
                            lambda x: self.storage.write_builder().add_items(
                                x, vector_fields=["vector"], search_fields=["content"]
                            ).execute(),
                            batch
                        )
                    )
                
                # Wait for futures to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                        completed_batches += 1
                        elapsed = time.time() - start_time
                        estimated_total = elapsed / completed_batches * total_batches if completed_batches > 0 else 0
                        remaining = estimated_total - elapsed
                        
                        # Only log progress at reasonable intervals to reduce log spam
                        if completed_batches == 1 or completed_batches == total_batches or completed_batches % max(1, total_batches // 10) == 0:
                            logger.info(
                                f"[BUILD CACHE] Progress: {completed_batches}/{total_batches} batches completed "
                                f"({(completed_batches/total_batches*100):.1f}%) "
                                f"Estimated time remaining: {remaining:.1f}s"
                            )
                    except Exception as e:
                        logger.error(f"[BUILD CACHE] Error saving batch: {str(e)}")
                        # Add more detailed error information
                        logger.error(f"[BUILD CACHE] Error details: batch size: {len(batch) if 'batch' in locals() else 'unknown'}")

            total_time = time.time() - start_time
            logger.info(f"[BUILD CACHE] All chunks written, total time: {total_time:.2f}s")
            self.storage.commit()
            logger.info("[BUILD CACHE] Changes committed to Byzer Storage")

    def update_storage(self, file_info: FileInfo, is_delete: bool):
        """
        Updates file content in the Byzer Storage vector database.
        
        Parameters:
            file_info: FileInfo object containing file path, relative path, modify time, and MD5 hash
            is_delete: Whether this is a delete operation, True means all records for this file will be removed
            
        Process:
            1. First query and delete all existing records for this file path from the vector database
            2. If not a delete operation:
               a. Get parsed content (SourceCode objects) for the file from local cache
               b. Iterate through each SourceCode object
               c. Split its source code into fixed-size (chunk_size) text chunks
               d. Create items for each chunk containing:
                  - ID: combination of module name and chunk index
                  - File path
                  - Content text
                  - Raw content (for searching)
                  - Vector representation (embedding generated by ByzerLLM)
                  - Modify time
            3. Write all items to Byzer Storage with vector and search fields specified
            4. Commit changes to ensure data persistence
            
        Notes:
            - This method removes all records for a file before updating to avoid leftovers
            - File content is processed in chunks, each stored and indexed separately
            - Vector fields are used for similarity search, content field for full-text search
        """
        logger.info(f"[UPDATE STORAGE] Starting update for file: {file_info.file_path}, is delete: {is_delete}")
        
        query = self.storage.query_builder()
        query.and_filter().add_condition("file_path", file_info.file_path).build()
        results = query.execute()
        if results:
            logger.info(f"[UPDATE STORAGE] Deleting existing records from Byzer Storage: {len(results)} records")
            for result in results:
                self.storage.delete_by_ids([result["_id"]])
        items = []

        if not is_delete:
            logger.info(f"[UPDATE STORAGE] Getting file content from cache and preparing update")
            content = [
                SourceCode.model_validate(doc)
                for doc in self.cache[file_info.file_path].content
            ]
            modify_time = self.cache[file_info.file_path].modify_time
            for doc in content:
                logger.info(f"[UPDATE STORAGE] Processing file: {doc.module_name}")
                doc.module_name
                chunks = self._chunk_text(doc.source_code, self.chunk_size)
                logger.info(f"[UPDATE STORAGE] File {doc.module_name} chunking completed, total chunks: {len(chunks)}")
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_item = {
                        "_id": f"{doc.module_name}_{chunk_idx}",
                        "file_path": file_info.file_path,
                        "content": chunk[0:self.chunk_size*2],
                        "raw_content": chunk[0:self.chunk_size*2],
                        "vector": chunk[0:self.chunk_size*2],
                        "mtime": modify_time,
                    }
                    items.append(chunk_item)
        if items:
            logger.info(f"[UPDATE STORAGE] Starting to write {len(items)} chunks to Byzer Storage")
            start_time = time.time()
            
            # Use optimal batch size here too
            batch_size = 100
            if len(items) > batch_size:
                logger.info(f"[UPDATE STORAGE] Using batched writes with {batch_size} items per batch")
                batches = [items[i:i + batch_size] for i in range(0, len(items), batch_size)]
                total_batches = len(batches)
                
                for i, batch in enumerate(batches):
                    self.storage.write_builder().add_items(
                        batch, vector_fields=["vector"], search_fields=["content"]
                    ).execute()
                    logger.info(f"[UPDATE STORAGE] Progress: {i+1}/{total_batches} batches written")
            else:
                # For small item counts, just use a single write operation
                self.storage.write_builder().add_items(
                    items, vector_fields=["vector"], search_fields=["content"]
                ).execute()
            
            self.storage.commit()
            elapsed = time.time() - start_time
            logger.info(f"[UPDATE STORAGE] Write completed, time elapsed: {elapsed:.2f}s")
        else:
            logger.info(f"[UPDATE STORAGE] No content to write")

    def process_queue(self):
        if not self.queue:
            logger.info("[QUEUE PROCESSING] Queue is empty, nothing to process")
            return
            
        logger.info(f"[QUEUE PROCESSING] Starting queue processing, queue length: {len(self.queue)}")
        start_time = time.time()
        
        while self.queue:
            file_list = self.queue.pop(0)
            if isinstance(file_list, DeleteEvent):
                logger.info(f"[QUEUE PROCESSING] Processing delete event, total files: {len(file_list.file_paths)}")
                for item in file_list.file_paths:
                    logger.info(f"[QUEUE PROCESSING] Processing file deletion: {item}")
                    del self.cache[item]
                    # remove from failed files if present
                    if item in self.failed_files:
                        self.failed_files.remove(item)                        
                        save_failed_files(self.failed_files_path, self.failed_files)
                    # Create a temporary FileInfo object
                    file_info = FileInfo(
                        file_path=item, relative_path="", modify_time=0, file_md5="")
                    self.update_storage(file_info, is_delete=True)

            elif isinstance(file_list, AddOrUpdateEvent):
                logger.info(f"[QUEUE PROCESSING] Processing add/update event, total files: {len(file_list.file_infos)}")
                for file_info in file_list.file_infos:
                    logger.info(
                        f"[QUEUE PROCESSING] Processing file update: {file_info.file_path}")
                    try:
                        content = process_file_local(
                            self.fileinfo_to_tuple(file_info), llm=self.llm, product_mode=self.product_mode)
                        if content:
                            self.cache[file_info.file_path] = CacheItem(
                                file_path=file_info.file_path,
                                relative_path=file_info.relative_path,
                                content=[c.model_dump() for c in content],
                                modify_time=file_info.modify_time,
                                md5=file_info.file_md5,
                            )
                            self.update_storage(file_info, is_delete=False)
                            # remove from failed files if present
                            if file_info.file_path in self.failed_files:
                                self.failed_files.remove(file_info.file_path)                                
                                save_failed_files(self.failed_files_path, self.failed_files)
                        else:
                            logger.warning(f"Empty result for file: {file_info.file_path}, treat as parse failed, skipping cache update")
                            self.failed_files.add(file_info.file_path)                            
                            save_failed_files(self.failed_files_path, self.failed_files)
                    except Exception as e:
                        logger.error(f"Error in process_queue: {e}")
                        self.failed_files.add(file_info.file_path)                        
                        save_failed_files(self.failed_files_path, self.failed_files)
            self.write_cache()
        
        elapsed = time.time() - start_time
        logger.info(f"[QUEUE PROCESSING] Queue processing completed, time elapsed: {elapsed:.2f}s")

    def trigger_update(self):
        logger.info("[TRIGGER UPDATE] Starting file update check...")
        start_time = time.time()
        
        files_to_process = []
        current_files = set()
        for file_info in self.get_all_files():
            current_files.add(file_info.file_path)
            # skip failed files
            if file_info.file_path in self.failed_files:
                logger.info(f"文件 {file_info.file_path} 之前解析失败，跳过此次更新")
                continue
            if (
                file_info.file_path not in self.cache
                or self.cache[file_info.file_path].md5 != file_info.file_md5
            ):
                files_to_process.append(file_info)

        deleted_files = set(self.cache.keys()) - current_files
        
        logger.info(f"[TRIGGER UPDATE] Files to process: {len(files_to_process)}")
        logger.info(f"[TRIGGER UPDATE] Files deleted: {len(deleted_files)}")
        
        if deleted_files:
            logger.info(f"[TRIGGER UPDATE] Adding delete event to queue")
            with self.lock:
                self.queue.append(DeleteEvent(file_paths=deleted_files))
        if files_to_process:
            logger.info(f"[TRIGGER UPDATE] Adding update event to queue")
            with self.lock:
                self.queue.append(AddOrUpdateEvent(
                    file_infos=files_to_process))
        
        elapsed = time.time() - start_time
        logger.info(f"[TRIGGER UPDATE] Check completed, time elapsed: {elapsed:.2f}s")

    def get_single_cache(self, query: str, options: Dict[str, Any]) -> Dict[str, Dict]:
        """Search cached documents using query"""
        
        total_tokens = 0
        logger.info(f"Querying cache, query: {query}")
        # Build query with both vector search and text search
        query_builder = self.storage.query_builder()
        query_builder.set_limit(100000)

        # Add vector search if enabled
        if options.get("enable_vector_search", True):
            query_builder.set_vector_query(query, fields=["vector"])

        # Add text search
        if options.get("enable_text_search", True):
            query_builder.set_search_query(query, fields=["content"])

        results = query_builder.execute()

        logger.info(f"From cache retrieved: {len(results)} records")
        # Preview first 5 results with all fields but limited content size
        preview_results = []
        for r in results[:5]:
            # Create a copy of the entire result
            preview = r.copy()            
            # Similarly limit raw_content if it exists
            if "raw_content" in preview and isinstance(preview["raw_content"], str):
                preview["raw_content"] = preview["raw_content"][:100] + "..." if len(preview["raw_content"]) > 100 else preview["raw_content"]
            preview_results.append(preview)
        logger.info(f"Previewing first 5 records:")
        
        for r in preview_results:
            logger.info(f"File path: {r['file_path']}")            
            logger.info(f"Raw content: {r['raw_content']}")
            # Print other fields
            for k, v in r.items():
                if k not in ["file_path", "raw_content"]:
                    logger.info(f"{k}: {v}")
            logger.info("-"*100)

        return results                       


    def get_cache(self, options: Dict[str, Any]) -> Dict[str, Dict]:
        """
        获取缓存中的文档信息
        
        如果options中包含query，则根据query搜索；否则返回所有缓存
        """
        # options是一个词典，词典的key是搜索参数，value是具体值
        
        # 触发更新
        self.trigger_update()        

        # 如果没有查询参数，则返回所有缓存
        if options is None or "queries" not in options:
            return {file_path: self.cache[file_path].model_dump() for file_path in self.cache}
        
        queries = options.get("queries", [])
        
        # 如果没有查询或只有一个查询，使用原来的方法
        if not queries:
            return {file_path: self.cache[file_path].model_dump() for file_path in self.cache}
        elif len(queries) == 1:
            results = self.get_single_cache(queries[0], options)
            return self._process_search_results(results)
        
        # 获取合并策略
        merge_strategy_name = options.get("merge_strategy", MergeStrategy.WEIGHTED_RANK.value)
        try:
            merge_strategy = MergeStrategy(merge_strategy_name)
        except ValueError:
            logger.warning(f"Unknown merge strategy: {merge_strategy_name}, using default strategy")
            merge_strategy = MergeStrategy.WEIGHTED_RANK
        
        # 限制最大结果数
        max_results = options.get("max_results", None)
        merger = CacheResultMerger(max_results=max_results)
        
        # 并发处理多个查询
        query_results = []
        with ThreadPoolExecutor(max_workers=min(len(queries), 10)) as executor:
            future_to_query = {executor.submit(self.get_single_cache, query, options): query for query in queries}
            for future in as_completed(future_to_query):
                query = future_to_query[future]
                try:
                    query_result = future.result()
                    logger.info(f"Query '{query}' returned {len(query_result)} records")
                    query_results.append((query, query_result))
                except Exception as e:
                    logger.error(f"Error processing query '{query}': {str(e)}")
        
        logger.info(f"All queries returned {sum(len(r) for _, r in query_results)} records")
        logger.info(f"Using merge strategy: {merge_strategy}")
        
        # 使用策略合并结果
        merged_results = merger.merge(query_results, strategy=merge_strategy)
        
        return self._process_search_results(merged_results)
    
    def _process_search_results(self, results):
        """处理搜索结果，提取文件路径并构建结果字典"""
        # 记录被处理的总tokens数
        total_tokens = 0
        
        # Group results by file_path and reconstruct documents while preserving order
        # 这里还可以有排序优化，综合考虑一篇内容出现的次数以及排序位置
        file_paths = []
        seen = set()
        for result in results:
            file_path = result["file_path"]
            if file_path not in seen:
                seen.add(file_path)
                file_paths.append(file_path)

        # 从缓存中获取文件内容
        result = {}
        for file_path in file_paths:
            if file_path in self.cache:
                cached_data = self.cache[file_path]
                for doc in cached_data.content:
                    if total_tokens + doc["tokens"] > self.max_output_tokens:
                        logger.info(f"User tokens set to: {self.max_output_tokens}, cumulative tokens: {total_tokens} current file: {file_path} tokens: {doc['tokens']}, data record count change: {len(results)} -> {len(result)}")
                        return result
                    total_tokens += doc["tokens"]
                result[file_path] = cached_data.model_dump()
        
        logger.info(f"User tokens set to: {self.max_output_tokens}, cumulative tokens: {total_tokens}, data record count change: {len(results)} -> {len(result)}")
        return result

    def get_all_files(self) -> List[FileInfo]:
        all_files = []
        for root, dirs, files in os.walk(self.path, followlinks=True):
            dirs[:] = [d for d in dirs if not d.startswith(
                ".") and d not in default_ignore_dirs]

            if self.ignore_spec:
                relative_root = os.path.relpath(root, self.path)
                dirs[:] = [
                    d
                    for d in dirs
                    if not self.ignore_spec.match_file(os.path.join(relative_root, d))
                ]
                files = [
                    f
                    for f in files
                    if not self.ignore_spec.match_file(os.path.join(relative_root, f))
                ]

            for file in files:
                if self.required_exts and not any(
                    file.endswith(ext) for ext in self.required_exts
                ):
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.path)
                modify_time = os.path.getmtime(file_path)
                file_md5 = generate_file_md5(file_path)
                all_files.append(FileInfo(file_path=file_path,
                                          relative_path=relative_path,
                                          modify_time=modify_time,
                                          file_md5=file_md5))

        return all_files
