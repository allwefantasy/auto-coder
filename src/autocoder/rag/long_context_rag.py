from typing import Any, Dict, List, Optional, Tuple, Generator
from autocoder.common import AutoCoderArgs
from concurrent.futures import ThreadPoolExecutor, as_completed
from byzerllm import ByzerLLM
from loguru import logger
import json
import os

import byzerllm


class LongContextRAG:
    def __init__(self, llm: ByzerLLM, args: AutoCoderArgs, path: str) -> None:
        self.llm = llm
        self.args = args
        self.path = path

    @byzerllm.prompt()
    def _check_relevance(self, query: str, document: str) -> str:
        """
        请判断以下文档是否能够回答给出的问题。
        只需回答"是"或"否"。

        问题：{{ query }}

        文档：
        {{ document }}

        回答：
        """

    @byzerllm.prompt()
    def _answer_question(self, query: str, relevant_docs: List[str]) -> str:
        """
        使用以下文档来回答问题。如果文档中没有相关信息，请说"我没有足够的信息来回答这个问题"。

        文档：
        {{ "\n\n".join(relevant_docs) }}

        问题：{{ query }}

        回答：
        """

    def stream_chat_oai(
        self,
        conversations,
        model: Optional[str] = None,
        role_mapping=None,
        llm_config: Dict[str, Any] = {},
    ):
        query = conversations[-1]["content"]
        documents = self._retrieve_documents()

        with ThreadPoolExecutor(max_workers=self.args.max_workers or 5) as executor:
            future_to_doc = {
                executor.submit(
                    self._check_relevance.with_llm(self.llm).run, query, doc
                ): doc
                for doc in documents
            }
            relevant_docs = []
            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    if "是" in future.result().strip().lower():
                        relevant_docs.append(doc)
                except Exception as exc:
                    logger.error(f"Document processing generated an exception: {exc}")

        if not relevant_docs:
            return (yield "没有找到相关的文档来回答这个问题。"), []

        response = self._answer_question.with_llm(self.llm).run(query, relevant_docs)
        return (yield from response), []

    def _retrieve_documents(self) -> List[str]:
        documents = []
        for root, dirs, files in os.walk(self.path):
            for file in files:
                if file.endswith(".md"):
                    file_path = os.path.join(root, file)
                    with open(file_path, "r", encoding="utf-8") as f:
                        documents.append(f.read())
        return documents
