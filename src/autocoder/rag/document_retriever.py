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


def retrieve_documents(
    path: str, ignore_spec, required_exts: list
) -> Generator[SourceCode, None, None]:
    cache_dir = os.path.join(path, ".cache")
    cache_file = os.path.join(cache_dir, "cache.jsonl")
    lock_file = os.path.join(cache_dir, "cache.jsonl.lock")

    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)

    def get_all_files() -> List[Tuple[str, str, float]]:
        all_files = []
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            if ignore_spec:
                relative_root = os.path.relpath(root, path)
                dirs[:] = [
                    d
                    for d in dirs
                    if not ignore_spec.match_file(os.path.join(relative_root, d))
                ]
                files = [
                    f
                    for f in files
                    if not ignore_spec.match_file(os.path.join(relative_root, f))
                ]

            for file in files:
                if required_exts and not any(
                    file.endswith(ext) for ext in required_exts
                ):
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, path)
                modify_time = os.path.getmtime(file_path)
                all_files.append((file_path, relative_path, modify_time))

        return all_files

    def read_cache() -> Dict[str, Dict]:
        cache = {}
        if os.path.exists(cache_file):
            with open(cache_file, "r") as f:
                for line in f:
                    data = json.loads(line)
                    cache[data["file_path"]] = data
        return cache

    def write_cache(cache: Dict[str, Dict]):
        with open(cache_file, "w") as f:
            for data in cache.values():
                json.dump(data, f,ensure_ascii=False)
                f.write("\n")
    
    def update_cache(
        cache: Dict[str, Dict], file_info: Tuple[str, str, float], content: str
    ):
        file_path, relative_path, modify_time = file_info
        with cache_lock:
            cache[file_path] = {
                "file_path": file_path,
                "relative_path": relative_path,
                "content": content,
                "modify_time": modify_time,
            }

    all_files = get_all_files()
    cache = read_cache()

    files_to_process = []
    for file_info in all_files:
        file_path, _, modify_time = file_info
        if file_path not in cache or cache[file_path]["modify_time"] < modify_time:
            files_to_process.append(file_info)

    with Pool(processes=os.cpu_count()) as pool:
        results = pool.map(process_file, files_to_process)

    for file_info, result in zip(files_to_process, results):
        for item in result:
            update_cache(cache, file_info, item.source_code)

    # with ThreadPoolExecutor(max_workers=num_threads) as executor:
    #     future_to_file = {
    #         executor.submit(process_file, file_info): file_info
    #         for file_info in files_to_process
    #     }

    #     for future in as_completed(future_to_file):
    #         file_info = future_to_file[future]
    #         try:
    #             results = future.result()
    #             for result in results:
    #                 update_cache(cache, file_info, result.source_code)
    #         except Exception as e:
    #             logger.error(f"Error processing file {file_info[0]}: {str(e)}")

    with open(lock_file, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            write_cache(cache)
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)

    for file_path, data in cache.items():
        yield SourceCode(
            module_name=f"##File: {file_path}", source_code=data["content"]
        )
