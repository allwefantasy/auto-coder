from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Generator
from loguru import logger
from autocoder.common import SourceCode

def check_token_limit(
    tokenizer: Callable[[str], int],
    token_limit: int,
    retrieve_documents: Callable[[], Generator[SourceCode, None, None]],
    max_workers: int
) -> List[str]:
    def process_doc(doc: SourceCode) -> str | None:
        token_num = tokenizer(doc.source_code)
        if token_num > token_limit:
            return doc.module_name
        return None

    def token_check_generator() -> Generator[str, None, None]:
        docs = retrieve_documents()
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            for doc in docs:
                future = executor.submit(process_doc, doc)
                futures.append(future)
            
            for future in as_completed(futures):
                result = future.result()
                if result:
                    yield result

    token_exceed_files = list(token_check_generator())

    if token_exceed_files:
        logger.warning(
            f"以下文件超过了 {token_limit} tokens: {token_exceed_files},将无法使用 RAG 模型进行搜索。"
        )

    return token_exceed_files