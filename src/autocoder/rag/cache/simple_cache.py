
from multiprocessing import Pool
from autocoder.common import SourceCode
from autocoder.rag.cache.base_cache import BaseCacheManager, DeleteEvent, AddOrUpdateEvent
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
    def __init__(self, path: str, ignore_spec, required_exts: list):
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.queue = []
        self.cache = {}
        self.lock = threading.Lock()
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._process_queue)
        self.thread.daemon = True
        self.thread.start()
        self.cache = self.read_cache()

    def _process_queue(self):
        while not self.stop_event.is_set():
            try:
                self.process_queue()
            except Exception as e:
                logger.error(f"Error in process_queue: {e}")
            time.sleep(1)  # 避免过于频繁的检查

    def stop(self):
        self.stop_event.set()
        self.thread.join()

    def __del__(self):
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
                    or self.cache[file_path].get("md5","") != file_md5
                ):
                    files_to_process.append(file_info)
            if not files_to_process:
                return
            # remote_process_file = ray.remote(process_file)
            # results = ray.get(
            #     [process_file.remote(file_info) for file_info in files_to_process]
            # )
            from autocoder.rag.token_counter import initialize_tokenizer

            with Pool(
                processes=os.cpu_count(),
                initializer=initialize_tokenizer,
                initargs=(VariableHolder.TOKENIZER_PATH,),
            ) as pool:
                results = pool.map(
                    process_file_in_multi_process, files_to_process)

            for file_info, result in zip(files_to_process, results):
                if result:  # 只有当result不为空时才更新缓存
                    self.update_cache(file_info, result)
                else:
                    logger.warning(f"Empty result for file: {file_info[0]}, skipping cache update")

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
                or self.cache[file_path].get("md5","") != file_md5
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

    def process_queue(self):
        while self.queue:
            file_list = self.queue.pop(0)
            if isinstance(file_list, DeleteEvent):
                for item in file_list.file_paths:
                    logger.info(f"{item} is detected to be removed")
                    del self.cache[item]
            elif isinstance(file_list, AddOrUpdateEvent):
                for file_info in file_list.file_infos:
                    logger.info(f"{file_info[0]} is detected to be updated")
                    try:
                        result = process_file_local(file_info[0])
                        if result:  # 只有当result不为空时才更新缓存
                            self.update_cache(file_info, result)
                        else:
                            logger.warning(f"Empty result for file: {file_info[0]}, skipping cache update")
                    except Exception as e:
                        logger.error(
                            f"SimpleCache Error in process_queue: {e}")

            self.write_cache()

    def read_cache(self) -> Dict[str, Dict]:
        cache_dir = os.path.join(self.path, ".cache")
        cache_file = os.path.join(cache_dir, "cache.jsonl")

        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)

        cache = {}
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                for line in f:
                    data = json.loads(line)
                    cache[data["file_path"]] = data
        return cache

    def write_cache(self):
        cache_dir = os.path.join(self.path, ".cache")
        cache_file = os.path.join(cache_dir, "cache.jsonl")

        if not fcntl:
            with open(cache_file, "w") as f:
                for data in self.cache.values():
                    try:
                        json.dump(data, f, ensure_ascii=False)
                        f.write("\n")
                    except Exception as e:
                        logger.error(
                            f"Failed to write {data['file_path']} to .cache/cache.jsonl: {e}")
        else:
            lock_file = cache_file + ".lock"
            with open(lock_file, "w") as lockf:
                try:
                    # 获取文件锁
                    fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    # 写入缓存文件
                    with open(cache_file, "w") as f:
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
        self.trigger_update()
        return self.cache

    def get_all_files(self) -> List[Tuple[str, str, float]]:
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
