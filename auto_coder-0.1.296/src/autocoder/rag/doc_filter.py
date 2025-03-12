import time
from typing import List, Dict, Optional, Generator, Tuple
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed
from autocoder.rag.lang import get_message_with_format_and_newline

from autocoder.rag.relevant_utils import (
    parse_relevance,
    FilterDoc,
    TaskTiming,
    DocFilterResult,
    ProgressUpdate
)

from autocoder.common import SourceCode, AutoCoderArgs
from autocoder.rag.rag_config import RagConfigManager
from byzerllm import ByzerLLM
import byzerllm


@byzerllm.prompt()
def _check_relevance_with_conversation(
    conversations: List[Dict[str, str]],
    documents: List[str],
    filter_config: Optional[str] = None,
) -> str:
    """
    使用以下文档和对话历史来回答问题。如果文档中没有相关信息，请说"我没有足够的信息来回答这个问题"。

    文档：
    <documents>
    {% for doc in documents %}
    {{ doc }}
    {% endfor %}
    </documents>

    对话历史：
    <conversations>
    {% for msg in conversations %}
    <{{ msg.role }}>: {{ msg.content }}
    {% endfor %}
    </conversations>

    {% if filter_config %}
    一些提示：
    {{ filter_config }}
    {% endif %}

    请结合提供的文档以及用户对话历史，判断提供的文档是不是能和用户的最后一个问题相关。
    如果该文档提供的知识能够和用户的问题相关，那么请回复"yes/<relevant>" 否则回复"no/<relevant>"。
    其中， <relevant> 是你认为文档中和问题的相关度，0-10之间的数字，数字越大表示相关度越高。
    """


class DocFilter:
    def __init__(
        self,
        llm: ByzerLLM,
        args: AutoCoderArgs,
        on_ray: bool = False,
        path: Optional[str] = None,
    ):
        self.llm = llm
        if self.llm.get_sub_client("recall_model"):
            self.recall_llm = self.llm.get_sub_client("recall_model")
        else:
            self.recall_llm = self.llm

        self.args = args
        self.relevant_score = self.args.rag_doc_filter_relevance
        self.on_ray = on_ray
        self.path = path

    def filter_docs(
        self, conversations: List[Dict[str, str]], documents: List[SourceCode]
    ) -> DocFilterResult:
        return self.filter_docs_with_threads(conversations, documents)

    def filter_docs_with_progress(
        self, conversations: List[Dict[str, str]], documents: List[SourceCode]
    ) -> Generator[Tuple[ProgressUpdate, Optional[DocFilterResult]], None, DocFilterResult]:
        """使用线程过滤文档，同时产生进度更新"""
        start_time = time.time()
        logger.info(f"=== DocFilter Starting ===")
        logger.info(
            f"Configuration: relevance_threshold={self.relevant_score}, thread_workers={self.args.index_filter_workers or 5}")

        rag_manager = RagConfigManager(path=self.path)
        rag_config = rag_manager.load_config()

        documents = list(documents)
        logger.info(f"Filtering {len(documents)} documents...")

        submitted_tasks = 0
        completed_tasks = 0
        relevant_count = 0
        model_name = self.recall_llm.default_model_name or "unknown"

        doc_filter_result = DocFilterResult(
            docs=[],
            raw_docs=[],
            input_tokens_counts=[],
            generated_tokens_counts=[],
            durations=[],
            model_name=model_name
        )
        relevant_docs = doc_filter_result.docs

        with ThreadPoolExecutor(
            max_workers=self.args.index_filter_workers or 5
        ) as executor:
            future_to_doc = {}

            # 提交所有任务
            for doc in documents:
                submit_time = time.time()
                submitted_tasks += 1

                def _run(conversations, docs):
                    submit_time_1 = time.time()
                    meta = None
                    try:
                        llm = self.recall_llm
                        meta_holder = byzerllm.MetaHolder()

                        v = (
                            _check_relevance_with_conversation.with_llm(
                                llm).with_meta(meta_holder)
                            .options({"llm_config": {"max_length": 10}})
                            .run(
                                conversations=conversations,
                                documents=docs,
                                filter_config=rag_config.filter_config,
                            )
                        )

                        meta = meta_holder.get_meta_model()
                    except Exception as e:
                        logger.error(
                            f"Error in _check_relevance_with_conversation: {str(e)}"
                        )
                        return (None, submit_time_1, time.time(), meta)

                    end_time_2 = time.time()
                    return (v, submit_time_1, end_time_2, meta)

                m = executor.submit(
                    _run,
                    conversations,
                    [f"##File: {doc.module_name}\n{doc.source_code}"],
                )
                future_to_doc[m] = (doc, submit_time)

            logger.info(
                f"Submitted {submitted_tasks} document filtering tasks to thread pool")

            # 发送初始进度更新
            yield (ProgressUpdate(
                phase="doc_filter",
                completed=0,
                total=len(documents),
                relevant_count=0,
                message=get_message_with_format_and_newline(
                    "doc_filter_start",
                    total=len(documents)
                )
            ), None)

            # 处理完成的任务
            for future in as_completed(list(future_to_doc.keys())):
                try:
                    doc, submit_time = future_to_doc[future]
                    end_time = time.time()
                    completed_tasks += 1
                    progress_percent = (completed_tasks / len(documents)) * 100

                    v, submit_time_1, end_time_2, meta = future.result()
                    task_timing = TaskTiming(
                        submit_time=submit_time,
                        end_time=end_time,
                        duration=end_time - submit_time,
                        real_start_time=submit_time_1,
                        real_end_time=end_time_2,
                        real_duration=end_time_2 - submit_time_1,
                    )

                    relevance = parse_relevance(v)
                    is_relevant = relevance and relevance.relevant_score >= self.relevant_score

                    if is_relevant:
                        relevant_count += 1
                        status_text = f"RELEVANT (Score: {relevance.relevant_score:.1f})"
                    else:
                        score_text = f"{relevance.relevant_score:.1f}" if relevance else "N/A"
                        status_text = f"NOT RELEVANT (Score: {score_text})"

                    queue_time = task_timing.real_start_time - task_timing.submit_time

                    input_tokens_count = meta.input_tokens_count if meta else 0
                    generated_tokens_count = meta.generated_tokens_count if meta else 0

                    logger.info(
                        f"Document filtering [{progress_percent:.1f}%] - {completed_tasks}/{len(documents)}:"
                        f"\n  - File: {doc.module_name}"
                        f"\n  - Status: {status_text}"
                        f"\n  - Model: {model_name}"
                        f"\n  - Threshold: {self.relevant_score}"
                        f"\n  - Input tokens: {input_tokens_count}"
                        f"\n  - Generated tokens: {generated_tokens_count}"
                        f"\n  - Timing: Duration={task_timing.duration:.2f}s, Processing={task_timing.real_duration:.2f}s, Queue={queue_time:.2f}s"
                        f"\n  - Response: {v}"
                    )

                    if "rag" not in doc.metadata:
                        doc.metadata["rag"] = {}
                    doc.metadata["rag"]["recall"] = {
                        "input_tokens_count": input_tokens_count,
                        "generated_tokens_count": generated_tokens_count,
                        "recall_model": model_name,
                        "duration": task_timing.real_duration
                    }

                    doc_filter_result.input_tokens_counts.append(
                        input_tokens_count)
                    doc_filter_result.generated_tokens_counts.append(
                        generated_tokens_count)
                    doc_filter_result.durations.append(
                        task_timing.real_duration)

                    new_filter_doc = FilterDoc(
                        source_code=doc,
                        relevance=relevance,
                        task_timing=task_timing,
                    )

                    doc_filter_result.raw_docs.append(new_filter_doc)

                    if is_relevant:
                        relevant_docs.append(
                            new_filter_doc
                        )

                    # 产生进度更新
                    yield (ProgressUpdate(
                        phase="doc_filter",
                        completed=completed_tasks,
                        total=len(documents),
                        relevant_count=relevant_count,
                        message=get_message_with_format_and_newline(
                            "doc_filter_progress",
                            progress_percent=progress_percent,
                            relevant_count=relevant_count,
                            total=len(documents)
                        )
                    ), None)

                except Exception as exc:
                    try:
                        doc, submit_time = future_to_doc[future]
                        completed_tasks += 1
                        progress_percent = (
                            completed_tasks / len(documents)) * 100
                        logger.error(
                            f"Document filtering [{progress_percent:.1f}%] - {completed_tasks}/{len(documents)}:"
                            f"\n  - File: {doc.module_name}"
                            f"\n  - Error: {exc}"
                            f"\n  - Duration: {time.time() - submit_time:.2f}s"
                        )
                        doc_filter_result.raw_docs.append(
                            FilterDoc(
                                source_code=doc,
                                relevance=None,
                                task_timing=TaskTiming(),
                            )
                        )
                    except Exception as e:
                        logger.error(
                            f"Document filtering error in task tracking: {exc}"
                        )

                    # 报告错误进度
                    yield (ProgressUpdate(
                        phase="doc_filter",
                        completed=completed_tasks,
                        total=len(documents),
                        relevant_count=relevant_count,
                        message=get_message_with_format_and_newline(
                            "doc_filter_error",
                            error=str(exc)
                        )
                    ), None)

        # Sort relevant_docs by relevance score in descending order
        relevant_docs.sort(
            key=lambda x: x.relevance.relevant_score, reverse=True)

        total_time = time.time() - start_time

        avg_processing_time = sum(
            doc.task_timing.real_duration for doc in relevant_docs) / len(relevant_docs) if relevant_docs else 0
        avg_queue_time = sum(doc.task_timing.real_start_time -
                             doc.task_timing.submit_time for doc in relevant_docs) / len(relevant_docs) if relevant_docs else 0

        total_input_tokens = sum(doc_filter_result.input_tokens_counts)
        total_generated_tokens = sum(doc_filter_result.generated_tokens_counts)

        logger.info(
            f"=== DocFilter Complete ==="
            f"\n  * Total time: {total_time:.2f}s"
            f"\n  * Documents processed: {completed_tasks}/{len(documents)}"
            f"\n  * Relevant documents: {relevant_count} (threshold: {self.relevant_score})"
            f"\n  * Average processing time: {avg_processing_time:.2f}s"
            f"\n  * Average queue time: {avg_queue_time:.2f}s"
            f"\n  * Total input tokens: {total_input_tokens}"
            f"\n  * Total generated tokens: {total_generated_tokens}"
        )

        if relevant_docs:
            logger.info(
                f"Top 5 relevant documents:"
                + "".join([f"\n  * {doc.source_code.module_name} (Score: {doc.relevance.relevant_score:.1f})"
                          for doc in relevant_docs[:5]])
            )
        else:
            logger.warning("No relevant documents found!")

        # 返回最终结果
        yield (ProgressUpdate(
            phase="doc_filter",
            completed=len(documents),
            total=len(documents),
            relevant_count=relevant_count,
            message=get_message_with_format_and_newline(
                "doc_filter_complete",
                total_time=total_time,
                relevant_count=relevant_count
            )
        ), doc_filter_result)

    def filter_docs_with_threads(
        self, conversations: List[Dict[str, str]], documents: List[SourceCode]
    ) -> DocFilterResult:
        # 保持兼容性的接口
        for _, result in self.filter_docs_with_progress(conversations, documents):
            if result is not None:
                return result

        # 这是一个应急情况，不应该到达这里
        return DocFilterResult(
            docs=[],
            raw_docs=[],
            input_tokens_counts=[],
            generated_tokens_counts=[],
            durations=[],
            model_name=self.recall_llm.default_model_name or "unknown"
        )
