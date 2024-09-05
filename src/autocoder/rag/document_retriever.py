import os
import json
import time
import platform

if platform.system() != "Windows":
    import fcntl
else:
    fcntl = None
from typing import Generator, List, Tuple, Dict
from autocoder.common import SourceCode
from autocoder.rag.loaders import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_excel,
    extract_text_from_ppt,
)
from loguru import logger
import threading
from multiprocessing import Pool
import ray
from pydantic import BaseModel

cache_lock = threading.Lock()


class DeleteEvent(BaseModel):
    file_paths: List[str]


class AddOrUpdateEvent(BaseModel):
    file_infos: List[Tuple[str, str, float]]


@ray.remote
def process_file(file_info: Tuple[str, str, float]) -> List[SourceCode]:
    start_time = time.time()
    file_path, relative_path, _ = file_info
    try:
        if file_path.endswith(".pdf"):
            with open(file_path, "rb") as f:
                content = extract_text_from_pdf(f.read())
            v = [SourceCode(module_name=file_path, source_code=content)]
        elif file_path.endswith(".docx"):
            with open(file_path, "rb") as f:
                content = extract_text_from_docx(f.read())
            v = [SourceCode(module_name=f"##File: {file_path}", source_code=content)]
        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            sheets = extract_text_from_excel(file_path)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}#{sheet[0]}",
                    source_code=sheet[1],
                )
                for sheet in sheets
            ]
        elif file_path.endswith(".pptx"):
            slides = extract_text_from_ppt(file_path)
            content = "".join(f"#{slide[0]}\n{slide[1]}\n\n" for slide in slides)
            v = [SourceCode(module_name=f"##File: {file_path}", source_code=content)]
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            v = [SourceCode(module_name=f"##File: {file_path}", source_code=content)]
        logger.info(f"Load file {file_path} in {time.time() - start_time}")
        return v
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        return []


def process_file2(file_info: Tuple[str, str, float]) -> List[SourceCode]:
    start_time = time.time()
    file_path, relative_path, _ = file_info
    try:
        if file_path.endswith(".pdf"):
            with open(file_path, "rb") as f:
                content = extract_text_from_pdf(f.read())
            v = [SourceCode(module_name=file_path, source_code=content)]
        elif file_path.endswith(".docx"):
            with open(file_path, "rb") as f:
                content = extract_text_from_docx(f.read())
            v = [SourceCode(module_name=f"##File: {file_path}", source_code=content)]
        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            sheets = extract_text_from_excel(file_path)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}#{sheet[0]}",
                    source_code=sheet[1],
                )
                for sheet in sheets
            ]
        elif file_path.endswith(".pptx"):
            slides = extract_text_from_ppt(file_path)
            content = "".join(f"#{slide[0]}\n{slide[1]}\n\n" for slide in slides)
            v = [SourceCode(module_name=f"##File: {file_path}", source_code=content)]
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            v = [SourceCode(module_name=f"##File: {file_path}", source_code=content)]
        logger.info(f"Load file {file_path} in {time.time() - start_time}")
        return v
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        return []


class AutoCoderRAGAsyncUpdateQueue:
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
                file_path, _, modify_time = file_info
                if (
                    file_path not in self.cache
                    or self.cache[file_path]["modify_time"] < modify_time
                ):
                    files_to_process.append(file_info)
            if not files_to_process:
                return
            # remote_process_file = ray.remote(process_file)
            # results = ray.get(
            #     [process_file.remote(file_info) for file_info in files_to_process]
            # )
            with Pool(processes=os.cpu_count()) as pool:
                results = pool.map(process_file2, files_to_process)

            for file_info, result in zip(files_to_process, results):
                self.update_cache(file_info, result)                    
            
            self.write_cache()

    def trigger_update(self):
        logger.info("检查文件是否有更新.....")
        files_to_process = []
        current_files = set()
        for file_info in self.get_all_files():
            file_path, _, modify_time = file_info
            current_files.add(file_path)
            if (
                file_path not in self.cache
                or self.cache[file_path]["modify_time"] < modify_time
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
                    result = process_file2(file_info)
                    self.update_cache(file_info, result)
                        
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
                    json.dump(data, f, ensure_ascii=False)
                    f.write("\n")
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

    def update_cache(self, file_info: Tuple[str, str, float], content: List[SourceCode]):
        file_path, relative_path, modify_time = file_info
        self.cache[file_path] = {
            "file_path": file_path,
            "relative_path": relative_path,
            "content": [c.model_dump() for c in content],
            "modify_time": modify_time,
        }

    def get_cache(self):
        self.load_first()
        self.trigger_update()
        return self.cache

    def get_all_files(self) -> List[Tuple[str, str, float]]:
        all_files = []
        for root, dirs, files in os.walk(self.path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]

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
                all_files.append((file_path, relative_path, modify_time))

        return all_files


def get_or_create_actor(path: str, ignore_spec, required_exts: list, cacher={}):
    with cache_lock:
        # 处理路径名
        actor_name = "AutoCoderRAGAsyncUpdateQueue_" + path.replace(
            os.sep, "_"
        ).replace(" ", "")
        try:
            actor = ray.get_actor(actor_name)
        except ValueError:
            actor = None
        if actor is None:
            actor = (
                ray.remote(AutoCoderRAGAsyncUpdateQueue)
                .options(name=actor_name, num_cpus=0)
                .remote(path, ignore_spec, required_exts)
            )
            ray.get(actor.load_first.remote())
        cacher[actor_name] = actor
        return actor


class DocumentRetriever:
    def __init__(
        self, path: str, ignore_spec, required_exts: list, on_ray: bool = False
    ) -> None:
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts

        self.on_ray = on_ray
        if self.on_ray:
            self.cacher = get_or_create_actor(path, ignore_spec, required_exts)
        else:
            self.cacher = AutoCoderRAGAsyncUpdateQueue(path, ignore_spec, required_exts)

    def get_cache(self):
        if self.on_ray:
            return ray.get(self.cacher.get_cache.remote())
        else:
            return self.cacher.get_cache()

    def retrieve_documents(self) -> Generator[SourceCode, None, None]:
        for _, data in self.get_cache().items():
            for source_code in data["content"]:
                yield SourceCode.model_validate(source_code)
