import time
from typing import List, Dict, Optional
from pydantic import BaseModel
import ray
from loguru import logger
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich.console import Console

from autocoder.rag.relevant_utils import (
    parse_relevance,
    FilterDoc,
    DocRelevance,
    TaskTiming,
)

from autocoder.common import SourceCode, AutoCoderArgs
from byzerllm import ByzerLLM
import byzerllm


@byzerllm.prompt()
def _check_relevance_with_conversation(
    conversations: List[Dict[str, str]], documents: List[str]
) -> str:
    """
    使用以下文档和对话历史来回答问题。如果文档中没有相关信息，请说"我没有足够的信息来回答这个问题"。

    文档：
    {% for doc in documents %}
    {{ doc }}
    {% endfor %}

    对话历史：
    {% for msg in conversations %}
    <{{ msg.role }}>: {{ msg.content }}
    {% endfor %}

    请结合提供的文档以及用户对话历史，判断提供的文档是不是能回答用户的最后一个问题。
    如果该文档提供的知识能够回答问题，那么请回复"yes/<relevant>" 否则回复"no/<relevant>"。
    其中， <relevant> 是你认为文档中和问题的相关度，0-10之间的数字，数字越大表示相关度越高。
    """


@ray.remote
class DocFilterWorker:
    def __init__(self, llm: ByzerLLM):
        self.llm = llm

    def filter_doc(
        self, conversations: List[Dict[str, str]], docs: List[str]
    ) -> Optional[FilterDoc]:
        submit_time_1 = time.time()
        try:
            v = _check_relevance_with_conversation.with_llm(self.llm).run(
                conversations=conversations, documents=docs
            )
        except Exception as e:
            logger.error(f"Error in _check_relevance_with_conversation: {str(e)}")
            return (None, submit_time_1, time.time())

        end_time_2 = time.time()
        return (v, submit_time_1, end_time_2)


class DocFilter:
    def __init__(self, llm: ByzerLLM, args: AutoCoderArgs, on_ray: bool = False):
        self.llm = llm
        self.args = args
        self.relevant_score = self.args.rag_doc_filter_relevance or 5
        self.on_ray = on_ray
        if self.on_ray:
            cpu_count = os.cpu_count() or 1
            self.workers = [
                DocFilterWorker.options(max_concurrency=1000, num_cpus=0).remote(llm)
                for _ in range(cpu_count)
            ]

    def filter_docs(
        self, conversations: List[Dict[str, str]], documents: List[SourceCode]
    ) -> List[FilterDoc]:
        if self.on_ray:
            return self.filter_docs_with_ray(conversations, documents)
        else:
            return self.filter_docs_with_threads(conversations, documents)

    def filter_docs_with_threads(
        self, conversations: List[Dict[str, str]], documents: List[SourceCode]
    ) -> List[FilterDoc]:
        console = Console()
        documents = list(documents)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),            
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task(
                "[cyan]Filtering documents...", total=len(documents)
            )

            with ThreadPoolExecutor(
                max_workers=self.args.index_filter_workers or 5
            ) as executor:
                future_to_doc = {}
                for doc in documents:
                    submit_time = time.time()

                    def _run(conversations, docs):
                        submit_time_1 = time.time()                        
                        try:
                            llm = ByzerLLM()
                            llm.setup_default_model_name(self.llm.default_model_name)
                            llm.skip_nontext_check = True
                            v = _check_relevance_with_conversation.with_llm(llm).run(
                                conversations=conversations, documents=docs
                            )
                        except Exception as e:
                            logger.error(
                                f"Error in _check_relevance_with_conversation: {str(e)}"
                            )
                            return (None, submit_time_1, time.time())
 
                        end_time_2 = time.time()
                        return (v, submit_time_1, end_time_2)

                    m = executor.submit(
                        _run,
                        conversations,
                        [f"##File: {doc.module_name}\n{doc.source_code}"],
                    )
                    future_to_doc[m] = (doc, submit_time)

            relevant_docs = []
            for future in as_completed(list(future_to_doc.keys())):
                try:
                    doc, submit_time = future_to_doc[future]
                    end_time = time.time()
                    v, submit_time_1, end_time_2 = future.result()
                    task_timing = TaskTiming(
                        submit_time=submit_time,
                        end_time=end_time,
                        duration=end_time - submit_time,
                        real_start_time=submit_time_1,
                        real_end_time=end_time_2,
                        real_duration=end_time_2 - submit_time_1,
                    )
                    progress.update(task, advance=1)
                 
                    relevance = parse_relevance(v)
                    if (
                        relevance
                        and relevance.is_relevant
                        and relevance.relevant_score >= self.relevant_score
                    ):
                        relevant_docs.append(
                            FilterDoc(
                                source_code=doc,
                                relevance=relevance,
                                task_timing=task_timing,
                            )
                        )
                except Exception as exc:
                    logger.error(f"Document processing generated an exception: {exc}")

        # Sort relevant_docs by relevance score in descending order
        relevant_docs.sort(key=lambda x: x.relevance.relevant_score, reverse=True)
        return relevant_docs

    def filter_docs_with_ray(
        self, conversations: List[Dict[str, str]], documents: List[SourceCode]
    ) -> List[FilterDoc]:
        futures = []
        count = 0
        submit_time = time.time()
        for doc in documents:
            worker = self.workers[count % len(self.workers)]
            count += 1
            future = worker.filter_doc.remote(
                conversations, [f"##File: {doc.module_name}\n{doc.source_code}"]
            )
            futures.append((future, doc))

        relevant_docs = []
        for future, doc in futures:
            try:
                v, submit_time_1, end_time_2 = ray.get(future)
                end_time = time.time()

                if v is None:
                    continue

                task_timing = TaskTiming(
                    submit_time=submit_time,
                    end_time=end_time,
                    duration=end_time - submit_time,
                    real_start_time=submit_time_1,
                    real_end_time=end_time_2,
                    real_duration=end_time_2 - submit_time_1,
                )
                logger.info(
                    f"Document: {doc.module_name} Duration: {task_timing.duration:.2f} seconds/{task_timing.real_duration:.2f}/{task_timing.real_duration-task_timing.duration} seconds"
                )
                relevance = parse_relevance(v)
                if (
                    relevance
                    and relevance.is_relevant
                    and relevance.relevant_score >= self.relevant_score
                ):
                    relevant_docs.append(
                        FilterDoc(
                            source_code=doc,
                            relevance=relevance,
                            task_timing=task_timing,
                        )
                    )
            except Exception as exc:
                logger.error(f"Document processing generated an exception: {exc}")

        # Sort relevant_docs by relevance score in descending order
        relevant_docs.sort(key=lambda x: x.relevance.relevant_score, reverse=True)
        return relevant_docs
