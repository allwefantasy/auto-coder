import json
import os
import time
from typing import Any, Dict, Generator, List, Optional, Tuple

import pathspec
from byzerllm import ByzerLLM
from loguru import logger
from openai import OpenAI
import statistics
import traceback

from autocoder.common import AutoCoderArgs, SourceCode
from autocoder.rag.doc_filter import DocFilter
from autocoder.rag.document_retriever import LocalDocumentRetriever
from autocoder.rag.relevant_utils import DocFilterResult
from autocoder.rag.token_counter import RemoteTokenCounter, TokenCounter,count_tokens
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
from autocoder.rag.searchable import SearchableResults
from autocoder.rag.conversation_to_queries import extract_search_queries
from autocoder.common import openai_content as OpenAIContentProcessor
from autocoder.common.save_formatted_log import save_formatted_log
from autocoder.rag.types import (
    RecallStat,ChunkStat,AnswerStat,OtherStat,RAGStat
)
import json, os
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
            self.args,
            self.llm,
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
        if not self.client:
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

    def _get_document_retriever_class(self):
        """Get the document retriever class based on configuration."""
        # Default to LocalDocumentRetriever if not specified
        return LocalDocumentRetriever

    def _load_ignore_file(self):
        serveignore_path = os.path.join(self.path, ".serveignore")
        if not os.path.exists(serveignore_path):
            serveignore_path = os.path.join(self.path, ".autocoderignore")
        
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
                result = (item for (item,_) in v)
                return [SourceCode(module_name=f"RAG:{url}", source_code="".join(result))]

    def _filter_docs(self, conversations: List[Dict[str, str]]) -> DocFilterResult:
        query = conversations[-1]["content"]
        queries = extract_search_queries(conversations=conversations, args=self.args, llm=self.llm, max_queries=self.args.rag_recall_max_queries)
        documents = self._retrieve_documents(
            options={"queries": [query] + [query.query for query in queries]})
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
        if not llm_config:
            llm_config = {}
        
        if extra_request_params:
            llm_config.update(extra_request_params)
        
        conversations = OpenAIContentProcessor.process_conversations(conversations)
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

        if not only_contexts and extra_request_params.get("only_contexts", False):
            only_contexts = True

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

        return self._generate_sream(
            conversations=conversations,
            query=query,
            only_contexts=only_contexts,
            start_time=start_time,
            rag_stat=rag_stat,
            context=context,
            target_llm=target_llm,
            model=model,
            role_mapping=role_mapping,
            llm_config=llm_config,
            extra_request_params=extra_request_params
        ), context

    
    def _generate_sream(
        self,
        conversations,
        query,
        only_contexts,
        start_time,
        rag_stat,
        context,
        target_llm,
        model=None,
        role_mapping=None,
        llm_config=None,
        extra_request_params=None
    ):
        """将RAG流程分为三个主要阶段的生成器函数"""

        yield ("", SingleOutputMeta(
            input_tokens_count=0,
            generated_tokens_count=0,
            reasoning_content=get_message_with_format_and_newline(
                "rag_processing"
            )
        ))              

        # 第一阶段：文档召回和过滤
        doc_retrieval_generator = self._process_document_retrieval(
            conversations=conversations,
            query=query,
            rag_stat=rag_stat
        )
        
        # 处理第一阶段结果
        for item in doc_retrieval_generator:
            if isinstance(item, tuple) and len(item) == 2:
                # 正常的生成器项，包含yield内容和元数据
                yield item
            elif isinstance(item, dict) and "result" in item:
                # 如果是只返回上下文的情况
                if only_contexts:
                    try:
                        searcher = SearchableResults()
                        result = searcher.reorder(docs=item["result"])
                        yield (json.dumps(result.model_dump(), ensure_ascii=False), SingleOutputMeta(
                            input_tokens_count=rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens,
                            generated_tokens_count=rag_stat.recall_stat.total_generated_tokens + rag_stat.chunk_stat.total_generated_tokens,
                        ))
                        return
                    except Exception as e:
                        yield (str(e), SingleOutputMeta(
                            input_tokens_count=rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens,
                            generated_tokens_count=rag_stat.recall_stat.total_generated_tokens + rag_stat.chunk_stat.total_generated_tokens,
                        ))
                        return
                
                # 如果没有找到相关文档
                if not item["result"]:
                    yield ("没有找到可以回答你问题的相关文档", SingleOutputMeta(
                        input_tokens_count=rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens,
                        generated_tokens_count=rag_stat.recall_stat.total_generated_tokens + rag_stat.chunk_stat.total_generated_tokens,
                    ))
                    return
                
                # 更新上下文
                context.extend([doc.source_code.module_name for doc in item["result"]])
                
                # 输出上下文文档名称
                yield ("", SingleOutputMeta(
                    input_tokens_count=rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens,
                    generated_tokens_count=rag_stat.recall_stat.total_generated_tokens + rag_stat.chunk_stat.total_generated_tokens,
                    reasoning_content=get_message_with_format_and_newline(
                        "context_docs_names",
                        context_docs_names="*****"
                    )
                ))
                
                # 记录信息到日志
                logger.info(f"=== RAG Search Results ===")
                logger.info(f"Query: {query}")
                relevant_docs = [doc.source_code for doc in item["result"]]
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
                
                # 第二阶段：文档分块与重排序
                doc_chunking_generator = self._process_document_chunking(
                    relevant_docs=relevant_docs,
                    conversations=conversations,
                    rag_stat=rag_stat,
                    filter_time=(time.time() - start_time)
                )
                
                for chunking_item in doc_chunking_generator:
                    if isinstance(chunking_item, tuple) and len(chunking_item) == 2:
                        # 正常的生成器项
                        yield chunking_item
                    elif isinstance(chunking_item, dict) and "result" in chunking_item:
                        processed_docs = chunking_item["result"]
                        filter_time = chunking_item.get("filter_time", 0)
                        first_round_full_docs = chunking_item.get("first_round_full_docs", [])
                        second_round_extracted_docs = chunking_item.get("second_round_extracted_docs", [])
                        sencond_round_time = chunking_item.get("sencond_round_time", 0)
                        
                        # 记录最终选择的文档详情
                        final_relevant_docs_info = []
                        for i, doc in enumerate(processed_docs):
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
                        request_tokens = sum([count_tokens(doc.source_code) for doc in processed_docs])
                        target_model = target_llm.default_model_name
                        logger.info(
                            f"=== LLM Request ===\n"
                            f"  * Target model: {target_model}\n"
                            f"  * Total tokens: {request_tokens}"
                        )

                        logger.info(
                            f"Start to send to model {target_model} with {request_tokens} tokens")

                        yield ("", SingleOutputMeta(
                            input_tokens_count=rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens,
                            generated_tokens_count=rag_stat.recall_stat.total_generated_tokens + rag_stat.chunk_stat.total_generated_tokens,
                            reasoning_content=get_message_with_format_and_newline(
                                "send_to_model",
                                model=target_model,
                                tokens=request_tokens
                            )
                        ))

                        yield ("", SingleOutputMeta(
                            input_tokens_count=rag_stat.recall_stat.total_input_tokens + rag_stat.chunk_stat.total_input_tokens,
                            generated_tokens_count=rag_stat.recall_stat.total_generated_tokens + rag_stat.chunk_stat.total_generated_tokens,
                            reasoning_content="qa_model_thinking"
                        ))
                        
                        # 第三阶段：大模型问答生成
                        qa_generation_generator = self._process_qa_generation(
                            relevant_docs=processed_docs,
                            conversations=conversations,
                            target_llm=target_llm,
                            rag_stat=rag_stat,
                            model=model,
                            role_mapping=role_mapping,
                            llm_config=llm_config,
                            extra_request_params=extra_request_params
                        )
                        
                        for gen_item in qa_generation_generator:
                            yield gen_item
                        
                        # 打印最终的统计信息
                        self._print_rag_stats(rag_stat, conversations)
                        return

    def _process_document_retrieval(self, conversations, 
                                    query, rag_stat):
        """第一阶段：文档召回和过滤"""
        recall_start_time = time.time()  # 记录召回阶段开始时间        
        
        yield ("", SingleOutputMeta(
            input_tokens_count=0,
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
        
        # 提取查询并检索候选文档
        queries = extract_search_queries(
            conversations=conversations, args=self.args, llm=self.llm, max_queries=self.args.rag_recall_max_queries,rag_stat=rag_stat)
        documents = self._retrieve_documents(
            options={"queries": [query] + [query.query for query in queries]})

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

        # 更新统计信息
        rag_stat.recall_stat.total_input_tokens += sum(doc_filter_result.input_tokens_counts)
        rag_stat.recall_stat.total_generated_tokens += sum(doc_filter_result.generated_tokens_counts)
        rag_stat.recall_stat.model_name = doc_filter_result.model_name
        rag_stat.recall_stat.duration = time.time() - recall_start_time  # 记录召回阶段耗时

        relevant_docs = doc_filter_result.docs
        
        yield ("", SingleOutputMeta(
            input_tokens_count=rag_stat.recall_stat.total_input_tokens,
            generated_tokens_count=rag_stat.recall_stat.total_generated_tokens,
            reasoning_content=get_message_with_format_and_newline(
                "rag_docs_filter_result",
                filter_time=rag_stat.recall_stat.duration,  # 使用实际耗时
                docs_num=len(relevant_docs),
                input_tokens=rag_stat.recall_stat.total_input_tokens,
                output_tokens=rag_stat.recall_stat.total_generated_tokens,
                model=rag_stat.recall_stat.model_name
            )
        ))

        # 仅保留高相关性文档
        highly_relevant_docs = [doc for doc in relevant_docs if doc.relevance.is_relevant]
        if highly_relevant_docs:
            relevant_docs = highly_relevant_docs
            logger.info(f"Found {len(relevant_docs)} highly relevant documents")
        
        # 返回结果
        yield {"result": relevant_docs}

    def _process_document_chunking(self, relevant_docs, conversations, rag_stat, filter_time):
        """第二阶段：文档分块与重排序"""
        chunk_start_time = time.time()  # 记录分块阶段开始时间
        
        yield ("", SingleOutputMeta(
            generated_tokens_count=0,
            reasoning_content=get_message_with_format_and_newline(
                "dynamic_chunking_start",
                model=rag_stat.chunk_stat.model_name
            )
        ))
        
        # 默认值
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

            # 更新统计信息
            rag_stat.chunk_stat.total_input_tokens += sum(token_limiter_result.input_tokens_counts)
            rag_stat.chunk_stat.total_generated_tokens += sum(token_limiter_result.generated_tokens_counts)
            rag_stat.chunk_stat.model_name = token_limiter_result.model_name

            final_relevant_docs = token_limiter_result.docs
            first_round_full_docs = token_limiter.first_round_full_docs
            second_round_extracted_docs = token_limiter.second_round_extracted_docs
            sencond_round_time = token_limiter.sencond_round_time
        else:
            # 如果没有tokenizer，直接限制文档数量
            final_relevant_docs = relevant_docs[: self.args.index_filter_file_num]
        
        rag_stat.chunk_stat.duration = time.time() - chunk_start_time  # 记录分块阶段耗时
        
        # 输出分块结果统计
        yield ("", SingleOutputMeta(
            generated_tokens_count=rag_stat.chunk_stat.total_generated_tokens + rag_stat.recall_stat.total_generated_tokens,
            input_tokens_count=rag_stat.chunk_stat.total_input_tokens + rag_stat.recall_stat.total_input_tokens,
            reasoning_content=get_message_with_format_and_newline(
                "dynamic_chunking_result",
                model=rag_stat.chunk_stat.model_name,
                docs_num=len(final_relevant_docs),
                filter_time=filter_time,
                sencond_round_time=sencond_round_time,
                first_round_full_docs=len(first_round_full_docs),
                second_round_extracted_docs=len(second_round_extracted_docs),
                input_tokens=rag_stat.chunk_stat.total_input_tokens,
                output_tokens=rag_stat.chunk_stat.total_generated_tokens
            )
        ))
        
        # 返回处理结果和相关统计信息
        yield {
            "result": final_relevant_docs,
            "filter_time": filter_time,
            "first_round_full_docs": first_round_full_docs,
            "second_round_extracted_docs": second_round_extracted_docs,
            "sencond_round_time": sencond_round_time
        }

    def _process_qa_generation(self, relevant_docs, conversations, 
                               target_llm, 
                               rag_stat, 
                               model=None, 
                               role_mapping=None, 
                               llm_config={}, 
                               extra_request_params={}):
        """第三阶段：大模型问答生成"""
        answer_start_time = time.time()  # 记录答案生成阶段开始时间
        
        # 使用LLMComputeEngine增强处理（如果可用）
        if LLMComputeEngine is not None and not self.args.disable_inference_enhance:
            llm_compute_engine = LLMComputeEngine(
                llm=target_llm,
                inference_enhance=not self.args.disable_inference_enhance,
                inference_deep_thought=self.args.inference_deep_thought,
                precision=self.args.inference_compute_precision,
                data_cells_max_num=self.args.data_cells_max_num,
                debug=False,
            )
            query = conversations[-1]["content"]
            new_conversations = llm_compute_engine.process_conversation(
                conversations, query, [doc.source_code for doc in relevant_docs]
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
            rag_stat.answer_stat.duration = time.time() - answer_start_time  # 记录答案生成阶段耗时
        else:
            # 常规QA处理路径
            qa_strategy = get_qa_strategy(self.args)
            new_conversations = qa_strategy.create_conversation(
                documents=[doc.source_code for doc in relevant_docs],
                conversations=conversations, local_image_host=self.args.local_image_host
            )            

            # 流式生成回答
            chunks = target_llm.stream_chat_oai(
                conversations=new_conversations,
                model=model,
                role_mapping=role_mapping,
                llm_config=llm_config,
                delta_mode=True,
                extra_request_params=extra_request_params
            )
             
            # 返回结果并更新统计信息
            last_content = ""
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
                last_content += chunk[0]
                yield chunk

            # 保存对话日志
            try:                    
                logger.info(f"Saving new_conversations log to {self.args.source_dir}/.cache/logs")
                project_root = self.args.source_dir
                json_text = json.dumps(new_conversations + [{"role": "assistant", "content": last_content}], ensure_ascii=False)
                save_formatted_log(project_root, json_text, "rag_conversation")
            except Exception as e:
                logger.warning(f"Failed to save new_conversations log: {e}")

            rag_stat.answer_stat.duration = time.time() - answer_start_time  # 记录答案生成阶段耗时

    def _print_rag_stats(self, rag_stat: RAGStat, conversations: Optional[List[Dict[str, str]]] = None) -> None:
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
        
        # 计算总耗时
        total_duration = (
            rag_stat.recall_stat.duration +
            rag_stat.chunk_stat.duration +
            rag_stat.answer_stat.duration
        )
        
        # 添加其他阶段的耗时（如果存在）
        if rag_stat.other_stats:
            total_duration += sum(other_stat.duration for other_stat in rag_stat.other_stats)

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
        
        # 计算其他阶段的令牌占比
        other_percents = []
        if total_tokens > 0 and rag_stat.other_stats:
            for other_stat in rag_stat.other_stats:
                other_percent = (other_stat.total_input_tokens +
                                other_stat.total_generated_tokens) / total_tokens * 100
                other_percents.append(other_percent)
        
        # 计算耗时分布百分比
        if total_duration == 0:
            recall_duration_percent = chunk_duration_percent = answer_duration_percent = 0
        else:
            recall_duration_percent = rag_stat.recall_stat.duration / total_duration * 100
            chunk_duration_percent = rag_stat.chunk_stat.duration / total_duration * 100
            answer_duration_percent = rag_stat.answer_stat.duration / total_duration * 100
            
        # 计算其他阶段的耗时占比
        other_duration_percents = []
        if total_duration > 0 and rag_stat.other_stats:
            for other_stat in rag_stat.other_stats:
                other_duration_percents.append(other_stat.duration / total_duration * 100)
        
        # 计算成本分布百分比
        if rag_stat.cost == 0:
            recall_cost_percent = chunk_cost_percent = answer_cost_percent = 0
        else:
            recall_cost_percent = rag_stat.recall_stat.cost / rag_stat.cost * 100
            chunk_cost_percent = rag_stat.chunk_stat.cost / rag_stat.cost * 100
            answer_cost_percent = rag_stat.answer_stat.cost / rag_stat.cost * 100
            
        # 计算其他阶段的成本占比
        other_costs_percent = []
        if rag_stat.cost > 0 and rag_stat.other_stats:
            for other_stat in rag_stat.other_stats:
                other_costs_percent.append(other_stat.cost / rag_stat.cost * 100)

        ## 这里会计算每个阶段的成本
        estimated_cost = self._estimate_token_cost(rag_stat)
        # 构建统计信息字符串
        query_content = ""
        if conversations and len(conversations) > 0:
            query_content = conversations[-1].get("content", "")
            if len(query_content) > 100:
                query_content = query_content[:100] + "..."
            query_content = f"查询内容: {query_content}\n"
        
        stats_str = (
            f"=== (RAG 执行统计信息) ===\n"
            f"{query_content}"
            f"总令牌使用: {total_tokens} 令牌\n"
            f"  * 输入令牌总数: {total_input_tokens}\n"
            f"  * 生成令牌总数: {total_generated_tokens}\n"
            f"  * 总成本: {rag_stat.cost:.6f}\n"
            f"  * 总耗时: {total_duration:.2f} 秒\n"
            f"\n"
            f"阶段统计:\n"
            f"  1. 文档检索阶段:\n"
            f"     - 模型: {rag_stat.recall_stat.model_name}\n"
            f"     - 输入令牌: {rag_stat.recall_stat.total_input_tokens}\n"
            f"     - 生成令牌: {rag_stat.recall_stat.total_generated_tokens}\n"
            f"     - 阶段总计: {rag_stat.recall_stat.total_input_tokens + rag_stat.recall_stat.total_generated_tokens}\n"
            f"     - 阶段成本: {rag_stat.recall_stat.cost:.6f}\n"
            f"     - 阶段耗时: {rag_stat.recall_stat.duration:.2f} 秒\n"
            f"\n"
            f"  2. 文档分块阶段:\n"
            f"     - 模型: {rag_stat.chunk_stat.model_name}\n"
            f"     - 输入令牌: {rag_stat.chunk_stat.total_input_tokens}\n"
            f"     - 生成令牌: {rag_stat.chunk_stat.total_generated_tokens}\n"
            f"     - 阶段总计: {rag_stat.chunk_stat.total_input_tokens + rag_stat.chunk_stat.total_generated_tokens}\n"
            f"     - 阶段成本: {rag_stat.chunk_stat.cost:.6f}\n"
            f"     - 阶段耗时: {rag_stat.chunk_stat.duration:.2f} 秒\n"
            f"\n"
            f"  3. 答案生成阶段:\n"
            f"     - 模型: {rag_stat.answer_stat.model_name}\n"
            f"     - 输入令牌: {rag_stat.answer_stat.total_input_tokens}\n"
            f"     - 生成令牌: {rag_stat.answer_stat.total_generated_tokens}\n"
            f"     - 阶段总计: {rag_stat.answer_stat.total_input_tokens + rag_stat.answer_stat.total_generated_tokens}\n"
            f"     - 阶段成本: {rag_stat.answer_stat.cost:.6f}\n"
            f"     - 阶段耗时: {rag_stat.answer_stat.duration:.2f} 秒\n"
            f"\n"
        )
        
        # 如果存在 other_stats，添加其统计信息
        if rag_stat.other_stats:
            for i, other_stat in enumerate(rag_stat.other_stats):
                stats_str += (
                    f"  {i+4}. 其他阶段 {i+1}:\n"
                    f"     - 模型: {other_stat.model_name}\n"
                    f"     - 输入令牌: {other_stat.total_input_tokens}\n"
                    f"     - 生成令牌: {other_stat.total_generated_tokens}\n"
                    f"     - 阶段总计: {other_stat.total_input_tokens + other_stat.total_generated_tokens}\n"
                    f"     - 阶段成本: {other_stat.cost:.6f}\n"
                    f"     - 阶段耗时: {other_stat.duration:.2f} 秒\n"
                    f"\n"
                )
        
        # 添加令牌分布百分比
        stats_str += (
            f"令牌分布百分比:\n"
            f"  - 文档检索: {recall_percent:.1f}%\n"
            f"  - 文档分块: {chunk_percent:.1f}%\n"
            f"  - 答案生成: {answer_percent:.1f}%\n"
        )
        
        # 如果存在 other_stats，添加其令牌占比
        if rag_stat.other_stats:
            for i, other_percent in enumerate(other_percents):
                if other_percent > 0:
                    stats_str += f"  - 其他阶段 {i+1}: {other_percent:.1f}%\n"
        
        # 添加耗时分布百分比
        stats_str += (
            f"\n"
            f"耗时分布百分比:\n"
            f"  - 文档检索: {recall_duration_percent:.1f}%\n"
            f"  - 文档分块: {chunk_duration_percent:.1f}%\n"
            f"  - 答案生成: {answer_duration_percent:.1f}%\n"
        )
        
        # 如果存在 other_stats，添加其耗时占比
        if rag_stat.other_stats:
            for i, other_duration_percent in enumerate(other_duration_percents):
                if other_duration_percent > 0:
                    stats_str += f"  - 其他阶段 {i+1}: {other_duration_percent:.1f}%\n"
        
        # 添加成本分布百分比
        stats_str += (
            f"\n"
            f"成本分布百分比:\n"
            f"  - 文档检索: {recall_cost_percent:.1f}%\n"
            f"  - 文档分块: {chunk_cost_percent:.1f}%\n"
            f"  - 答案生成: {answer_cost_percent:.1f}%\n"
        )
        
        # 如果存在 other_stats，添加其成本占比
        if rag_stat.other_stats:
            for i, other_cost_percent in enumerate(other_costs_percent):
                if other_cost_percent > 0:
                    stats_str += f"  - 其他阶段 {i+1}: {other_cost_percent:.1f}%\n"
        
        # 输出统计信息
        logger.info(stats_str)

        # 记录原始统计数据，以便调试
        logger.debug(f"RAG Stat 原始数据: {rag_stat}")

        
        if estimated_cost > 0:
            logger.info(f"估计成本: 约 {estimated_cost:.4f} ")

    def _estimate_token_cost(self, rag_stat: RAGStat) -> float:
        """估算当前请求的令牌成本（人民币）"""
        from autocoder.models import get_model_by_name
        
        total_cost = 0.0
        
        # 计算召回阶段成本
        if rag_stat.recall_stat.model_name != "unknown":
            try:
                recall_model = get_model_by_name(rag_stat.recall_stat.model_name)
                input_cost = recall_model.get("input_price", 0.0) / 1000000
                output_cost = recall_model.get("output_price", 0.0) / 1000000
                recall_cost = (rag_stat.recall_stat.total_input_tokens * input_cost) + \
                             (rag_stat.recall_stat.total_generated_tokens * output_cost)
                total_cost += recall_cost
            except Exception as e:
                logger.warning(f"计算召回阶段成本时出错: {str(e)}")                
                recall_cost = 0.0
                total_cost += recall_cost
            rag_stat.recall_stat.cost = recall_cost    
        
        # 计算分块阶段成本
        if rag_stat.chunk_stat.model_name != "unknown":
            try:
                chunk_model = get_model_by_name(rag_stat.chunk_stat.model_name)
                input_cost = chunk_model.get("input_price", 0.0) / 1000000
                output_cost = chunk_model.get("output_price", 0.0) / 1000000
                chunk_cost = (rag_stat.chunk_stat.total_input_tokens * input_cost) + \
                            (rag_stat.chunk_stat.total_generated_tokens * output_cost)
                total_cost += chunk_cost
            except Exception as e:
                logger.warning(f"计算分块阶段成本时出错: {str(e)}")
                # 使用默认值
                chunk_cost = 0.0
                total_cost += chunk_cost
            rag_stat.chunk_stat.cost = chunk_cost    
        
        # 计算答案生成阶段成本
        if rag_stat.answer_stat.model_name != "unknown":
            try:
                answer_model = get_model_by_name(rag_stat.answer_stat.model_name)
                input_cost = answer_model.get("input_price", 0.0) / 1000000
                output_cost = answer_model.get("output_price", 0.0) / 1000000
                answer_cost = (rag_stat.answer_stat.total_input_tokens * input_cost) + \
                             (rag_stat.answer_stat.total_generated_tokens * output_cost)
                total_cost += answer_cost
            except Exception as e:
                logger.warning(f"计算答案生成阶段成本时出错: {str(e)}")
                # 使用默认值
                answer_cost = 0.0
                total_cost += answer_cost
            rag_stat.answer_stat.cost = answer_cost
            
        # 计算其他阶段成本（如果存在）
        for i, other_stat in enumerate(rag_stat.other_stats):
            if other_stat.model_name != "unknown":
                try:
                    other_model = get_model_by_name(other_stat.model_name)
                    input_cost = other_model.get("input_price", 0.0) / 1000000
                    output_cost = other_model.get("output_price", 0.0) / 1000000
                    other_cost = (other_stat.total_input_tokens * input_cost) + \
                                (other_stat.total_generated_tokens * output_cost)
                    total_cost += other_cost
                except Exception as e:
                    logger.warning(f"计算其他阶段 {i+1} 成本时出错: {str(e)}")
                    # 使用默认值
                    other_cost = 0.0
                    total_cost += other_cost
                rag_stat.other_stats[i].cost = other_cost
        
        # 将总成本保存到 rag_stat
        rag_stat.cost = total_cost
        return total_cost
