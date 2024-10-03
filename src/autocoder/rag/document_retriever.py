import json
import os
import platform
import time
import traceback

from watchfiles import Change, DefaultFilter, awatch, watch

if platform.system() != "Windows":
    import fcntl
else:
    fcntl = None
import threading
from multiprocessing import Pool
from typing import Dict, Generator, List, Tuple

import ray
from loguru import logger
from pydantic import BaseModel

from autocoder.common import SourceCode
from autocoder.rag.loaders import (
    extract_text_from_docx,
    extract_text_from_excel,
    extract_text_from_pdf,
    extract_text_from_ppt,
)
from autocoder.rag.token_counter import count_tokens_worker, count_tokens
from uuid import uuid4
from autocoder.rag.variable_holder import VariableHolder

cache_lock = threading.Lock()


class DeleteEvent(BaseModel):
    file_paths: List[str]


class AddOrUpdateEvent(BaseModel):
    file_infos: List[Tuple[str, str, float]]


def process_file_in_multi_process(
    file_info: Tuple[str, str, float]
) -> List[SourceCode]:
    start_time = time.time()
    file_path, relative_path, _ = file_info
    try:
        if file_path.endswith(".pdf"):
            with open(file_path, "rb") as f:
                content = extract_text_from_pdf(f.read())
            v = [
                SourceCode(
                    module_name=file_path,
                    source_code=content,
                    tokens=count_tokens_worker(content),
                )
            ]
        elif file_path.endswith(".docx"):
            with open(file_path, "rb") as f:
                content = extract_text_from_docx(f.read())
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens_worker(content),
                )
            ]
        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            sheets = extract_text_from_excel(file_path)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}#{sheet[0]}",
                    source_code=sheet[1],
                    tokens=count_tokens_worker(sheet[1]),
                )
                for sheet in sheets
            ]
        elif file_path.endswith(".pptx"):
            slides = extract_text_from_ppt(file_path)
            content = "".join(f"#{slide[0]}\n{slide[1]}\n\n" for slide in slides)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens_worker(content),
                )
            ]
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens_worker(content),
                )
            ]
        logger.info(f"Load file {file_path} in {time.time() - start_time}")
        return v
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")
        return []


def process_file_local(file_path: str) -> List[SourceCode]:
    start_time = time.time()
    try:
        if file_path.endswith(".pdf"):
            with open(file_path, "rb") as f:
                content = extract_text_from_pdf(f.read())
            v = [
                SourceCode(
                    module_name=file_path,
                    source_code=content,
                    tokens=count_tokens(content),
                )
            ]
        elif file_path.endswith(".docx"):
            with open(file_path, "rb") as f:
                content = extract_text_from_docx(f.read())
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens(content),
                )
            ]
        elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
            sheets = extract_text_from_excel(file_path)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}#{sheet[0]}",
                    source_code=sheet[1],
                    tokens=count_tokens(sheet[1]),
                )
                for sheet in sheets
            ]
        elif file_path.endswith(".pptx"):
            slides = extract_text_from_ppt(file_path)
            content = "".join(f"#{slide[0]}\n{slide[1]}\n\n" for slide in slides)
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens(content),
                )
            ]
        else:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            v = [
                SourceCode(
                    module_name=f"##File: {file_path}",
                    source_code=content,
                    tokens=count_tokens(content),
                )
            ]
        logger.info(f"Load file {file_path} in {time.time() - start_time}")
        return v
    except Exception as e:
        logger.error(f"Error processing file {file_path}: {str(e)}")        
        traceback.print_exc()
        return []


class AutoCoderRAGDocListener:
    cache: Dict[str, Dict] = {}
    ignore_dirs = [
        "__pycache__",
        ".git",
        ".hg",
        ".svn",
        ".tox",
        ".venv",
        ".cache",
        ".idea",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".hypothesis",
    ]
    ignore_entity_patterns = [
        r"\.py[cod]$",
        r"\.___jb_...___$",
        r"\.sw.$",
        "~$",
        r"^\.\#",
        r"^\.DS_Store$",
        r"^flycheck_",
        r"^test.*$",
    ]

    def __init__(self, path: str, ignore_spec, required_exts: List) -> None:
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.stop_event = threading.Event()

        # connect list
        self.ignore_entity_patterns.extend(self._load_ignore_file())
        self.file_filter = DefaultFilter(
            ignore_dirs=self.ignore_dirs,
            ignore_paths=[],
            ignore_entity_patterns=self.ignore_entity_patterns,
        )
        self.load_first()
        # 创建一个新线程来执行open_watch
        self.watch_thread = threading.Thread(target=self.open_watch)
        # 将线程设置为守护线程,这样主程序退出时,这个线程也会自动退出
        self.watch_thread.daemon = True
        # 启动线程
        self.watch_thread.start()

    def stop(self):
        self.stop_event.set()
        self.watch_thread.join()

    def __del__(self):
        self.stop()

    def load_first(self):
        files_to_process = self.get_all_files()
        if not files_to_process:
            return
        for item in files_to_process:
            self.update_cache(item)

    def update_cache(self, file_path):
        source_code = process_file_local(file_path)
        self.cache[file_path] = {
            "file_path": file_path,
            "content": [c.model_dump() for c in source_code],
        }
        logger.info(f"update cache: {file_path}")
        logger.info(f"current cache: {self.cache.keys()}")

    def remove_cache(self, file_path):
        del self.cache[file_path]
        logger.info(f"remove cache: {file_path}")
        logger.info(f"current cache: {self.cache.keys()}")

    def open_watch(self):
        logger.info(f"start monitor: {self.path}...")
        for changes in watch(
            self.path, watch_filter=self.file_filter, stop_event=self.stop_event
        ):
            for change in changes:
                (action, path) = change
                if action == Change.added or action == Change.modified:
                    self.update_cache(path)
                elif action == Change.deleted:
                    self.remove_cache(path)

    def get_cache(self):
        return self.cache

    def _load_ignore_file(self):
        serveignore_path = os.path.join(self.path, ".serveignore")
        gitignore_path = os.path.join(self.path, ".gitignore")

        if os.path.exists(serveignore_path):
            with open(serveignore_path, "r") as ignore_file:
                patterns = ignore_file.readlines()
                return [pattern.strip() for pattern in patterns]
        elif os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as ignore_file:
                patterns = ignore_file.readlines()
                return [pattern.strip() for pattern in patterns]
        return []

    def get_all_files(self) -> List[str]:
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
                absolute_path = os.path.abspath(file_path)
                all_files.append(absolute_path)

        return all_files


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
            from autocoder.rag.token_counter import initialize_tokenizer

            with Pool(
                processes=os.cpu_count(),
                initializer=initialize_tokenizer,
                initargs=(VariableHolder.TOKENIZER_PATH,),
            ) as pool:
                results = pool.map(process_file_in_multi_process, files_to_process)

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
                    result = process_file_local(file_info[0])
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

    def update_cache(
        self, file_info: Tuple[str, str, float], content: List[SourceCode]
    ):
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
        self,
        path: str,
        ignore_spec,
        required_exts: list,
        on_ray: bool = False,
        monitor_mode: bool = False,
        single_file_token_limit: int = 60000,
        disable_auto_window: bool = False,
    ) -> None:
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.monitor_mode = monitor_mode
        self.single_file_token_limit = single_file_token_limit
        self.disable_auto_window = disable_auto_window

        # 多小的文件会被合并
        self.small_file_token_limit = self.single_file_token_limit / 4
        # 合并后的最大文件大小
        self.small_file_merge_limit = self.single_file_token_limit / 2

        self.on_ray = on_ray
        if self.on_ray:
            self.cacher = get_or_create_actor(path, ignore_spec, required_exts)
        else:
            if self.monitor_mode:
                self.cacher = AutoCoderRAGDocListener(path, ignore_spec, required_exts)
            else:
                self.cacher = AutoCoderRAGAsyncUpdateQueue(
                    path, ignore_spec, required_exts
                )

        logger.info(f"DocumentRetriever initialized with:")
        logger.info(f"  Path: {self.path}")
        logger.info(f"  Diable auto window: {self.disable_auto_window} ")
        logger.info(f"  Single file token limit: {self.single_file_token_limit}")
        logger.info(f"  Small file token limit: {self.small_file_token_limit}")
        logger.info(f"  Small file merge limit: {self.small_file_merge_limit}")

    def get_cache(self):
        if self.on_ray:
            return ray.get(self.cacher.get_cache.remote())
        else:
            return self.cacher.get_cache()

    def retrieve_documents(self) -> Generator[SourceCode, None, None]:
        logger.info("Starting document retrieval process")
        waiting_list = []
        waiting_tokens = 0
        for _, data in self.get_cache().items():
            for source_code in data["content"]:
                doc = SourceCode.model_validate(source_code)
                if self.disable_auto_window:
                    yield doc
                else:
                    if doc.tokens <= 0:
                        yield doc
                    elif doc.tokens < self.small_file_token_limit:
                        waiting_list, waiting_tokens = self._add_to_waiting_list(
                            doc, waiting_list, waiting_tokens
                        )
                        if waiting_tokens >= self.small_file_merge_limit:
                            yield from self._process_waiting_list(waiting_list)
                            waiting_list = []
                            waiting_tokens = 0
                    elif doc.tokens > self.single_file_token_limit:
                        yield from self._split_large_document(doc)
                    else:
                        yield doc
        if waiting_list and not self.disable_auto_window:            
            yield from self._process_waiting_list(waiting_list)

        logger.info("Document retrieval process completed")

    def _add_to_waiting_list(
        self, doc: SourceCode, waiting_list: List[SourceCode], waiting_tokens: int
    ) -> Tuple[List[SourceCode], int]:
        waiting_list.append(doc)
        return waiting_list, waiting_tokens + doc.tokens

    def _process_waiting_list(
        self, waiting_list: List[SourceCode]
    ) -> Generator[SourceCode, None, None]:
        if len(waiting_list) == 1:
            yield waiting_list[0]            
        elif len(waiting_list) > 1:
            yield self._merge_documents(waiting_list)

    def _merge_documents(self, docs: List[SourceCode]) -> SourceCode:
        merged_content = "\n".join(
            [f"#File: {doc.module_name}\n{doc.source_code}" for doc in docs]
        )
        merged_tokens = sum([doc.tokens for doc in docs])
        merged_name = f"Merged_{len(docs)}_docs_{str(uuid4())}"        
        logger.info(
            f"Merged {len(docs)} documents into {merged_name} (tokens: {merged_tokens})."
        )
        return SourceCode(
            module_name=merged_name,
            source_code=merged_content,
            tokens=merged_tokens,
            metadata={"original_docs": [doc.module_name for doc in docs]},
        )

    def _split_large_document(
        self, doc: SourceCode
    ) -> Generator[SourceCode, None, None]:
        chunk_size = self.single_file_token_limit
        total_chunks = (doc.tokens + chunk_size - 1) // chunk_size
        logger.info(f"Splitting document {doc.module_name} into {total_chunks} chunks")
        for i in range(0, doc.tokens, chunk_size):
            chunk_content = doc.source_code[i : i + chunk_size]
            chunk_tokens = min(chunk_size, doc.tokens - i)
            chunk_name = f"{doc.module_name}#chunk{i//chunk_size+1}"
            # logger.debug(f"  Created chunk: {chunk_name} (tokens: {chunk_tokens})")
            yield SourceCode(
                module_name=chunk_name,
                source_code=chunk_content,
                tokens=chunk_tokens,
                metadata={
                    "original_doc": doc.module_name,
                    "chunk_index": i // chunk_size + 1,
                },
            )

    def _split_document(
        self, doc: SourceCode, token_limit: int
    ) -> Generator[SourceCode, None, None]:
        remaining_tokens = doc.tokens
        chunk_number = 1
        start_index = 0

        while remaining_tokens > 0:
            end_index = start_index + token_limit
            chunk_content = doc.source_code[start_index:end_index]
            chunk_tokens = min(token_limit, remaining_tokens)

            chunk_name = f"{doc.module_name}#{chunk_number:06d}"
            yield SourceCode(
                module_name=chunk_name, source_code=chunk_content, tokens=chunk_tokens
            )

            start_index = end_index
            remaining_tokens -= chunk_tokens
            chunk_number += 1
