import json
import os
import time
from typing import Any, Dict, Generator, List, Optional, Tuple

import byzerllm
import pandas as pd
import pathspec
from byzerllm import ByzerLLM
from loguru import logger
from openai import OpenAI
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
import statistics
import traceback

from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.rag.doc_filter import DocFilter
from autocoder.rag.document_retriever import LocalDocumentRetriever
from autocoder.rag.relevant_utils import (
    DocRelevance,
    FilterDoc,
    TaskTiming,
    parse_relevance,
    ProgressUpdate,
    DocFilterResult
)
from autocoder.rag.token_checker import check_token_limit
from autocoder.rag.token_counter import RemoteTokenCounter, TokenCounter
from autocoder.rag.token_limiter import TokenLimiter
from tokenizers import Tokenizer
from autocoder.rag.variable_holder import VariableHolder
from importlib.metadata import version
from autocoder.rag.stream_event import event_writer
from autocoder.rag.relevant_utils import DocFilterResult
from pydantic import BaseModel
from byzerllm.utils.types import SingleOutputMeta
from autocoder.rag.lang import get_message_with_format_and_newline
from autocoder.rag.qa_conversation_strategy import get_qa_strategy

try:
    from autocoder_pro.rag.llm_compute import LLMComputeEngine
    pro_version = version("auto-coder-pro")
    autocoder_version = version("auto-coder")
    logger.warning(
        f"auto-coder-pro({pro_version}) plugin is enabled in auto-coder.rag({autocoder_version})")
except ImportError:
    logger.warning(
        "Please install auto-coder-pro to enhance llm compute ability")
    LLMComputeEngine = None


class RecallStat(BaseModel):
    total_input_tokens: int
    total_generated_tokens: int
    model_name: str = "unknown"


class ChunkStat(BaseModel):
    total_input_tokens: int
    total_generated_tokens: int
    model_name: str = "unknown"


class AnswerStat(BaseModel):
    total_input_tokens: int
    total_generated_tokens: int
    model_name: str = "unknown"


class RAGStat(BaseModel):
    recall_stat: RecallStat
    chunk_stat: ChunkStat
    answer_stat: AnswerStat


class LongContextRAG:
    def __init__(
        self,
        llm: ByzerLLM,
        args: AutoCoderArgs,
        path: str,
        tokenizer_path: Optional[str] = None,
    ) -> None:
        self.llm = llm
        self.recall_llm = self.llm
        self.chunk_llm = self.llm
        self.qa_llm = self.llm
        self.emb_llm = None

        if self.llm.get_sub_client("qa_model"):
            self.qa_llm = self.llm.get_sub_client("qa_model")

        if self.llm.get_sub_client("recall_model"):
            self.recall_llm = self.llm.get_sub_client("recall_model")

        if self.llm.get_sub_client("chunk_model"):
            self.chunk_llm = self.llm.get_sub_client("chunk_model")

        if self.llm.get_sub_client("emb_model"):
            self.emb_llm = self.llm.get_sub_client("emb_model")

        self.args = args

        self.path = path
        self.relevant_score = self.args.rag_doc_filter_relevance or 5

        self.full_text_ratio = args.full_text_ratio
        self.segment_ratio = args.segment_ratio
        self.buff_ratio = 1 - self.full_text_ratio - self.segment_ratio

        if self.buff_ratio < 0:
            raise ValueError(
                "The sum of full_text_ratio and segment_ratio must be less than or equal to 1.0"
            )

        self.full_text_limit = int(
            args.rag_context_window_limit * self.full_text_ratio)
        self.segment_limit = int(
            args.rag_context_window_limit * self.segment_ratio)
        self.buff_limit = int(args.rag_context_window_limit * self.buff_ratio)

        self.tokenizer = None
        self.tokenizer_path = tokenizer_path
        self.on_ray = False

        if self.tokenizer_path:
            VariableHolder.TOKENIZER_PATH = self.tokenizer_path
            VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(
                self.tokenizer_path)
            self.tokenizer = TokenCounter(self.tokenizer_path)
        else:
            if llm.is_model_exist("deepseek_tokenizer"):
                tokenizer_llm = ByzerLLM()
                tokenizer_llm.setup_default_model_name("deepseek_tokenizer")
                self.tokenizer = RemoteTokenCounter(tokenizer_llm)

        self.required_exts = (
            [ext.strip() for ext in self.args.required_exts.split(",")]
            if self.args.required_exts
            else []
        )

        # if open monitor mode
        self.monitor_mode = self.args.monitor_mode or False
        self.enable_hybrid_index = self.args.enable_hybrid_index
        logger.info(f"Monitor mode: {self.monitor_mode}")

        if args.rag_url and args.rag_url.startswith("http://"):
            if not args.rag_token:
                raise ValueError(
                    "You are in client mode, please provide the RAG token. e.g. rag_token: your_token_here"
                )
            if not args.rag_url.endswith("/v1"):
                args.rag_url = args.rag_url.rstrip("/") + "/v1"
            self.client = OpenAI(api_key=args.rag_token, base_url=args.rag_url)
        else:
            self.client = None
            # if not pure client mode, then the path should be provided
            if (
                not self.path
                and args.rag_url
                and not args.rag_url.startswith("http://")
            ):
                self.path = args.rag_url

            if not self.path:
                raise ValueError(
                    "Please provide the path to the documents in the local file system."
                )

        self.ignore_spec = self._load_ignore_file()

        self.token_limit = self.args.rag_context_window_limit or 120000
        retriever_class = self._get_document_retriever_class()

        if self.args.enable_hybrid_index and not self.on_ray:
            if self.emb_llm is None:
                raise ValueError(
                    "emb_llm is required for local byzer storage cache")

        self.document_retriever = retriever_class(
            self.path,
            self.ignore_spec,
            self.required_exts,
            self.on_ray,
            self.monitor_mode,
            # 确保全文区至少能放下一个文件
            single_file_token_limit=self.full_text_limit - 100,
            disable_auto_window=self.args.disable_auto_window,
            enable_hybrid_index=self.args.enable_hybrid_index,
            extra_params=self.args,
            emb_llm=self.emb_llm
        )

        self.doc_filter = DocFilter(
            self.llm, self.args, on_ray=self.on_ray, path=self.path
        )

        doc_num = 0
        token_num = 0
        token_counts = []
        for doc in self._retrieve_documents():
            doc_num += 1
            doc_tokens = doc.tokens
            token_num += doc_tokens
            token_counts.append(doc_tokens)

        avg_tokens = statistics.mean(token_counts) if token_counts else 0
        median_tokens = statistics.median(token_counts) if token_counts else 0

        logger.info(
            "RAG Configuration:\n"
            f"  Total docs:        {doc_num}\n"
            f"  Total tokens:      {token_num}\n"
            f"  Tokenizer path:    {self.tokenizer_path}\n"
            f"  Relevant score:    {self.relevant_score}\n"
            f"  Token limit:       {self.token_limit}\n"
            f"  Full text limit:   {self.full_text_limit}\n"
            f"  Segment limit:     {self.segment_limit}\n"
            f"  Buff limit:        {self.buff_limit}\n"
            f"  Max doc tokens:    {max(token_counts) if token_counts else 0}\n"
            f"  Min doc tokens:    {min(token_counts) if token_counts else 0}\n"
            f"  Avg doc tokens:    {avg_tokens:.2f}\n"
            f"  Median doc tokens: {median_tokens:.2f}\n"
        )

    def count_tokens(self, text: str) -> int:
        if self.tokenizer is None:
            return -1
        return self.tokenizer.count_tokens(text)

    @byzerllm.prompt()
    def extract_relevance_info_from_docs_with_conversation(
        self, conversations: List[Dict[str, str]], documents: List[str]
    ) -> str:
        """
        使用以下文档和对话历史来提取相关信息。

        文档：
        <documents>
        {% for doc in documents %}
        {{ doc }}
        {% endfor %}
        </documents>

        对话历史：
        <conversations>
        {% for msg in conversations %}
        [{{ msg.role }}]: 
        {{ msg.content }}

        {% endfor %}
        </conversations>

        请根据提供的文档内容、用户对话历史以及最后一个问题，提取并总结文档中与问题相关的重要信息。
        如果文档中没有相关信息，请回复"该文档中没有与问题相关的信息"。
        提取的信息尽量保持和原文中的一样，并且只输出这些信息。
        """    

    def _get_document_retriever_class(self):
        """Get the document retriever class based on configuration."""
        # Default to LocalDocumentRetriever if not specified
        return LocalDocumentRetriever

    def _load_ignore_file(self):
        serveignore_path = os.path.join(self.path, ".serveignore")
        gitignore_path = os.path.join(self.path, ".gitignore")

        if os.path.exists(serveignore_path):
            with open(serveignore_path, "r", encoding="utf-8") as ignore_file:
                return pathspec.PathSpec.from_lines("gitwildmatch", ignore_file)
        elif os.path.exists(gitignore_path):
            with open(gitignore_path, "r", encoding="utf-8") as ignore_file:
                return pathspec.PathSpec.from_lines("gitwildmatch", ignore_file)
        return None

    def _retrieve_documents(self, options: Optional[Dict[str, Any]] = None) -> Generator[SourceCode, None, None]:
        return self.document_retriever.retrieve_documents(options=options)

    def build(self):
        pass

    def search(self, query: str) -> List[SourceCode]:
        target_query = query
        only_contexts = False
        if self.args.enable_rag_search and isinstance(self.args.enable_rag_search, str):
            target_query = self.args.enable_rag_search
        elif self.args.enable_rag_context and isinstance(
            self.args.enable_rag_context, str
        ):
            target_query = self.args.enable_rag_context
            only_contexts = True
        elif self.args.enable_rag_context:
            only_contexts = True

        logger.info("Search from RAG.....")
        logger.info(
            f"Query: {target_query[0:100]}... only_contexts: {only_contexts}")

        if self.client:
            new_query = json.dumps(
                {"query": target_query, "only_contexts": only_contexts},
                ensure_ascii=False,
            )
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": new_query}],
                model=self.args.model,
                max_tokens=self.args.rag_params_max_tokens,
            )
            v = response.choices[0].message.content
            if not only_contexts:
                return [SourceCode(module_name=f"RAG:{target_query}", source_code=v)]

            json_lines = [json.loads(line)
                          for line in v.split("\n") if line.strip()]
            return [SourceCode.model_validate(json_line) for json_line in json_lines]
        else:
            if only_contexts:
                return [
                    doc.source_code
                    for doc in self._filter_docs(
                        [{"role": "user", "content": target_query}]
                    )
                ]
            else:
                v, contexts = self.stream_chat_oai(
                    conversations=[{"role": "user", "content": target_query}]
                )
                url = ",".join(contexts)
                return [SourceCode(module_name=f"RAG:{url}", source_code="".join(v))]

    def _filter_docs(self, conversations: List[Dict[str, str]]) -> DocFilterResult:
        query = conversations[-1]["content"]
        documents = self._retrieve_documents(options={"query": query})
        return self.doc_filter.filter_docs(
            conversations=conversations, documents=documents
        )

    def stream_chat_oai(
        self,
        conversations,
        model: Optional[str] = None,
        role_mapping=None,
        llm_config: Dict[str, Any] = {},
        extra_request_params: Dict[str, Any] = {}
    ):
        try:
            return self._stream_chat_oai(
                conversations,
                model=model,
                role_mapping=role_mapping,
                llm_config=llm_config,
                extra_request_params=extra_request_params
            )
        except Exception as e:
            logger.error(f"Error in stream_chat_oai: {str(e)}")
            traceback.print_exc()
            return ["出现错误，请稍后再试。"], []

    def _stream_chatfrom_openai_sdk(self, response):
        for chunk in response:
            if hasattr(chunk, "usage") and chunk.usage:
                input_tokens_count = chunk.usage.prompt_tokens
                generated_tokens_count = chunk.usage.completion_tokens
            else:
                input_tokens_count = 0
                generated_tokens_count = 0

            if not chunk.choices:
                if last_meta:
                    yield ("", SingleOutputMeta(input_tokens_count=input_tokens_count,
                                                generated_tokens_count=generated_tokens_count,
                                                reasoning_content="",
                                                finish_reason=last_meta.finish_reason))
                continue

            content = chunk.choices[0].delta.content or ""

            reasoning_text = ""
            if hasattr(chunk.choices[0].delta, "reasoning_content"):
                reasoning_text = chunk.choices[0].delta.reasoning_content or ""

            last_meta = SingleOutputMeta(input_tokens_count=input_tokens_count,
                                         generated_tokens_count=generated_tokens_count,
                                         reasoning_content=reasoning_text,
                                         finish_reason=chunk.choices[0].finish_reason)
            yield (content, last_meta)

    def _stream_chat_oai(
        self,
        conversations,
        model: Optional[str] = None,
        role_mapping=None,
        llm_config: Dict[str, Any] = {},
        extra_request_params: Dict[str, Any] = {}
    ):
        if self.client:
            model = model or self.args.model
            response = self.client.chat.completions.create(
                model=model,
                messages=conversations,
                stream=True,
                max_tokens=self.args.rag_params_max_tokens,
                extra_body=extra_request_params
            )
            return self._stream_chatfrom_openai_sdk(response), []

        target_llm = self.llm
        if self.llm.get_sub_client("qa_model"):
            target_llm = self.llm.get_sub_client("qa_model")

        query = conversations[-1]["content"]
        context = []

        if (
            "使用四到五个字直接返回这句话的简要主题，不要解释、不要标点、不要语气词、不要多余文本，不要加粗，如果没有主题"
            in query
            or "简要总结一下对话内容，用作后续的上下文提示 prompt，控制在 200 字以内"
            in query
        ):

            chunks = target_llm.stream_chat_oai(
                conversations=conversations,
                model=model,
                role_mapping=role_mapping,
                llm_config=llm_config,
                delta_mode=True,
                extra_request_params=extra_request_params
            )

            def generate_chunks():
                for chunk in chunks:
                    yield chunk
            return generate_chunks(), context

        try:
            request_params = json.loads(query)
            if "request_id" in request_params:
                request_id = request_params["request_id"]
                index = request_params["index"]

                file_path = event_writer.get_event_file_path(request_id)
                logger.info(
                    f"Get events for request_id: {request_id} index: {index} file_path: {file_path}")
                events = []
                if not os.path.exists(file_path):
                    return [], context

                with open(file_path, "r") as f:
                    for line in f:
                        event = json.loads(line)
                        if event["index"] >= index:
                            events.append(event)
                return [json.dumps({
                    "events": [event for event in events],
                }, ensure_ascii=False)], context
        except json.JSONDecodeError:
            pass

        if self.args.without_contexts and LLMComputeEngine is not None:
            llm_compute_engine = LLMComputeEngine(
                llm=target_llm,
                inference_enhance=not self.args.disable_inference_enhance,
                inference_deep_thought=self.args.inference_deep_thought,
                inference_slow_without_deep_thought=self.args.inference_slow_without_deep_thought,
                precision=self.args.inference_compute_precision,
                data_cells_max_num=self.args.data_cells_max_num,
            )
            conversations = conversations[:-1]
            new_conversations = llm_compute_engine.process_conversation(
                conversations, query, []
            )
            chunks = llm_compute_engine.stream_chat_oai(
                conversations=new_conversations,
                model=model,
                role_mapping=role_mapping,
                llm_config=llm_config,
                delta_mode=True,
                extra_request_params=extra_request_params
            )

            def generate_chunks():
                for chunk in chunks:
                    yield chunk

            return (
                generate_chunks(),
                context,
            )

        only_contexts = False
        try:
            v = json.loads(query)
            if "only_contexts" in v:
                query = v["query"]
                only_contexts = v["only_contexts"]
                conversations[-1]["content"] = query
        except json.JSONDecodeError:
            pass

        logger.info(f"Query: {query} only_contexts: {only_contexts}")
        start_time = time.time()

        rag_stat = RAGStat(
            recall_stat=RecallStat(
                total_input_tokens=0,
                total_generated_tokens=0,
                model_name=self.recall_llm.default_model_name,
            ),
            chunk_stat=ChunkStat(
                total_input_tokens=0,
                total_generated_tokens=0,
                model_name=self.chunk_llm.default_model_name,
            ),
            answer_stat=AnswerStat(
                total_input_tokens=0,
                total_generated_tokens=0,
                model_name=self.qa_llm.default_model_name,
            ),
        )

        context = []

        def generate_sream():
            nonlocal context

            yield ("", SingleOutputMeta(input_tokens_count=0,
                                        generated_tokens_count=0,
                                        reasoning_content=get_message_with_format_and_newline(
                                            "rag_searching_docs",
                                            model=rag_stat.recall_stat.model_name
                                        )
                                        ))

            doc_filter_result = DocFilterResult(
                docs=[],
                raw_docs=[],
                input_tokens_counts=[],
                generated_tokens_counts=[],
                durations=[],
                model_name=rag_stat.recall_stat.model_name
            )
            query = conversations[-1]["content"]
            documents = self._retrieve_documents(options={"query": query})

            # 使用带进度报告的过滤方法
            for progress_update, result in self.doc_filter.filter_docs_with_progress(conversations, documents):
                if result is not None:
                    doc_filter_result = result
                else:
                    # 生成进度更新
                    yield ("", SingleOutputMeta(
                        input_tokens_count=rag_stat.recall_stat.total_input_tokens,
                        generated_tokens_count=rag_stat.recall_stat.total_generated_tokens,
                        reasoning_content=f"{progress_update.message} ({progress_update.completed}/{progress_update.total})"
                    ))

            rag_stat.recall_stat.total_input_tokens += sum(
                doc_filter_result.input_tokens_counts)
            rag_stat.recall_stat.total_generated_tokens += sum(
                doc_filter_result.generated_tokens_counts)
            rag_stat.recall_stat.model_name = doc_filter_result.model_name

            relevant_docs: List[FilterDoc] = doc_filter_result.docs
            filter_time = time.time() - start_time

            yield ("", SingleOutputMeta(input_tokens_count=rag_stat.recall_stat.total_input_tokens,
                                        generated_tokens_count=rag_stat.recall_stat.total_generated_tokens,
                                        reasoning_content=get_message_with_format_and_newline(
                                            "rag_docs_filter_result",
                                            filter_time=filter_time,
                                            docs_num=len(relevant_docs),
                                            input_tokens=rag_stat.recall_stat.total_input_tokens,
                                            output_tokens=rag_stat.recall_stat.total_generated_tokens,
                                            model=rag_stat.recall_stat.model_name
                                        )
                                        ))

            # Filter relevant_docs to only include those with is_relevant=True
            highly_relevant_docs = [
                doc for doc in relevant_docs if doc.relevance.is_relevant
            ]

            if highly_relevant_docs:
                relevant_docs = highly_relevant_docs
                logger.info(
                    f"Found {len(relevant_docs)} highly relevant documents")

            logger.info(
                f"Filter time: {filter_time:.2f} seconds with {len(relevant_docs)} docs"
            )

            if only_contexts:
                final_docs = []
                for doc in relevant_docs:
                    final_docs.append(doc.model_dump())
                return [json.dumps(final_docs, ensure_ascii=False)], []

            if not relevant_docs:
                yield ("没有找到可以回答你问题的相关文档", SingleOutputMeta(input_tokens_count=rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens,
                                                            generated_tokens_count=rag_stat.recall_stat.total_generated_tokens +
                                                            rag_stat.chunk_stat.total_generated_tokens,
                                                            ))
                return

            context = [doc.source_code.module_name for doc in relevant_docs]

            yield ("", SingleOutputMeta(input_tokens_count=rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens,
                                        generated_tokens_count=rag_stat.recall_stat.total_generated_tokens +
                                        rag_stat.chunk_stat.total_generated_tokens,
                                        reasoning_content=get_message_with_format_and_newline(
                                            "context_docs_names",
                                            context_docs_names=",".join(
                                                context))
                                        ))

            # 将 FilterDoc 转化为 SourceCode 方便后续的逻辑继续做处理
            relevant_docs = [doc.source_code for doc in relevant_docs]

            logger.info(f"=== RAG Search Results ===")
            logger.info(f"Query: {query}")
            logger.info(f"Found relevant docs: {len(relevant_docs)}")

            # 记录相关文档信息
            relevant_docs_info = []
            for i, doc in enumerate(relevant_docs):
                doc_path = doc.module_name.replace(self.path, '', 1)
                info = f"{i+1}. {doc_path}"
                if "original_docs" in doc.metadata:
                    original_docs = ", ".join(
                        [
                            doc.replace(self.path, "", 1)
                            for doc in doc.metadata["original_docs"]
                        ]
                    )
                    info += f" (Original docs: {original_docs})"
                relevant_docs_info.append(info)

            if relevant_docs_info:
                logger.info(
                    f"Relevant documents list:"
                    + "".join([f"\n  * {info}" for info in relevant_docs_info])
                )

            yield ("", SingleOutputMeta(generated_tokens_count=0,
                                        reasoning_content=get_message_with_format_and_newline(
                                            "dynamic_chunking_start",
                                            model=rag_stat.chunk_stat.model_name
                                        )
                                        ))
            first_round_full_docs = []
            second_round_extracted_docs = []
            sencond_round_time = 0

            if self.tokenizer is not None:

                token_limiter = TokenLimiter(
                    count_tokens=self.count_tokens,
                    full_text_limit=self.full_text_limit,
                    segment_limit=self.segment_limit,
                    buff_limit=self.buff_limit,
                    llm=self.llm,
                    disable_segment_reorder=self.args.disable_segment_reorder,
                )

                token_limiter_result = token_limiter.limit_tokens(
                    relevant_docs=relevant_docs,
                    conversations=conversations,
                    index_filter_workers=self.args.index_filter_workers or 5,
                )

                rag_stat.chunk_stat.total_input_tokens += sum(
                    token_limiter_result.input_tokens_counts)
                rag_stat.chunk_stat.total_generated_tokens += sum(
                    token_limiter_result.generated_tokens_counts)
                rag_stat.chunk_stat.model_name = token_limiter_result.model_name

                final_relevant_docs = token_limiter_result.docs
                first_round_full_docs = token_limiter.first_round_full_docs
                second_round_extracted_docs = token_limiter.second_round_extracted_docs
                sencond_round_time = token_limiter.sencond_round_time

                relevant_docs = final_relevant_docs
            else:
                relevant_docs = relevant_docs[: self.args.index_filter_file_num]

            logger.info(f"Finally send to model: {len(relevant_docs)}")
            # 记录分段处理的统计信息
            logger.info(
                f"=== Token Management ===\n"
                f"  * Only contexts: {only_contexts}\n"
                f"  * Filter time: {filter_time:.2f} seconds\n"
                f"  * Final relevant docs: {len(relevant_docs)}\n"
                f"  * First round full docs: {len(first_round_full_docs)}\n"
                f"  * Second round extracted docs: {len(second_round_extracted_docs)}\n"
                f"  * Second round time: {sencond_round_time:.2f} seconds"
            )

            yield ("", SingleOutputMeta(generated_tokens_count=rag_stat.chunk_stat.total_generated_tokens + rag_stat.recall_stat.total_generated_tokens,
                                        input_tokens_count=rag_stat.chunk_stat.total_input_tokens +
                                        rag_stat.recall_stat.total_input_tokens,
                                        reasoning_content=get_message_with_format_and_newline(
                                            "dynamic_chunking_result",
                                            model=rag_stat.chunk_stat.model_name,
                                            docs_num=len(relevant_docs),
                                            filter_time=filter_time,
                                            sencond_round_time=sencond_round_time,
                                            first_round_full_docs=len(
                                                first_round_full_docs),
                                            second_round_extracted_docs=len(
                                                second_round_extracted_docs),
                                            input_tokens=rag_stat.chunk_stat.total_input_tokens,
                                            output_tokens=rag_stat.chunk_stat.total_generated_tokens
                                        )
                                        ))

            # 记录最终选择的文档详情
            final_relevant_docs_info = []
            for i, doc in enumerate(relevant_docs):
                doc_path = doc.module_name.replace(self.path, '', 1)
                info = f"{i+1}. {doc_path}"

                metadata_info = []
                if "original_docs" in doc.metadata:
                    original_docs = ", ".join(
                        [
                            od.replace(self.path, "", 1)
                            for od in doc.metadata["original_docs"]
                        ]
                    )
                    metadata_info.append(f"Original docs: {original_docs}")

                if "chunk_ranges" in doc.metadata:
                    chunk_ranges = json.dumps(
                        doc.metadata["chunk_ranges"], ensure_ascii=False
                    )
                    metadata_info.append(f"Chunk ranges: {chunk_ranges}")

                if "processing_time" in doc.metadata:
                    metadata_info.append(
                        f"Processing time: {doc.metadata['processing_time']:.2f}s")

                if metadata_info:
                    info += f" ({'; '.join(metadata_info)})"

                final_relevant_docs_info.append(info)

            if final_relevant_docs_info:
                logger.info(
                    f"Final documents to be sent to model:"
                    + "".join([f"\n  * {info}" for info in final_relevant_docs_info])
                )

            # 记录令牌统计
            request_tokens = sum([doc.tokens for doc in relevant_docs])
            target_model = target_llm.default_model_name
            logger.info(
                f"=== LLM Request ===\n"
                f"  * Target model: {target_model}\n"
                f"  * Total tokens: {request_tokens}"
            )

            logger.info(
                f"Start to send to model {target_model} with {request_tokens} tokens")

            yield ("", SingleOutputMeta(input_tokens_count=rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens,
                                        generated_tokens_count=rag_stat.recall_stat.total_generated_tokens +
                                        rag_stat.chunk_stat.total_generated_tokens,
                                        reasoning_content=get_message_with_format_and_newline(
                                            "send_to_model",
                                            model=target_model,
                                            tokens=request_tokens
                                        )
                                        ))

            yield ("", SingleOutputMeta(input_tokens_count=rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens,
                                        generated_tokens_count=rag_stat.recall_stat.total_generated_tokens +
                                        rag_stat.chunk_stat.total_generated_tokens,
                                        reasoning_content="qa_model_thinking"
                                        ))

            if LLMComputeEngine is not None and not self.args.disable_inference_enhance:
                llm_compute_engine = LLMComputeEngine(
                    llm=target_llm,
                    inference_enhance=not self.args.disable_inference_enhance,
                    inference_deep_thought=self.args.inference_deep_thought,
                    precision=self.args.inference_compute_precision,
                    data_cells_max_num=self.args.data_cells_max_num,
                    debug=False,
                )
                new_conversations = llm_compute_engine.process_conversation(
                    conversations, query, [
                        doc.source_code for doc in relevant_docs]
                )
                chunks = llm_compute_engine.stream_chat_oai(
                    conversations=new_conversations,
                    model=model,
                    role_mapping=role_mapping,
                    llm_config=llm_config,
                    delta_mode=True,
                )

                for chunk in chunks:
                    if chunk[1] is not None:
                        rag_stat.answer_stat.total_input_tokens += chunk[1].input_tokens_count
                        rag_stat.answer_stat.total_generated_tokens += chunk[1].generated_tokens_count
                        chunk[1].input_tokens_count = rag_stat.recall_stat.total_input_tokens + \
                            rag_stat.chunk_stat.total_input_tokens + \
                            rag_stat.answer_stat.total_input_tokens
                        chunk[1].generated_tokens_count = rag_stat.recall_stat.total_generated_tokens + \
                            rag_stat.chunk_stat.total_generated_tokens + \
                            rag_stat.answer_stat.total_generated_tokens
                    yield chunk

                self._print_rag_stats(rag_stat)
            else:
                
                qa_strategy = get_qa_strategy(self.args.rag_qa_conversation_strategy)
                new_conversations = qa_strategy.create_conversation(
                    documents=[doc.source_code for doc in relevant_docs],
                    conversations=conversations
                )                

                chunks = target_llm.stream_chat_oai(
                    conversations=new_conversations,
                    model=model,
                    role_mapping=role_mapping,
                    llm_config=llm_config,
                    delta_mode=True,
                    extra_request_params=extra_request_params
                )

                for chunk in chunks:
                    if chunk[1] is not None:
                        rag_stat.answer_stat.total_input_tokens += chunk[1].input_tokens_count
                        rag_stat.answer_stat.total_generated_tokens += chunk[1].generated_tokens_count
                        chunk[1].input_tokens_count = rag_stat.recall_stat.total_input_tokens + \
                            rag_stat.chunk_stat.total_input_tokens + \
                            rag_stat.answer_stat.total_input_tokens
                        chunk[1].generated_tokens_count = rag_stat.recall_stat.total_generated_tokens + \
                            rag_stat.chunk_stat.total_generated_tokens + \
                            rag_stat.answer_stat.total_generated_tokens

                    yield chunk

                self._print_rag_stats(rag_stat)

        return generate_sream(), context

    def _print_rag_stats(self, rag_stat: RAGStat) -> None:
        """打印RAG执行的详细统计信息"""
        total_input_tokens = (
            rag_stat.recall_stat.total_input_tokens +
            rag_stat.chunk_stat.total_input_tokens +
            rag_stat.answer_stat.total_input_tokens
        )
        total_generated_tokens = (
            rag_stat.recall_stat.total_generated_tokens +
            rag_stat.chunk_stat.total_generated_tokens +
            rag_stat.answer_stat.total_generated_tokens
        )
        total_tokens = total_input_tokens + total_generated_tokens

        # 避免除以零错误
        if total_tokens == 0:
            recall_percent = chunk_percent = answer_percent = 0
        else:
            recall_percent = (rag_stat.recall_stat.total_input_tokens +
                              rag_stat.recall_stat.total_generated_tokens) / total_tokens * 100
            chunk_percent = (rag_stat.chunk_stat.total_input_tokens +
                             rag_stat.chunk_stat.total_generated_tokens) / total_tokens * 100
            answer_percent = (rag_stat.answer_stat.total_input_tokens +
                              rag_stat.answer_stat.total_generated_tokens) / total_tokens * 100

        logger.info(
            f"=== RAG 执行统计信息 ===\n"
            f"总令牌使用: {total_tokens} 令牌\n"
            f"  * 输入令牌总数: {total_input_tokens}\n"
            f"  * 生成令牌总数: {total_generated_tokens}\n"
            f"\n"
            f"阶段统计:\n"
            f"  1. 文档检索阶段:\n"
            f"     - 模型: {rag_stat.recall_stat.model_name}\n"
            f"     - 输入令牌: {rag_stat.recall_stat.total_input_tokens}\n"
            f"     - 生成令牌: {rag_stat.recall_stat.total_generated_tokens}\n"
            f"     - 阶段总计: {rag_stat.recall_stat.total_input_tokens + rag_stat.recall_stat.total_generated_tokens}\n"
            f"\n"
            f"  2. 文档分块阶段:\n"
            f"     - 模型: {rag_stat.chunk_stat.model_name}\n"
            f"     - 输入令牌: {rag_stat.chunk_stat.total_input_tokens}\n"
            f"     - 生成令牌: {rag_stat.chunk_stat.total_generated_tokens}\n"
            f"     - 阶段总计: {rag_stat.chunk_stat.total_input_tokens + rag_stat.chunk_stat.total_generated_tokens}\n"
            f"\n"
            f"  3. 答案生成阶段:\n"
            f"     - 模型: {rag_stat.answer_stat.model_name}\n"
            f"     - 输入令牌: {rag_stat.answer_stat.total_input_tokens}\n"
            f"     - 生成令牌: {rag_stat.answer_stat.total_generated_tokens}\n"
            f"     - 阶段总计: {rag_stat.answer_stat.total_input_tokens + rag_stat.answer_stat.total_generated_tokens}\n"
            f"\n"
            f"令牌分布百分比:\n"
            f"  - 文档检索: {recall_percent:.1f}%\n"
            f"  - 文档分块: {chunk_percent:.1f}%\n"
            f"  - 答案生成: {answer_percent:.1f}%\n"
        )

        # 记录原始统计数据，以便调试
        logger.debug(f"RAG Stat 原始数据: {rag_stat}")

        # 返回成本估算
        estimated_cost = self._estimate_token_cost(
            total_input_tokens, total_generated_tokens)
        if estimated_cost > 0:
            logger.info(f"估计成本: 约 ${estimated_cost:.4f} 人民币")

    def _estimate_token_cost(self, input_tokens: int, output_tokens: int) -> float:
        """估算当前请求的令牌成本（人民币）"""
        # 实际应用中，可以根据不同模型设置不同价格
        input_cost_per_1m = 2.0/1000000   # 每百万输入令牌的成本
        output_cost_per_1m = 8.0/100000   # 每百万输出令牌的成本

        cost = (input_tokens * input_cost_per_1m / 1000000) + \
            (output_tokens * output_cost_per_1m/1000000)
        return cost
