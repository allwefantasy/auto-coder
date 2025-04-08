import threading
from typing import Dict, Generator, List, Tuple, Any, Optional,Union

from byzerllm import ByzerLLM, SimpleByzerLLM
from loguru import logger
from autocoder.common import SourceCode
from uuid import uuid4
from abc import ABC, abstractmethod
from autocoder.rag.cache.simple_cache import AutoCoderRAGAsyncUpdateQueue
from autocoder.rag.cache.file_monitor_cache import AutoCoderRAGDocListener
from autocoder.rag.cache.byzer_storage_cache import ByzerStorageCache
from autocoder.rag.cache.local_byzer_storage_cache import LocalByzerStorageCache
from autocoder.rag.cache.local_duckdb_storage_cache import LocalDuckDBStorageCache
from autocoder.common import AutoCoderArgs

cache_lock = threading.Lock()

class BaseDocumentRetriever(ABC):
    """Abstract base class for document retrieval."""

    @abstractmethod
    def get_cache(self, options: Optional[Dict[str, Any]] = None):
        """Get cached documents."""
        pass

    @abstractmethod
    def retrieve_documents(
        self, options: Optional[Dict[str, Any]] = None
    ) -> Generator[SourceCode, None, None]:
        """Retrieve documents."""
        pass


class LocalDocumentRetriever(BaseDocumentRetriever):
    """Local filesystem document retriever implementation."""

    def __init__(
        self,
        args: AutoCoderArgs,
        llm: Union[ByzerLLM,SimpleByzerLLM],
        path: str,
        ignore_spec,
        required_exts: list,
        on_ray: bool = False,
        monitor_mode: bool = False,
        single_file_token_limit: int = 60000,
        disable_auto_window: bool = False,
        enable_hybrid_index: bool = False,
        extra_params: Optional['AutoCoderArgs'] = None,
        emb_llm: Union['ByzerLLM', 'SimpleByzerLLM'] = None,
    ) -> None:
        self.args = args
        self.llm = llm

        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.monitor_mode = monitor_mode
        self.enable_hybrid_index = enable_hybrid_index
        self.single_file_token_limit = single_file_token_limit
        self.disable_auto_window = disable_auto_window

        # 多小的文件会被合并
        self.small_file_token_limit = self.single_file_token_limit / 4
        # 合并后的最大文件大小
        self.small_file_merge_limit = self.single_file_token_limit / 2

        self.on_ray = on_ray        
        if self.enable_hybrid_index:
            if self.on_ray:
                self.cacher = ByzerStorageCache(
                    path, ignore_spec, required_exts, extra_params,
                    args=self.args, llm=self.llm
                )
            else:
                if extra_params.rag_storage_type == "duckdb":
                    self.cacher = LocalDuckDBStorageCache(
                        path, ignore_spec, required_exts, extra_params,
                        emb_llm=emb_llm,
                        args=self.args, llm=self.llm
                    )
                elif extra_params.rag_storage_type in ["byzer-storage", "byzer_storage"]:
                    self.cacher = LocalByzerStorageCache(
                        path, ignore_spec, required_exts, extra_params,
                        emb_llm=emb_llm,
                        args=self.args, llm=self.llm
                    )
        else:
            if self.monitor_mode:
                self.cacher = AutoCoderRAGDocListener(
                    path, ignore_spec, required_exts,
                    args=self.args, llm=self.llm
                )
            else:
                self.cacher = AutoCoderRAGAsyncUpdateQueue(
                    path, ignore_spec, required_exts,
                    args=self.args, llm=self.llm
                )

        logger.info(f"DocumentRetriever initialized with:")
        logger.info(f"  Path: {self.path}")
        logger.info(f"  Diable auto window: {self.disable_auto_window} ")
        logger.info(
            f"  Single file token limit: {self.single_file_token_limit}")
        logger.info(f"  Small file token limit: {self.small_file_token_limit}")
        logger.info(f"  Small file merge limit: {self.small_file_merge_limit}")
        logger.info(f"  Enable hybrid index: {self.enable_hybrid_index}")
        if extra_params:
            logger.info(
                f"  Hybrid index max output tokens: {extra_params.hybrid_index_max_output_tokens}"
            )

    def get_cache(self, options: Optional[Dict[str, Any]] = None):
        return self.cacher.get_cache(options=options)

    def retrieve_documents(
        self, options: Optional[Dict[str, Any]] = None
    ) -> Generator[SourceCode, None, None]:
        logger.info("Starting document retrieval process")
        waiting_list = []
        waiting_tokens = 0
        for _, data in self.get_cache(options=options).items():
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
        logger.info(
            f"Splitting document {doc.module_name} into {total_chunks} chunks")
        for i in range(0, doc.tokens, chunk_size):
            chunk_content = doc.source_code[i: i + chunk_size]
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
