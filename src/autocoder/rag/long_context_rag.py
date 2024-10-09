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
from autocoder.rag.document_retriever import DocumentRetriever
from autocoder.rag.relevant_utils import (
    DocRelevance,
    FilterDoc,
    TaskTiming,
    parse_relevance,
)
from autocoder.rag.token_checker import check_token_limit
from autocoder.rag.token_counter import RemoteTokenCounter, TokenCounter
from autocoder.rag.token_limiter import TokenLimiter
from tokenizers import Tokenizer
from autocoder.rag.variable_holder import VariableHolder

try:
    from autocoder_pro.rag.llm_compute import LLMComputeEngine
except ImportError:
    logger.warning("Please install auto-coder-pro to enhance llm compute ability")
    LLMComputeEngine = None


class LongContextRAG:
    def __init__(
        self,
        llm: ByzerLLM,
        args: AutoCoderArgs,
        path: str,
        tokenizer_path: Optional[str] = None,
    ) -> None:
        self.llm = llm
        self.args = args

        self.index_model = byzerllm.ByzerLLM()
        self.index_model.setup_default_model_name(
            args.index_model or self.llm.default_model_name
        )

        self.path = path
        self.relevant_score = self.args.rag_doc_filter_relevance or 5

        self.full_text_ratio = args.full_text_ratio
        self.segment_ratio = args.segment_ratio
        self.buff_ratio = 1 - self.full_text_ratio - self.segment_ratio

        if self.buff_ratio < 0:
            raise ValueError(
                "The sum of full_text_ratio and segment_ratio must be less than or equal to 1.0"
            )

        self.full_text_limit = int(args.rag_context_window_limit * self.full_text_ratio)
        self.segment_limit = int(args.rag_context_window_limit * self.segment_ratio)
        self.buff_limit = int(args.rag_context_window_limit * self.buff_ratio)

        self.tokenizer = None
        self.tokenizer_path = tokenizer_path
        self.on_ray = False

        if self.tokenizer_path:
            VariableHolder.TOKENIZER_PATH = self.tokenizer_path
            VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(self.tokenizer_path)
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
        logger.info(f"Monitor mode: {self.monitor_mode}")

        if args.rag_url and args.rag_url.startswith("http://"):
            if not args.rag_token:
                raise ValueError(
                    "You are in client mode, please provide the RAG token. e.g. rag_token: your_token_here"
                )
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
        self.document_retriever = DocumentRetriever(
            self.path,
            self.ignore_spec,
            self.required_exts,
            self.on_ray,
            self.monitor_mode,
            ## 确保全文区至少能放下一个文件
            single_file_token_limit=self.full_text_limit - 100,
            disable_auto_window=self.args.disable_auto_window,
        )

        self.doc_filter = DocFilter(
            self.index_model, self.args, on_ray=self.on_ray, path=self.path
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
        {% for doc in documents %}
        {{ doc }}
        {% endfor %}

        对话历史：
        {% for msg in conversations %}
        <{{ msg.role }}>: {{ msg.content }}
        {% endfor %}

        请根据提供的文档内容、用户对话历史以及最后一个问题，提取并总结文档中与问题相关的重要信息。
        如果文档中没有相关信息，请回复"该文档中没有与问题相关的信息"。
        提取的信息尽量保持和原文中的一样，并且只输出这些信息。
        """

    @byzerllm.prompt()
    def _answer_question(
        self, query: str, relevant_docs: List[str]
    ) -> Generator[str, None, None]:
        """
        使用以下文档来回答问题。如果文档中没有相关信息，请说"我没有足够的信息来回答这个问题"。

        文档：
        {% for doc in relevant_docs %}
        {{ doc }}
        {% endfor %}

        问题：{{ query }}

        回答：
        """

    def _load_ignore_file(self):
        serveignore_path = os.path.join(self.path, ".serveignore")
        gitignore_path = os.path.join(self.path, ".gitignore")

        if os.path.exists(serveignore_path):
            with open(serveignore_path, "r") as ignore_file:
                return pathspec.PathSpec.from_lines("gitwildmatch", ignore_file)
        elif os.path.exists(gitignore_path):
            with open(gitignore_path, "r") as ignore_file:
                return pathspec.PathSpec.from_lines("gitwildmatch", ignore_file)
        return None

    def _retrieve_documents(self) -> Generator[SourceCode, None, None]:
        return self.document_retriever.retrieve_documents()

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
        logger.info(f"Query: {target_query[0:100]}... only_contexts: {only_contexts}")

        if self.client:
            new_query = json.dumps(
                {"query": target_query, "only_contexts": only_contexts},
                ensure_ascii=False,
            )
            response = self.client.chat.completions.create(
                messages=[{"role": "user", "content": new_query}],
                model=self.args.model,
            )
            v = response.choices[0].message.content
            if not only_contexts:
                return [SourceCode(module_name=f"RAG:{target_query}", source_code=v)]

            json_lines = [json.loads(line) for line in v.split("\n") if line.strip()]
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

    def _filter_docs(self, conversations: List[Dict[str, str]]) -> List[FilterDoc]:
        documents = self._retrieve_documents()
        return self.doc_filter.filter_docs(
            conversations=conversations, documents=documents
        )

    def stream_chat_oai(
        self,
        conversations,
        model: Optional[str] = None,
        role_mapping=None,
        llm_config: Dict[str, Any] = {},
    ):
        try:
            return self._stream_chat_oai(
                conversations,
                model=model,
                role_mapping=role_mapping,
                llm_config=llm_config,
            )
        except Exception as e:
            logger.error(f"Error in stream_chat_oai: {str(e)}")
            traceback.print_exc()
            return ["出现错误，请稍后再试。"], []

    def _stream_chat_oai(
        self,
        conversations,
        model: Optional[str] = None,
        role_mapping=None,
        llm_config: Dict[str, Any] = {},
    ):
        if self.client:
            model = model or self.args.model
            response = self.client.chat.completions.create(
                model=model,
                messages=conversations,
                stream=True,
            )

            def response_generator():
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        yield chunk.choices[0].delta.content

            return response_generator(), []
        else:
            query = conversations[-1]["content"]
            context = []

            if (
                "使用四到五个字直接返回这句话的简要主题，不要解释、不要标点、不要语气词、不要多余文本，不要加粗，如果没有主题"
                in query
                or "简要总结一下对话内容，用作后续的上下文提示 prompt，控制在 200 字以内"
                in query
            ):
                chunks = self.llm.stream_chat_oai(
                    conversations=conversations,
                    model=model,
                    role_mapping=role_mapping,
                    llm_config=llm_config,
                    delta_mode=True,
                )
                return (chunk[0] for chunk in chunks), context

            only_contexts = False
            try:
                v = json.loads(query)
                if "only_contexts" in v:
                    query = v["query"]
                    only_contexts = v["only_contexts"]
            except json.JSONDecodeError:
                pass

            logger.info(f"Query: {query} only_contexts: {only_contexts}")
            start_time = time.time()
            relevant_docs: List[FilterDoc] = self._filter_docs(conversations)
            filter_time = time.time() - start_time

            # Filter relevant_docs to only include those with is_relevant=True
            highly_relevant_docs = [
                doc for doc in relevant_docs if doc.relevance.is_relevant
            ]

            if highly_relevant_docs:
                relevant_docs = highly_relevant_docs
                logger.info(f"Found {len(relevant_docs)} highly relevant documents")
            else:
                if relevant_docs:
                    prefix_chunk = FilterDoc(
                        source_code=SourceCode(
                            module_name="特殊说明",
                            source_code="没有找到特别相关的内容，下面的内容是一些不是很相关的文档。在根据后续文档回答问题前，你需要和用户先提前说一下。",
                        ),
                        relevance=DocRelevance(False, 0),
                    )
                    relevant_docs.insert(0, prefix_chunk)
                    logger.info(
                        "No highly relevant documents found. Added a prefix chunk to indicate this."
                    )

            logger.info(
                f"Filter time: {filter_time:.2f} seconds with {len(relevant_docs)} docs"
            )

            if only_contexts:
                return (
                    doc.source_code.model_dump_json() + "\n" for doc in relevant_docs
                ), []

            if not relevant_docs:
                return ["没有找到相关的文档来回答这个问题。"], []

            context = [doc.source_code.module_name for doc in relevant_docs]

            # 将 FilterDoc 转化为 SourceCode 方便后续的逻辑继续做处理
            relevant_docs = [doc.source_code for doc in relevant_docs]

            console = Console()

            # Create a table for the query information
            query_table = Table(title="Query Information", show_header=False)
            query_table.add_row("Query", query)
            query_table.add_row("Relevant docs", str(len(relevant_docs)))

            # Add relevant docs information
            relevant_docs_info = []
            for doc in relevant_docs:
                info = f"- {doc.module_name.replace(self.path,'',1)}"
                if "original_docs" in doc.metadata:
                    original_docs = ", ".join(
                        [
                            doc.replace(self.path, "", 1)
                            for doc in doc.metadata["original_docs"]
                        ]
                    )
                    info += f" (Original docs: {original_docs})"
                relevant_docs_info.append(info)

            relevant_docs_info = "\n".join(relevant_docs_info)
            query_table.add_row("Relevant docs list", relevant_docs_info)

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
                final_relevant_docs = token_limiter.limit_tokens(
                    relevant_docs=relevant_docs,
                    conversations=conversations,
                    index_filter_workers=self.args.index_filter_workers or 5,
                )
                first_round_full_docs = token_limiter.first_round_full_docs
                second_round_extracted_docs = token_limiter.second_round_extracted_docs
                sencond_round_time = token_limiter.sencond_round_time

                relevant_docs = final_relevant_docs
            else:
                relevant_docs = relevant_docs[: self.args.index_filter_file_num]

            logger.info(f"Finally send to model: {len(relevant_docs)}")

            query_table.add_row("Only contexts", str(only_contexts))
            query_table.add_row("Filter time", f"{filter_time:.2f} seconds")
            query_table.add_row("Final relevant docs", str(len(relevant_docs)))
            query_table.add_row(
                "first_round_full_docs", str(len(first_round_full_docs))
            )
            query_table.add_row(
                "second_round_extracted_docs", str(len(second_round_extracted_docs))
            )
            query_table.add_row(
                "Second round time", f"{sencond_round_time:.2f} seconds"
            )

            # Add relevant docs information
            final_relevant_docs_info = []
            for doc in relevant_docs:
                info = f"- {doc.module_name.replace(self.path,'',1)}"
                if "original_docs" in doc.metadata:
                    original_docs = ", ".join(
                        [
                            doc.replace(self.path, "", 1)
                            for doc in doc.metadata["original_docs"]
                        ]
                    )
                    info += f" (Original docs: {original_docs})"
                if "chunk_ranges" in doc.metadata:
                    chunk_ranges = json.dumps(
                        doc.metadata["chunk_ranges"], ensure_ascii=False
                    )
                    info += f" (Chunk ranges: {chunk_ranges})"
                final_relevant_docs_info.append(info)

            final_relevant_docs_info = "\n".join(final_relevant_docs_info)
            query_table.add_row("Final Relevant docs list", final_relevant_docs_info)

            # Create a panel to contain the table
            panel = Panel(
                query_table,
                title="RAG Search Results",
                expand=False,
            )

            # Log the panel using rich
            console.print(panel)

            request_tokens = sum([doc.tokens for doc in relevant_docs])
            target_model = model or self.llm.default_model_name
            logger.info(
                f"Start to send to model {target_model} with {request_tokens} tokens"
            )

            if LLMComputeEngine is not None:
                llm_compute_engine = LLMComputeEngine(
                    llm=self.llm, inference_enhance=True, debug=False
                )
                new_conversations = llm_compute_engine.process_conversation(
                    conversations, query, [doc.source_code for doc in relevant_docs]
                )

                return (
                    llm_compute_engine.stream_chat_oai(
                        conversations=new_conversations,
                        model=model,
                        role_mapping=role_mapping,
                        llm_config=llm_config,
                        delta_mode=True,
                    ),
                    context,
                )

            new_conversations = conversations[:-1] + [
                {
                    "role": "user",
                    "content": self._answer_question.prompt(
                        query=query,
                        relevant_docs=[doc.source_code for doc in relevant_docs],
                    ),
                }
            ]

            chunks = self.llm.stream_chat_oai(
                conversations=new_conversations,
                model=model,
                role_mapping=role_mapping,
                llm_config=llm_config,
                delta_mode=True,
            )

            return (chunk[0] for chunk in chunks), context
