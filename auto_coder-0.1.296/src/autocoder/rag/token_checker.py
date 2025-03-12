from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Generator, Tuple
from loguru import logger
from autocoder.common import SourceCode
import threading
import time
from rich.progress import Progress, SpinnerColumn, TimeElapsedColumn, BarColumn, TextColumn

def check_token_limit(
    count_tokens: Callable[[str], int],
    token_limit: int,
    retrieve_documents: Callable[[], Generator[SourceCode, None, None]],
    max_workers: int
) -> Tuple[List[str], int]:
    lock = threading.Lock()
    file_count = 0
    start_time = time.time()

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),        
        TimeElapsedColumn(),
    ) as progress:
        task = progress.add_task("Processing files", total=None)

        def process_doc(doc: SourceCode) -> Tuple[str | None, int]:
            token_num = count_tokens(doc.source_code)
            with lock:
                nonlocal file_count
                file_count += 1
                elapsed_time = time.time() - start_time
                files_per_second = file_count / elapsed_time if elapsed_time > 0 else 0
                progress.update(task, description=f"Processed {file_count} files ({files_per_second:.2f} files/s)")
            if token_num > token_limit:
                return doc.module_name, token_num
            return None, token_num

        def token_check_generator() -> Generator[Tuple[str | None, int], None, None]:
            docs = retrieve_documents()
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = []
                for doc in docs:
                    future = executor.submit(process_doc, doc)
                    futures.append(future)
                
                for future in as_completed(futures):
                    yield future.result()

        token_exceed_files = []
        total_tokens = 0
        for result, tokens in token_check_generator():
            if result:
                logger.info(f"文件 {result}({tokens}) 超过了 {token_limit} tokens")
                token_exceed_files.append(result)
            total_tokens += tokens

        progress.update(task, completed=file_count, total=file_count)

    total_time = time.time() - start_time
    average_speed = file_count / total_time if total_time > 0 else 0

    if token_exceed_files:
        logger.warning(
            f"以下文件超过了 {token_limit} tokens: {token_exceed_files},将无法使用 RAG 模型进行搜索。"
        )

    logger.info(f"累计 tokens: {total_tokens}")
    logger.info(f"总处理时间: {total_time:.2f} 秒")
    logger.info(f"平均处理速度: {average_speed:.2f} 文件/秒")

    return token_exceed_files, total_tokens