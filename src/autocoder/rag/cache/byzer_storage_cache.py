from autocoder.rag.cache.base_cache import (
    BaseCacheManager,
    DeleteEvent,
    AddOrUpdateEvent,
)
from typing import Generator, List, Dict, Any, Optional, Tuple
from autocoder.common import SourceCode
from loguru import logger
import pathspec
import os
import uuid
import json
from autocoder.rag.utils import process_file_in_multi_process, process_file_local
from byzerllm.apps.byzer_storage.simple_api import (
    ByzerStorage,
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
class ByzerStorageCache(BaseCacheManager):
    def __init__(
        self,
        path,
        ignore_spec,
        required_exts,
        extra_params: Optional[AutoCoderArgs] = None,
    ):
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.storage = ByzerStorage("byzerai_store", "rag", "files")
        self.queue = []
        self.chunk_size = 1000
        self._init_schema()

        if not extra_params:
            raise ValueError("extra_params is required for ByzerStorageCache")

        self.max_output_tokens = extra_params.hybrid_index_max_output_tokens

        # 设置缓存文件路径
        self.cache_dir = os.path.join(self.path, ".cache")
        self.cache_file = os.path.join(self.cache_dir, "byzer_storage_speedup.jsonl")
        self.cache = {}

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.process_queue)
        self.thread.daemon = True
        self.thread.start()

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
                with open(self.cache_file, "r") as f:
                    lines = f.readlines()
                    cache = {}
                    for line in lines:
                        try:
                            data = json.loads(line.strip())
                            if isinstance(data, dict) and "file_path" in data:
                                cache[data["file_path"]] = data
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
                with open(cache_file, "w") as f:
                    for data in self.cache.values():
                        json.dump(data, f, ensure_ascii=False)
                        f.write("\n")
            except IOError as e:
                logger.error(f"Error writing cache file: {str(e)}")
        else:
            lock_file = cache_file + ".lock"
            with open(lock_file, "w") as lockf:
                try:
                    # 获取文件锁
                    fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # 写入缓存文件
                    with open(cache_file, "w") as f:
                        for data in self.cache.values():
                            json.dump(data, f, ensure_ascii=False)
                            f.write("\n")

                finally:
                    # 释放文件锁
                    fcntl.flock(lockf, fcntl.LOCK_UN)

    def build_cache(self):
        """Build the cache by reading files and storing in Byzer Storage"""
        logger.info(f"Building cache for path: {self.path}")

        files_to_process = []
        for file_info in self.get_all_files():
            file_path, _, modify_time, file_md5 = file_info
            if (
                file_path not in self.cache                
                or self.cache[file_path]["md5"] != file_md5
            ):
                files_to_process.append(file_info)
                
        if not files_to_process:
            return

        from autocoder.rag.token_counter import initialize_tokenizer

        with Pool(
            processes=os.cpu_count(),
            initializer=initialize_tokenizer,
            initargs=(VariableHolder.TOKENIZER_PATH,),
        ) as pool:
            results = pool.map(process_file_in_multi_process, files_to_process)

        items = []
        for file_info, result in zip(files_to_process, results):            
            file_path, relative_path, modify_time, file_md5 = file_info
            content: List[SourceCode] = result
            self.cache[file_path] = {
                "file_path": file_path,
                "relative_path": relative_path,
                "content": [c.model_dump() for c in content],
                "modify_time": modify_time,
                "md5": file_md5,
            }

            for doc in content:
                logger.info(f"Processing file: {doc.module_name}")
                doc.module_name
                chunks = self._chunk_text(doc.source_code, self.chunk_size)
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_item = {
                        "_id": f"{doc.module_name}_{chunk_idx}",
                        "file_path": file_path,
                        "content": chunk,
                        "raw_content": chunk,
                        "vector": chunk,
                        "mtime": modify_time,
                    }
                    items.append(chunk_item)

        # Save to local cache
        logger.info("Saving cache to local file")
        self.write_cache()
        
        if items:
            logger.info("Clear cache from Byzer Storage")
            self.storage.truncate_table()
            logger.info("Save new cache to Byzer Storage")            
            max_workers = 5            
            chunk_size = max(1, len(items) // max_workers)
            item_chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
            
            total_chunks = len(item_chunks)
            completed_chunks = 0

            logger.info(f"Progress: {0}/{total_chunks} chunks completed")
            
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for chunk in item_chunks:
                    futures.append(
                        executor.submit(
                            lambda x: self.storage.write_builder().add_items(
                                x, vector_fields=["vector"], search_fields=["content"]
                            ).execute(),
                            chunk
                        )
                    )
                # Wait for all futures to complete
                for future in as_completed(futures):
                    try:
                        future.result()
                        completed_chunks += 1
                        logger.info(f"Progress: {completed_chunks}/{total_chunks} chunks completed")
                    except Exception as e:
                        logger.error(f"Error in saving chunk: {str(e)}")
            
            self.storage.commit()

    def update_storage(self, file_path, is_delete: bool):
        query = self.storage.query_builder()
        query.and_filter().add_condition("file_path", file_path).build()
        results = query.execute()
        if results:
            for result in results:
                self.storage.delete_by_ids([result["_id"]])
        items = []

        if not is_delete:
            content = [
                SourceCode.model_validate(doc)
                for doc in self.cache[file_path]["content"]
            ]
            modify_time = self.cache[file_path]["modify_time"]
            for doc in content:
                logger.info(f"Processing file: {doc.module_name}")
                doc.module_name
                chunks = self._chunk_text(doc.source_code, self.chunk_size)
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_item = {
                        "_id": f"{doc.module_name}_{chunk_idx}",
                        "file_path": file_path,
                        "content": chunk,
                        "raw_content": chunk,
                        "vector": chunk,
                        "mtime": modify_time,
                    }
                    items.append(chunk_item)
        if items:
            self.storage.write_builder().add_items(
                items, vector_fields=["vector"], search_fields=["content"]
            ).execute()
            self.storage.commit()

    def process_queue(self):
        while self.queue:
            file_list = self.queue.pop(0)
            if isinstance(file_list, DeleteEvent):
                for item in file_list.file_paths:
                    logger.info(f"{item} is detected to be removed")
                    del self.cache[item]
                    self.update_storage(item, is_delete=True)

            elif isinstance(file_list, AddOrUpdateEvent):
                for file_info in file_list.file_infos:
                    logger.info(f"{file_info[0]} is detected to be updated")
                    result = process_file_local(file_info[0])
                    self.cache[file_info[0]] = result
                    self.update_storage(file_info[0], is_delete=False)
            self.write_cache()

    def trigger_update(self):
        logger.info("检查文件是否有更新.....")
        files_to_process = []
        current_files = set()
        for file_info in self.get_all_files():
            file_path, _, _, file_md5 = file_info
            current_files.add(file_path)
            if (
                file_path not in self.cache
                or self.cache[file_path]["md5"] != file_md5
            ):
                files_to_process.append(file_info)

        deleted_files = set(self.cache.keys()) - current_files
        logger.info(f"files_to_process: {files_to_process}")
        logger.info(f"deleted_files: {deleted_files}")
        if deleted_files:
            with self.lock:
                self.queue.append(DeleteEvent(file_paths=deleted_files))
        if files_to_process:
            with self.lock:
                self.queue.append(AddOrUpdateEvent(file_infos=files_to_process))

    def get_cache(self, options: Dict[str, Any]) -> Dict[str, Dict]:
        """Search cached documents using query"""

        self.trigger_update()

        if options is None or "query" not in options:
            return self.cache
        
        query = options.get("query", "")
        total_tokens = 0    

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

        # Group results by file_path and reconstruct documents while preserving order
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
                for doc in cached_data["content"]:                    
                    if total_tokens + doc["tokens"] > self.max_output_tokens:
                        return result
                    total_tokens += doc["tokens"]
                result[file_path] = cached_data

        return result

                

    def get_all_files(self) -> List[Tuple[str, str, float, str]]:
        all_files = []
        for root, dirs, files in os.walk(self.path,followlinks=True):
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in default_ignore_dirs]

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
                all_files.append((file_path, relative_path, modify_time, file_md5))

        return all_files
