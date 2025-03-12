import hashlib
import json
import os
import time
import platform
import threading
from multiprocessing import Pool
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional, Tuple, Union
import numpy as np
from loguru import logger

try:
    import duckdb
except ImportError:
    logger.error("DuckDB is not installed, please install it using 'pip install duckdb'")
    raise

from autocoder.common import AutoCoderArgs
from autocoder.common import SourceCode
from autocoder.rag.cache.base_cache import (
    BaseCacheManager,
    DeleteEvent,
    AddOrUpdateEvent,
    FileInfo,
    CacheItem
)
from autocoder.rag.utils import process_file_in_multi_process, process_file_local
from autocoder.rag.variable_holder import VariableHolder
from byzerllm import SimpleByzerLLM, ByzerLLM

if platform.system() != "Windows":
    import fcntl
else:
    fcntl = None


default_ignore_dirs = [
    "__pycache__",
    "node_modules",
    "_images"
]


def generate_file_md5(file_path: str) -> str:
    md5_hash = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5_hash.update(chunk)
    return md5_hash.hexdigest()


class DuckDBLocalContext:
    def __init__(self, database_path: str):
        self.database_path = database_path
        self._conn = None

    def _install_load_extension(self, ext_list):
        for ext in ext_list:
            self._conn.install_extension(ext)
            self._conn.load_extension(ext)

    def __enter__(self) -> "duckdb.DuckDBPyConnection":
        if not os.path.exists(os.path.dirname(self.database_path)):
            raise ValueError(
                f"Directory {os.path.dirname(self.database_path)} does not exist."
            )

        self._conn = duckdb.connect(self.database_path)
        self._install_load_extension(["json", "fts", "vss"])

        return self._conn

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        if self._conn:
            self._conn.close()


class LocalDuckdbStorage:

    def __init__(
            self, llm: Union[ByzerLLM, SimpleByzerLLM] = None, database_name: str = ":memory:", table_name: str = "documents",
            embed_dim: Optional[int] = None, persist_dir: str = "./storage"
    ) -> None:
        self.llm = llm
        self.database_name = database_name
        self.table_name = table_name
        self.embed_dim = embed_dim
        self.persist_dir = persist_dir
        self.cache_dir = os.path.join(self.persist_dir, '.cache')
        logger.info(f"正在启动 DuckDBVectorStore.")

        if self.database_name != ":memory:":
            self.database_path = os.path.join(self.cache_dir, self.database_name)

        if self.database_name == ":memory:":
            self._conn = duckdb.connect(self.database_name)
            self._install_load_extension(["json", "fts", "vss"])
            self._initialize()
        else:
            if not os.path.exists(self.database_path):
                if not os.path.exists(self.cache_dir):
                    os.makedirs(self.cache_dir)
                self._initialize()
            self._conn = None
        logger.info(f"DuckDBVectorStore 初始化完成, 存储目录: {self.cache_dir}, "
                    f"数据库名称: {self.database_name}, 数据表名称: {self.table_name}")

    @classmethod
    def class_name(cls) -> str:
        return "DuckDBVectorStore"

    @property
    def client(self) -> Any:
        """Return client."""
        return self._conn

    def _install_load_extension(self, ext_list):
        for ext in ext_list:
            self._conn.install_extension(ext)
            self._conn.load_extension(ext)

    @staticmethod
    def _apply_pca(embedding, target_dim):
        # 生成固定随机投影矩阵（避免每次调用重新生成）
        np.random.seed(42)  # 固定随机种子保证一致性
        source_dim = len(embedding)
        projection_matrix = np.random.randn(source_dim, target_dim) / np.sqrt(source_dim)

        # 执行投影
        reduced = np.dot(embedding, projection_matrix)
        return reduced

    def _embedding(self, context: str, norm: bool = True, dim: int | None = None) -> List[float]:
        embedding = self.llm.emb_query(context)[0].output

        if dim:
            embedding = self._apply_pca(embedding, target_dim=dim)  # 降维后形状 (1024,)

        if norm:
            embedding = embedding / np.linalg.norm(embedding)

        return embedding.tolist()

    def _initialize(self) -> None:
        if self.embed_dim is None:
            _query = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    _id VARCHAR,
                    file_path VARCHAR,
                    content TEXT,
                    raw_content TEXT,
                    vector FLOAT[],
                    mtime FLOAT
                );
            """
        else:
            _query = f"""
                CREATE TABLE IF NOT EXISTS {self.table_name} (
                    _id VARCHAR,
                    file_path VARCHAR,
                    content TEXT,
                    raw_content TEXT,
                    vector FLOAT[],
                    mtime FLOAT
                );
            """

        if self.database_name == ":memory:":
            self._conn.execute(_query)
        elif self.database_path is not None:
            with DuckDBLocalContext(self.database_path) as _conn:
                _conn.execute(_query)

    def truncate_table(self):
        _truncate_query = f"""TRUNCATE TABLE {self.table_name};"""
        if self.database_name == ":memory:":
            self._conn.execute(_truncate_query)
        elif self.database_path is not None:
            with DuckDBLocalContext(self.database_path) as _conn:
                _conn.execute(_truncate_query)

    def query_by_path(self, file_path: str):
        _exists_query = f"""SELECT _id FROM {self.table_name} WHERE file_path = ?"""
        query_params = [
            file_path
        ]
        _final_results = []
        if self.database_name == ":memory:":
            _final_results = self._conn.execute(_exists_query, query_params).fetchall()
        elif self.database_path is not None:
            with DuckDBLocalContext(self.database_path) as _conn:
                _final_results = _conn.execute(_exists_query, query_params).fetchall()
        return _final_results

    def delete_by_ids(self, _ids: List[str]):
        _delete_query = f"""DELETE FROM {self.table_name} WHERE _id IN (?);"""
        query_params = [
            ','.join(_ids)
        ]
        if self.database_name == ":memory:":
            _final_results = self._conn.execute(_delete_query, query_params).fetchall()
        elif self.database_path is not None:
            with DuckDBLocalContext(self.database_path) as _conn:
                _final_results = _conn.execute(_delete_query, query_params).fetchall()
        return _final_results

    def _node_to_table_row(self, context_chunk: Dict[str, str | float], dim: int | None = None) -> Any:
        return (
            context_chunk["_id"],
            context_chunk["file_path"],
            context_chunk["content"],
            context_chunk["raw_content"],
            self._embedding(context_chunk["raw_content"], norm=True, dim=dim),
            context_chunk["mtime"]
        )

    def add_doc(self, context_chunk: Dict[str, str | float], dim: int | None = None):
        """
        {
            "_id": f"{doc.module_name}_{chunk_idx}",
            "file_path": file_info.file_path,
            "content": chunk,
            "raw_content": chunk,
            "vector": chunk,
            "mtime": file_info.modify_time,
        }
        """
        if self.database_name == ":memory:":
            _table = self._conn.table(self.table_name)
            _row = self._node_to_table_row(context_chunk, dim=dim)
            _table.insert(_row)
        elif self.database_path is not None:
            with DuckDBLocalContext(self.database_path) as _conn:
                _table = _conn.table(self.table_name)
                _row = self._node_to_table_row(context_chunk, dim=dim)
                _table.insert(_row)

    def vector_search(
            self, query: str, similarity_value: float = 0.7, similarity_top_k: int = 10, query_dim: int | None = None
    ):
        """
        list_cosine_similarity: 计算两个列表之间的余弦相似度
        list_cosine_distance: 计算两个列表之间的余弦距离
        list_dot_product: 计算两个大小相同的数字列表的点积
        """
        _db_query = f"""
            SELECT _id, file_path, mtime, score
            FROM (
                SELECT *, list_cosine_similarity(vector, ?) AS score
                FROM {self.table_name}
            ) sq
            WHERE score IS NOT NULL
            AND score >= ?
            ORDER BY score DESC LIMIT ?;
        """
        query_params = [
            self._embedding(query, norm=True, dim=query_dim),
            similarity_value,
            similarity_top_k,
        ]

        _final_results = []
        if self.database_name == ":memory:":
            _final_results = self._conn.execute(_db_query, query_params).fetchall()
        elif self.database_path is not None:
            with DuckDBLocalContext(self.database_path) as _conn:
                _final_results = _conn.execute(_db_query, query_params).fetchall()
        return _final_results


efault_ignore_dirs = [
    "__pycache__",
    "node_modules",
    "_images"
]


class LocalDuckDBStorageCache(BaseCacheManager):
    def __init__(
            self,
            path,
            ignore_spec,
            required_exts,
            extra_params: Optional[AutoCoderArgs] = None,
            emb_llm: Union[ByzerLLM, SimpleByzerLLM] = None
    ):
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.extra_params = extra_params

        self.storage = LocalDuckdbStorage(
            llm=emb_llm,
            database_name="byzerai_store_duckdb.db",
            table_name="rag_duckdb",
            persist_dir=self.path
        )
        self.queue = []
        self.chunk_size = 1000
        self.max_output_tokens = extra_params.hybrid_index_max_output_tokens

        # 设置缓存文件路径
        self.cache_dir = os.path.join(self.path, ".cache")
        self.cache_file = os.path.join(self.cache_dir, "duckdb_storage_speedup.jsonl")
        self.cache: Dict[str, CacheItem] = {}
        # 创建缓存目录
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)

        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self.process_queue)
        self.thread.daemon = True
        self.thread.start()

        # 加载缓存
        self.cache = self._load_cache()

    @staticmethod
    def _chunk_text(text, max_length=1000):
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
                        json.dump(cache_item.model_dump(), f, ensure_ascii=False)
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
                            json.dump(cache_item.model_dump(), f, ensure_ascii=False)
                            f.write("\n")

                finally:
                    # 释放文件锁
                    fcntl.flock(lockf, fcntl.LOCK_UN)

    @staticmethod
    def fileinfo_to_tuple(file_info: FileInfo) -> Tuple[str, str, float, str]:
        return file_info.file_path, file_info.relative_path, file_info.modify_time, file_info.file_md5

    def build_cache(self):
        """Build the cache by reading files and storing in DuckDBVectorStore"""
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
                chunks = self._chunk_text(doc.source_code, self.chunk_size)
                for chunk_idx, chunk in enumerate(chunks):
                    chunk_item = {
                        "_id": f"{doc.module_name}_{chunk_idx}",
                        "file_path": file_info.file_path,
                        "content": chunk,
                        "raw_content": chunk,
                        "vector": "",
                        "mtime": file_info.modify_time,
                    }
                    items.append(chunk_item)

        # Save to local cache
        logger.info("Saving cache to local file")
        self.write_cache()

        if items:
            logger.info("Clear cache from Byzer DuckDB Storage")
            self.storage.truncate_table()
            logger.info("Save new cache to Byzer DuckDB Storage")

            total_chunks = len(items)
            completed_chunks = 0

            logger.info(f"进度: 已完成 {0}/{total_chunks} 个文本块")

            for _chunk in items:
                try:
                    self.storage.add_doc(_chunk, dim=self.extra_params.rag_duckdb_vector_dim)
                    completed_chunks += 1
                    logger.info(f"进度: 已完成 {completed_chunks}/{total_chunks} 个文本块")
                    time.sleep(self.extra_params.anti_quota_limit)
                except Exception as err:
                    logger.error(f"Error in saving chunk: {str(err)}")

    def update_storage(self, file_info: FileInfo, is_delete: bool):
        results = self.storage.query_by_path(file_info.file_path)
        if results:  # [('_id',)]
            for result in results:
                self.storage.delete_by_ids([result[0]])

        items = []
        if not is_delete:
            content = [
                SourceCode.model_validate(doc) for doc in self.cache[file_info.file_path].content
            ]
            modify_time = self.cache[file_info.file_path].modify_time
            for doc in content:
                logger.info(f"正在处理更新文件: {doc.module_name}")
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
            for _chunk in items:
                try:
                    self.storage.add_doc(_chunk, dim=self.extra_params.rag_duckdb_vector_dim)
                    time.sleep(self.extra_params.anti_quota_limit)
                except Exception as err:
                    logger.error(f"Error in saving chunk: {str(err)}")

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
                    # content = process_file_local(
                    #     self.fileinfo_to_tuple(file_info))
                    content = process_file_local(file_info.file_path)
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
        logger.info(f"待处理的文件: {len(files_to_process)}个")
        logger.info(f"已删除的文件: {len(deleted_files)}个")
        if deleted_files:
            with self.lock:
                self.queue.append(DeleteEvent(file_paths=deleted_files))
        if files_to_process:
            with self.lock:
                self.queue.append(AddOrUpdateEvent(file_infos=files_to_process))

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
                all_files.append(
                    FileInfo(
                        file_path=file_path,
                        relative_path=relative_path,
                        modify_time=modify_time,
                        file_md5=file_md5))

        return all_files

    def get_cache(self, options: Optional[Dict[str, Any]] = None) -> Dict[str, Dict]:
        """Search cached documents using query"""
        self.trigger_update()  # 检查更新

        if options is None or "query" not in options:
            return {file_path: self.cache[file_path].model_dump() for file_path in self.cache}

        query = options.get("query", "")
        logger.info(f"正在使用向量搜索检索数据, 你的问题: {query}")
        total_tokens = 0
        results = []

        # Add vector search if enabled
        if options.get("enable_vector_search", True):
            # 返回值包含  [(_id, file_path, mtime, score,),]
            # results = self.storage.vector_search(query, similarity_value=0.7, similarity_top_k=200)
            search_results = self.storage.vector_search(
                query,
                similarity_value=self.extra_params.duckdb_query_similarity,
                similarity_top_k=self.extra_params.duckdb_query_top_k,
                query_dim=self.extra_params.duckdb_vector_dim
            )
            results.extend(search_results)

        # Group results by file_path and reconstruct documents while preserving order
        # 这里还可以有排序优化，综合考虑一篇内容出现的次数以及排序位置
        file_paths = []
        seen = set()
        for result in results:
            _id, _file_path, _mtime, _score = result
            if _file_path not in seen:
                seen.add(_file_path)
                file_paths.append(_file_path)

        # 从缓存中获取文件内容
        result = {}
        for file_path in file_paths:
            if file_path in self.cache:
                cached_data = self.cache[file_path]
                for doc in cached_data.content:
                    if total_tokens + doc["tokens"] > self.max_output_tokens:
                        logger.info(
                            f"当前检索已超出用户设置 Hybrid Index Max Tokens:{self.max_output_tokens}，"
                            f"累计tokens: {total_tokens}, "
                            f"经过向量搜索共检索出 {len(result.keys())} 个文档, 共 {len(self.cache.keys())} 个文档")
                        return result
                    total_tokens += doc["tokens"]
                result[file_path] = cached_data.model_dump()
        logger.info(
            f"用户Hybrid Index Max Tokens设置为:{self.max_output_tokens}，"
            f"累计tokens: {total_tokens}, "
            f"经过向量搜索共检索出 {len(result.keys())} 个文档, 共 {len(self.cache.keys())} 个文档")
        return result