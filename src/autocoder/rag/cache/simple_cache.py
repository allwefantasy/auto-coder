from multiprocessing import Pool
import functools
from autocoder.common import SourceCode
from autocoder.rag.cache.base_cache import (
    BaseCacheManager, DeleteEvent, AddOrUpdateEvent,
    FileInfo,
    CacheItem
)
from typing import Dict, List, Tuple, Any, Optional, Union
import os
import threading
import json
import platform
if platform.system() != "Windows":
    import fcntl
else:
    fcntl = None
import time
from loguru import logger
from autocoder.rag.utils import process_file_in_multi_process, process_file_local
from autocoder.rag.variable_holder import VariableHolder
import hashlib
from .failed_files_utils import load_failed_files, save_failed_files
from autocoder.common import AutoCoderArgs
from byzerllm import SimpleByzerLLM, ByzerLLM
from autocoder.utils.llms import get_llm_names
from autocoder.common.file_monitor.monitor import get_file_monitor, Change


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


def generate_content_md5(content: Union[str, bytes]) -> str:
    if isinstance(content, str):
        content = content.encode("utf-8")
    md5_hash = hashlib.md5()
    md5_hash.update(content)
    return md5_hash.hexdigest()


class AutoCoderRAGAsyncUpdateQueue(BaseCacheManager):
    def __init__(self, path: str, ignore_spec, required_exts: list, args: Optional[AutoCoderArgs] = None, llm: Optional[Union[ByzerLLM, SimpleByzerLLM, str]] = None):
        """
        初始化异步更新队列，用于管理代码文件的缓存。

        参数:
            path: 需要索引的代码库根目录
            ignore_spec: 指定哪些文件/目录应被忽略的规则
            required_exts: 需要处理的文件扩展名列表
            args: AutoCoderArgs 对象，包含配置信息
            llm: 用于代码分析的 LLM 实例

        缓存结构 (self.cache):
            self.cache 是一个字典，其结构如下:
            {
                "file_path1": {                    # 键为文件的绝对路径
                    "file_path": str,              # 文件的绝对路径
                    "relative_path": str,          # 相对于项目根目录的路径
                    "content": List[Dict],         # 文件内容的结构化表示，每个元素是 SourceCode 对象的序列化
                    "modify_time": float,          # 文件最后修改时间的时间戳
                    "md5": str                     # 文件内容的 MD5 哈希值，用于检测变更
                },
                "file_path2": { ... },
                ...
            }

            这个缓存保存在项目根目录的 .cache/cache.jsonl 文件中，采用 JSONL 格式存储。
            每次启动时从磁盘加载，并在文件变更时异步更新。

        源代码处理函数:
            在缓存更新过程中使用了两个关键函数:

            1. process_file_in_multi_process: 在多进程环境中处理文件
               - 参数: file_info (文件信息元组)
               - 返回值: List[SourceCode] 或 None
               - 用途: 在初始加载时并行处理多个文件

            2. process_file_local: 在当前进程中处理单个文件
               - 参数: file_path (文件路径)
               - 返回值: List[SourceCode] 或 None
               - 用途: 在检测到文件更新时处理单个文件

            这两个函数返回的 SourceCode 对象列表会通过 model_dump() 方法序列化为字典，
            然后存储在缓存的 "content" 字段中。如果返回为空，则跳过缓存更新。
        """
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.args = args
        self.llm = llm
        self.product_mode = args.product_mode or "lite"
        self.queue = []
        self.cache = {}  # 初始化为空字典，稍后通过 read_cache() 填充
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        # 用于存放解析失败的文件路径集合
        self.failed_files_path = os.path.join(
            self.path, ".cache", "failed_files.json")
        self.failed_files = load_failed_files(self.failed_files_path)

        # 启动处理队列的线程
        self.queue_thread = threading.Thread(target=self._process_queue)
        self.queue_thread.daemon = True
        self.queue_thread.start()

        # 注册文件监控回调
        self.file_monitor = get_file_monitor(self.path)
        # 注册根目录的监控，这样可以捕获所有子目录和文件的变化
        self.file_monitor.register(self.path, self._on_file_change)
        # 确保监控器已启动
        if not self.file_monitor.is_running():
            self.file_monitor.start()
            logger.info(f"Started file monitor for {self.path}")
        else:
            logger.info(f"File monitor already running for {self.path}")

        self.cache = self.read_cache()

    def _process_queue(self):
        while not self.stop_event.is_set():
            try:
                self.process_queue()
            except Exception as e:
                logger.error(f"Error in process_queue: {e}")
            time.sleep(1)  # 避免过于频繁的检查

    def _on_file_change(self, change_type: Change, file_path: str):
        """
        文件监控回调函数，当文件发生变化时触发更新
        
        参数:
            change_type: 变化类型 (Change.added, Change.modified, Change.deleted)
            file_path: 发生变化的文件路径
        """
        try:
            # 如果缓存还没有初始化，跳过触发
            if not self.cache:
                return
                
            # 检查文件扩展名，如果不在需要处理的扩展名列表中，跳过
            if self.required_exts and not any(file_path.endswith(ext) for ext in self.required_exts):
                return
                
            # 检查是否在忽略规则中
            if self.ignore_spec and self.ignore_spec.match_file(os.path.relpath(file_path, self.path)):
                return
                
            logger.info(f"File change detected: {change_type} - {file_path}")
            self.trigger_update()
        except Exception as e:
            logger.error(f"Error in file change handler: {e}")
            logger.exception(e)

    def stop(self):
        self.stop_event.set()
        # 取消注册文件监控回调
        try:
            self.file_monitor.unregister(self.path, self._on_file_change)
            logger.info(f"Unregistered file monitor callback for {self.path}")
        except Exception as e:
            logger.error(f"Error unregistering file monitor callback: {e}")
        # 只等待队列处理线程结束
        if hasattr(self, 'queue_thread') and self.queue_thread.is_alive():
            self.queue_thread.join(timeout=2.0)

    def fileinfo_to_tuple(self, file_info: FileInfo) -> Tuple[str, str, float, str]:
        return (file_info.file_path, file_info.relative_path, file_info.modify_time, file_info.file_md5)

    def __del__(self):
        # 确保在对象被销毁时停止监控并清理资源
        self.stop()

    def load_first(self):
        with self.lock:
            if self.cache:
                return
            files_to_process = []            
            for file_info in self.get_all_files():
                file_path, _, modify_time, file_md5 = file_info
                if (
                    file_path not in self.cache
                    or self.cache[file_path].get("md5", "") != file_md5
                ):
                    files_to_process.append(file_info)
            if not files_to_process:
                return
            # remote_process_file = ray.remote(process_file)
            # results = ray.get(
            #     [process_file.remote(file_info) for file_info in files_to_process]
            # )
            from autocoder.rag.token_counter import initialize_tokenizer
            llm_name = get_llm_names(self.llm)[0] if self.llm else None            
            with Pool(
                processes=os.cpu_count(),
                initializer=initialize_tokenizer,
                initargs=(VariableHolder.TOKENIZER_PATH,),
            ) as pool:
                
                worker_func = functools.partial(
                    process_file_in_multi_process, llm=llm_name, product_mode=self.product_mode)
                results = pool.map(worker_func, files_to_process)            
            
            for file_info, result in zip(files_to_process, results):
                if result:  # 只有当result不为空时才更新缓存
                    self.update_cache(file_info, result)
                else:
                    logger.warning(
                        f"Empty result for file: {file_info[0]}, skipping cache update")

            self.write_cache()

    def trigger_update(self):
        logger.info("检查文件是否有更新.....")
        files_to_process = []
        current_files = set()
        for file_info in self.get_all_files():
            file_path, relative_path, modify_time, file_md5 = file_info
            current_files.add(file_path)
            # 如果文件曾经解析失败，跳过本次增量更新
            if file_path in self.failed_files:                
                continue
            # 变更检测            
            if (
                file_path not in self.cache
                or self.cache[file_path].get("md5", "") != file_md5
            ):
                files_to_process.append(
                    (file_path, relative_path, modify_time, file_md5))            

        deleted_files = set(self.cache.keys()) - current_files
        logger.info(f"files_to_process: {files_to_process}")
        logger.info(f"deleted_files: {deleted_files}")
        if deleted_files:
            with self.lock:
                self.queue.append(DeleteEvent(file_paths=deleted_files))
        if files_to_process:
            with self.lock:
                self.queue.append(AddOrUpdateEvent(
                    file_infos=[FileInfo(
                        file_path=item[0],
                        relative_path=item[1],
                        modify_time=item[2],
                        file_md5=item[3]
                    ) for item in files_to_process]))

    def process_queue(self):
        while self.queue:
            file_list = self.queue.pop(0)
            if isinstance(file_list, DeleteEvent):
                for item in file_list.file_paths:
                    logger.info(f"{item} is detected to be removed")
                    if item in self.cache:
                        del self.cache[item]
                    # 删除时也从失败列表中移除（防止文件已修复）
                    if item in self.failed_files:
                        self.failed_files.remove(item)
                        save_failed_files(
                            self.failed_files_path, self.failed_files)
            elif isinstance(file_list, AddOrUpdateEvent):
                for file_info in file_list.file_infos:
                    logger.info(
                        f"{file_info.file_path} is detected to be updated")
                    try:
                        result = process_file_local(
                            file_info.file_path, llm=self.llm, product_mode=self.product_mode)
                        if result:
                            # 解析成功且非空
                            self.update_cache(
                                self.fileinfo_to_tuple(file_info), result)
                            # 如果之前失败过且本次成功，移除失败记录
                            if file_info.file_path in self.failed_files:
                                self.failed_files.remove(file_info.file_path)
                                save_failed_files(
                                    self.failed_files_path, self.failed_files)
                        else:
                            # 只要为空也认为解析失败，加入失败列表
                            logger.warning(
                                f"Empty result for file: {file_info.file_path}, treat as parse failed, skipping cache update")
                            self.failed_files.add(file_info.file_path)
                            save_failed_files(
                                self.failed_files_path, self.failed_files)
                    except Exception as e:
                        logger.error(
                            f"SimpleCache Error in process_queue: {e}")
                        # 解析失败则加入失败列表
                        self.failed_files.add(file_info.file_path)
                        save_failed_files(
                            self.failed_files_path, self.failed_files)

            self.write_cache()

    def read_cache(self) -> Dict[str, Dict]:
        cache_dir = os.path.join(self.path, ".cache")
        cache_file = os.path.join(cache_dir, "cache.jsonl")

        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        cache = {}
        if os.path.exists(cache_file):
            with open(cache_file, "r", encoding="utf-8") as f:
                for line in f:
                    data = json.loads(line)
                    cache[data["file_path"]] = data
        else:
            self.load_first()            
        return cache

    def write_cache(self):
        cache_dir = os.path.join(self.path, ".cache")
        cache_file = os.path.join(cache_dir, "cache.jsonl")

        if not fcntl:
            with open(cache_file, "w", encoding="utf-8") as f:
                for data in self.cache.values():
                    try:
                        json.dump(data, f, ensure_ascii=False)
                        f.write("\n")
                    except Exception as e:
                        logger.error(
                            f"Failed to write {data['file_path']} to .cache/cache.jsonl: {e}")
        else:
            lock_file = cache_file + ".lock"
            with open(lock_file, "w", encoding="utf-8") as lockf:
                try:
                    # 获取文件锁
                    fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # 写入缓存文件
                    with open(cache_file, "w", encoding="utf-8") as f:
                        for data in self.cache.values():
                            try:
                                json.dump(data, f, ensure_ascii=False)
                                f.write("\n")
                            except Exception as e:
                                logger.error(
                                    f"Failed to write {data['file_path']} to .cache/cache.jsonl: {e}")

                finally:
                    # 释放文件锁
                    fcntl.flock(lockf, fcntl.LOCK_UN)

    def update_cache(
        self, file_info: Tuple[str, str, float, str], content: List[SourceCode]
    ):
        """
        更新缓存中的文件信息。

        参数:
            file_info: 包含文件信息的元组 (file_path, relative_path, modify_time, file_md5)
            content: 解析后的文件内容，SourceCode 对象列表

        说明:
            此方法将文件的最新内容更新到缓存中。缓存项的结构为:
            {
                "file_path": str,              # 文件的绝对路径
                "relative_path": str,          # 相对于项目根目录的路径
                "content": List[Dict],         # 文件内容的结构化表示，每个元素是 SourceCode 对象的序列化结果
                "modify_time": float,          # 文件最后修改时间的时间戳
                "md5": str                     # 文件内容的 MD5 哈希值，用于检测变更
            }

            该方法不会立即写入磁盘，需调用 write_cache() 方法将更新后的缓存持久化。
        """
        file_path, relative_path, modify_time, file_md5 = file_info
        self.cache[file_path] = {
            "file_path": file_path,
            "relative_path": relative_path,
            "content": [c.model_dump() for c in content],
            "modify_time": modify_time,
            "md5": file_md5,
        }

    def get_cache(self, options: Optional[Dict[str, Any]] = None):
        self.load_first()
        # 不再在这里触发更新，因为已经有定时线程在处理
        return self.cache

    def get_all_files(self) -> List[Tuple[str, str, float]]:
        all_files = []
        for root, dirs, files in os.walk(self.path, followlinks=True):
            dirs[:] = [d for d in dirs if not d.startswith(
                ".") and d not in default_ignore_dirs]

            # Filter out files that start with a dot
            files[:] = [f for f in files if not f.startswith(".")]

            if self.ignore_spec:
                relative_root = os.path.relpath(root, self.path)
                dirs[:] = [
                    d
                    for d in dirs
                    if not self.ignore_spec.match_file(os.path.join(relative_root, d))
                ]
                files[:] = [
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
                    (file_path, relative_path, modify_time, file_md5))        
        return all_files
