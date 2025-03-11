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
from .rag_file_meta import FileInfo
from .cache_result_merge import CacheResultMerger, MergeStrategy

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
    ):
        """
        初始化基于 Byzer Storage 的 RAG 缓存管理器。
        
        参数:
            path: 需要索引的代码库根目录
            ignore_spec: 指定哪些文件/目录应被忽略的规则
            required_exts: 需要处理的文件扩展名列表
            extra_params: 额外的配置参数，包含向量索引相关设置
            emb_llm: 用于生成文本向量嵌入的 ByzerLLM 实例
            host: Byzer Storage 服务的主机地址
            port: Byzer Storage 服务的端口
            
        缓存结构 (self.cache):
            self.cache 是一个字典，键为文件路径，值为 CacheItem 对象:
            {
                "file_path1": CacheItem(
                    file_path: str,              # 文件的绝对路径
                    relative_path: str,          # 相对于项目根目录的路径
                    content: List[Dict],         # 文件内容的结构化表示，每个元素是 SourceCode 对象的序列化
                    modify_time: float,          # 文件最后修改时间的时间戳
                    md5: str                     # 文件内容的 MD5 哈希值，用于检测变更
                ),
                "file_path2": CacheItem(...),
                ...
            }
            
            这个缓存有两层存储:
            1. 本地文件缓存: 保存在项目根目录的 .cache/byzer_storage_speedup.jsonl 文件中
               - 用于跟踪文件变更和快速加载
               - 使用 JSONL 格式存储，每行是一个 CacheItem 的 JSON 表示
            
            2. Byzer Storage 向量数据库:
               - 存储文件内容的分块和向量嵌入
               - 每个文件被分割成大小为 chunk_size 的文本块
               - 每个块都会生成向量嵌入，用于语义搜索
               - 存储结构包含: 文件路径、内容块、原始内容、向量嵌入、修改时间
        
        源代码处理流程:
            在缓存更新过程中使用了两个关键函数:
            
            1. process_file_in_multi_process: 在多进程环境中处理文件
               - 参数: file_info (文件信息元组)
               - 返回值: List[SourceCode] 或 None
               - 用途: 在初始构建缓存时并行处理多个文件
            
            2. process_file_local: 在当前进程中处理单个文件
               - 参数: file_path (文件路径)
               - 返回值: List[SourceCode] 或 None
               - 用途: 在检测到文件更新时处理单个文件
            
            文件处理后，会:
            1. 更新内存中的缓存 (self.cache)
            2. 将缓存持久化到本地文件
            3. 将内容分块并更新到 Byzer Storage 向量数据库
        
        更新机制:
            - 通过单独的线程异步处理文件变更
            - 使用 MD5 哈希值检测文件是否发生变化
            - 支持文件添加、更新和删除事件
            - 使用向量数据库进行语义检索，支持相似度搜索
        """
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
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
        logger.info(f"Building cache for path: {self.path}")

        files_to_process = []
        for file_info in self.get_all_files():
            if (
                file_info.file_path not in self.cache
                or self.cache[file_info.file_path].md5 != file_info.file_md5
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
            target_files_to_process = []
            for file_info in files_to_process:
                target_files_to_process.append(
                    self.fileinfo_to_tuple(file_info))
            results = pool.map(process_file_in_multi_process,
                               target_files_to_process)

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
                logger.info(f"Processing file: {doc.module_name}")
                doc.module_name
                chunks = self._chunk_text(doc.source_code, self.chunk_size)
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_item = {
                        "_id": f"{doc.module_name}_{chunk_idx}",
                        "file_path": file_info.file_path,
                        "content": chunk,
                        "raw_content": chunk,
                        "vector": chunk,
                        "mtime": file_info.modify_time,
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
            item_chunks = [items[i:i + chunk_size]
                           for i in range(0, len(items), chunk_size)]

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
                        logger.info(
                            f"Progress: {completed_chunks}/{total_chunks} chunks completed")
                    except Exception as e:
                        logger.error(f"Error in saving chunk: {str(e)}")

            self.storage.commit()

    def update_storage(self, file_info: FileInfo, is_delete: bool):
        """
        更新 Byzer Storage 向量数据库中的文件内容。
        
        参数:
            file_info: 包含文件路径、相对路径、修改时间和MD5哈希的文件信息对象
            is_delete: 是否为删除操作，True表示从数据库中删除该文件的所有记录
            
        处理流程:
            1. 首先查询并删除向量数据库中该文件路径的所有现有记录
            2. 如果不是删除操作:
               a. 从本地缓存获取文件的解析内容 (SourceCode 对象列表)
               b. 遍历每个 SourceCode 对象
               c. 将其源代码分成固定大小 (chunk_size) 的文本块
               d. 为每个块创建包含以下内容的项:
                  - ID: 由模块名和块索引组成
                  - 文件路径
                  - 内容文本
                  - 原始内容 (用于搜索)
                  - 向量表示 (由 ByzerLLM 生成的嵌入)
                  - 修改时间
            3. 将所有项写入 Byzer Storage，并设置向量和搜索字段
            4. 提交更改以确保数据持久化
            
        注意:
            - 该方法在删除文件前会先从数据库中删除所有相关记录，避免残留
            - 文件内容会被分块处理，每个块独立存储和索引
            - 向量字段用于相似度搜索，content字段用于全文搜索
        """
        query = self.storage.query_builder()
        query.and_filter().add_condition("file_path", file_info.file_path).build()
        results = query.execute()
        if results:
            for result in results:
                self.storage.delete_by_ids([result["_id"]])
        items = []

        if not is_delete:
            content = [
                SourceCode.model_validate(doc)
                for doc in self.cache[file_info.file_path].content
            ]
            modify_time = self.cache[file_info.file_path].modify_time
            for doc in content:
                logger.info(f"Processing file: {doc.module_name}")
                doc.module_name
                chunks = self._chunk_text(doc.source_code, self.chunk_size)
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_item = {
                        "_id": f"{doc.module_name}_{chunk_idx}",
                        "file_path": file_info.file_path,
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
                    # 创建一个临时的 FileInfo 对象
                    file_info = FileInfo(
                        file_path=item, relative_path="", modify_time=0, file_md5="")
                    self.update_storage(file_info, is_delete=True)

            elif isinstance(file_list, AddOrUpdateEvent):
                for file_info in file_list.file_infos:
                    logger.info(
                        f"{file_info.file_path} is detected to be updated")
                    # 处理文件并创建 CacheItem
                    content = process_file_local(
                        self.fileinfo_to_tuple(file_info))
                    self.cache[file_info.file_path] = CacheItem(
                        file_path=file_info.file_path,
                        relative_path=file_info.relative_path,
                        content=[c.model_dump() for c in content],
                        modify_time=file_info.modify_time,
                        md5=file_info.file_md5,
                    )
                    self.update_storage(file_info, is_delete=False)
            self.write_cache()

    def trigger_update(self):
        logger.info("检查文件是否有更新.....")
        files_to_process = []
        current_files = set()
        for file_info in self.get_all_files():
            current_files.add(file_info.file_path)
            if (
                file_info.file_path not in self.cache
                or self.cache[file_info.file_path].md5 != file_info.file_md5
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
                self.queue.append(AddOrUpdateEvent(
                    file_infos=files_to_process))

    def get_single_cache(self, query: str, options: Dict[str, Any]) -> Dict[str, Dict]:
        """Search cached documents using query"""
        
        total_tokens = 0
        logger.info(f"查询缓存 query: {query}")
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

        logger.info(f"从缓存获取: {len(results)} 条数据")
        # Preview first 5 results with all fields but limited content size
        preview_results = []
        for r in results[:5]:
            # Create a copy of the entire result
            preview = r.copy()            
            # Similarly limit raw_content if it exists
            if "raw_content" in preview and isinstance(preview["raw_content"], str):
                preview["raw_content"] = preview["raw_content"][:100] + "..." if len(preview["raw_content"]) > 100 else preview["raw_content"]
            preview_results.append(preview)
        logger.info(f"预览前5条数据:")
        
        for r in preview_results:
            logger.info(f"文件路径: {r['file_path']}")            
            logger.info(f"原始内容: {r['raw_content']}")
            # 打印其他字段
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
        if "query" not in options and "queries" not in options:
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
            logger.warning(f"未知的合并策略: {merge_strategy_name}，使用默认策略")
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
                    logger.info(f"查询 '{query}' 返回 {len(query_result)} 条结果")
                    query_results.append((query, query_result))
                except Exception as e:
                    logger.error(f"处理查询 '{query}' 时出错: {str(e)}")
        
        logger.info(f"所有查询共返回 {sum(len(r) for _, r in query_results)} 条结果")
        logger.info(f"使用合并策略: {merge_strategy}")
        
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
                        logger.info(f"用户tokens设置为:{self.max_output_tokens}，累计tokens: {total_tokens} 当前文件: {file_path} tokens: {doc['tokens']}，数据条数变化: {len(results)} -> {len(result)}")
                        return result
                    total_tokens += doc["tokens"]
                result[file_path] = cached_data.model_dump()
        
        logger.info(f"用户tokens设置为:{self.max_output_tokens}，累计tokens: {total_tokens}，数据条数变化: {len(results)} -> {len(result)}")
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
