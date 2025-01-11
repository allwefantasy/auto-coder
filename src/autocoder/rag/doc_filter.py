import time
from typing import List, Dict, Optional
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed

from autocoder.rag.relevant_utils import (
    parse_relevance,
    FilterDoc,    
    TaskTiming,
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
        self.relevant_score = self.args.rag_doc_filter_relevance or 5
        self.on_ray = on_ray
        self.path = path        

    def filter_docs(
        self, conversations: List[Dict[str, str]], documents: List[SourceCode]
    ) -> List[FilterDoc]:
        return self.filter_docs_with_threads(conversations, documents)            

    def filter_docs_with_threads(
        self, conversations: List[Dict[str, str]], documents: List[SourceCode]
    ) -> List[FilterDoc]:
        
        rag_manager = RagConfigManager(path=self.path)
        rag_config = rag_manager.load_config()
        documents = list(documents)   
        logger.info(f"Filtering {len(documents)} documents....")
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
                        llm.skip_nontext_check = True
                        llm.setup_default_model_name(self.recall_llm.default_model_name)

                        v = (
                            _check_relevance_with_conversation.with_llm(
                                llm)
                            .options({"llm_config": {"max_length": 10}})
                            .run(
                                conversations=conversations,
                                documents=docs,
                                filter_config=rag_config.filter_config,
                            )
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

                relevance = parse_relevance(v)
                logger.info(
                    f"Document filtering progress:\n"
                    f"  - File: {doc.module_name}\n"
                    f"  - Relevance: {'Relevant' if relevance and relevance.is_relevant else 'Not Relevant'}\n"
                    f"  - Score: {relevance.relevant_score if relevance else 'N/A'}\n"
                    f"  - Raw Response: {v}\n"
                    f"  - Timing:\n"
                    f"    * Total Duration: {task_timing.duration:.2f}s\n"
                    f"    * Real Duration: {task_timing.real_duration:.2f}s\n"
                    f"    * Queue Time: {(task_timing.real_start_time - task_timing.submit_time):.2f}s"
                )
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
                try:
                    doc, submit_time = future_to_doc[future]
                    logger.error(
                        f"Filtering document generated an exception (doc: {doc.module_name}): {exc}")
                except Exception as e:
                    logger.error(
                        f"Filtering document generated an exception: {exc}")

        # Sort relevant_docs by relevance score in descending order
        relevant_docs.sort(
            key=lambda x: x.relevance.relevant_score, reverse=True)
        return relevant_docs
    
