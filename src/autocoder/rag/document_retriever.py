import os
import json
import time
import fcntl
from concurrent.futures import ThreadPoolExecutor, as_completed
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

cache_lock = threading.Lock()


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
        # logger.info(f"Load file {file_path} in {time.time() - start_time}")
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
        self.cache = self.read_cache()

        files_to_process = []
        for file_info in self.get_all_files():
            file_path, _, modify_time = file_info
            if (
                file_path not in self.cache
                or self.cache[file_path]["modify_time"] < modify_time
            ):
                files_to_process.append(file_info)

        with Pool(processes=os.cpu_count()) as pool:
            results = pool.map(process_file, files_to_process)

        for file_info, result in zip(files_to_process, results):
            for item in result:
                self.update_cache(self.cache, file_info, item.source_code)
        self.write_cache()

    def add_update_request(self, file_infos: List[Tuple[str, str, float]]):
        for file_info in file_infos:
            self.queue.append(file_info)

    def process_queue(self):
        while self.queue:
            file_info = self.queue.pop(0)
            self.process_file(file_info)
            self.write_cache()

    def process_file(self, file_info: Tuple[str, str, float]) -> List[SourceCode]:
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
                v = [
                    SourceCode(module_name=f"##File: {file_path}", source_code=content)
                ]
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
                v = [
                    SourceCode(module_name=f"##File: {file_path}", source_code=content)
                ]
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                v = [
                    SourceCode(module_name=f"##File: {file_path}", source_code=content)
                ]

            for item in v:
                self.update_cache(file_info, item.source_code)

            logger.info(
                f"Processed and updated cache for file {file_path} in {time.time() - start_time}"
            )
            return v
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return []

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
        lock_file = os.path.join(cache_dir, "cache.jsonl.lock")

        with open(lock_file, "w") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            try:
                with open(cache_file, "w") as f:
                    for data in self.cache.values():
                        json.dump(data, f, ensure_ascii=False)
                        f.write("\n")
            finally:
                fcntl.flock(lock, fcntl.LOCK_UN)

    def update_cache(self, file_info: Tuple[str, str, float], content: str):
        file_path, relative_path, modify_time = file_info
        self.cache[file_path] = {
            "file_path": file_path,
            "relative_path": relative_path,
            "content": content,
            "modify_time": modify_time,
        }

    def get_cache(self):
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


def get_or_create_actor(path: str, ignore_spec, required_exts: list):
    with cache_lock:
        try:
            actor = ray.get_actor("AutoCoderRAGAsyncUpdateQueue")
        except ValueError:
            actor = None
        if actor is None:
            actor = (
                ray.remote(AutoCoderRAGAsyncUpdateQueue)
                .options(lifetime="detached", name="AutoCoderRAGAsyncUpdateQueue")
                .remote(path, ignore_spec, required_exts)
            )
        return actor


def retrieve_documents(
    path: str, ignore_spec, required_exts: list
) -> Generator[SourceCode, None, None]:

    cacher = get_or_create_actor(path, ignore_spec, required_exts)

    cache = cacher.get_cache.remote()

    for file_path, data in cache.items():
        yield SourceCode(
            module_name=f"##File: {file_path}", source_code=data["content"]
        )
