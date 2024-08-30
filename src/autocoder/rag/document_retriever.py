import os
import queue
import threading
from typing import Generator
from autocoder.common import SourceCode
from autocoder.rag.loaders import (
    extract_text_from_pdf,
    extract_text_from_docx,
    extract_text_from_excel,
    extract_text_from_ppt,
)
from loguru import logger

def retrieve_documents(path: str, ignore_spec, required_exts: list) -> Generator[SourceCode, None, None]:
    file_queue = queue.Queue(maxsize=1000)
    result_queue = queue.Queue()
    stop_event = threading.Event()

    def process_file(file_path, relative_path):
        try:
            if file_path.endswith(".pdf"):
                with open(file_path, "rb") as f:
                    content = extract_text_from_pdf(f.read())
                return SourceCode(module_name=file_path, source_code=content)
            elif file_path.endswith(".docx"):
                with open(file_path, "rb") as f:
                    content = extract_text_from_docx(f.read())
                return SourceCode(module_name=f"##File: {file_path}", source_code=content)
            elif file_path.endswith(".xlsx") or file_path.endswith(".xls"):
                sheets = extract_text_from_excel(file_path)
                return [SourceCode(module_name=f"##File: {file_path}#{sheet[0]}", source_code=sheet[1]) for sheet in sheets]
            elif file_path.endswith(".pptx"):
                slides = extract_text_from_ppt(file_path)
                content = "".join(f"#{slide[0]}\n{slide[1]}\n\n" for slide in slides)
                return SourceCode(module_name=f"##File: {file_path}", source_code=content)
            else:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                return SourceCode(module_name=f"##File: {file_path}", source_code=content)
        except Exception as e:
            logger.error(f"Error processing file {file_path}: {str(e)}")
            return None

    def worker():
        while not stop_event.is_set():
            try:
                file_path, relative_path = file_queue.get(timeout=1)
                result = process_file(file_path, relative_path)
                if result:
                    if isinstance(result, list):
                        for item in result:
                            result_queue.put(item)
                    else:
                        result_queue.put(result)
                file_queue.task_done()
            except queue.Empty:
                continue

    def directory_walker():
        for root, dirs, files in os.walk(path):
            # 过滤掉隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith(".")]

            # 应用 .serveignore 或 .gitignore 规则
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
                if required_exts and not any(file.endswith(ext) for ext in required_exts):
                    continue

                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, path)
                file_queue.put((file_path, relative_path))

        # 所有文件都已添加到队列中，设置结束标志
        stop_event.set()

    num_threads = min(32, os.cpu_count() * 2)
    threads = [threading.Thread(target=worker) for _ in range(num_threads)]
    for thread in threads:
        thread.start()

    # 启动目录遍历线程
    directory_thread = threading.Thread(target=directory_walker)
    directory_thread.start()

    # 等待目录遍历完成
    directory_thread.join()

    # 等待所有工作线程完成
    for thread in threads:
        thread.join()

    while not result_queue.empty():
        yield result_queue.get()