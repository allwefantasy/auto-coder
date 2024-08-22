from typing import Any, Dict, List, Optional, Tuple, Generator
from autocoder.common import AutoCoderArgs, SourceCode
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
        self.required_exts = [ext.strip() for ext in self.args.required_exts.split(",")] if self.args.required_exts else []

    @byzerllm.prompt()
    def _check_relevance(self, query: str, document: str) -> str:
        """
        请判断以下文档是否能够回答给出的问题。

        文档：
        {{ document }}

        问题：{{ query }}

        如果该文档提供的知识能够回答问题，那么请回复"yes" 否则回复"no"。
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

    def _retrieve_documents(self) -> List[SourceCode]:
        documents = []
        for root, dirs, files in os.walk(self.path):
            for file in files:
                if self.required_exts:
                    if not any(file.endswith(ext) for ext in self.required_exts):
                        continue
                else:
                    if not file.endswith(".md"):
                        continue
                file_path = os.path.join(root, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    relative_path = os.path.relpath(file_path, self.path)
                    documents.append(
                        SourceCode(module_name=relative_path, source_code=content)
                    )
        return documents

    def stream_chat_oai(
        self,
        conversations,
        model: Optional[str] = None,
        role_mapping=None,
        llm_config: Dict[str, Any] = {},
    ):
        query = conversations[-1]["content"]
        documents = self._retrieve_documents()

        with ThreadPoolExecutor(
            max_workers=self.args.index_filter_workers or 5
        ) as executor:
            future_to_doc = {
                executor.submit(
                    self._check_relevance.with_llm(self.llm).run,
                    query,
                    f"##File: {doc.module_name}\n{doc.source_code}",
                ): doc
                for doc in documents
            }
            relevant_docs = []
            for future in as_completed(future_to_doc):
                try:
                    doc = future_to_doc[future]
                    v = future.result()
                    logger.info(
                        f"Query: {query} Document: {doc.module_name}, Relevance: {v}"
                    )
                    if "yes" in v.strip().lower():
                        relevant_docs.append(doc.source_code)
                except Exception as exc:
                    logger.error(f"Document processing generated an exception: {exc}")

        if not relevant_docs:
            return ["没有找到相关的文档来回答这个问题。"], []
        else:
            relevant_docs = relevant_docs[: self.args.index_filter_file_num]
            context = "\n".join(relevant_docs)

            # 构建新的对话历史，包含除最后一条外的所有对话
            new_conversations = conversations[:-1] + [
                {
                    "role": "user",
                    "content": self._answer_question.prompt(
                        query=query, relevant_docs=relevant_docs
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
            return (chunk[0] for chunk in chunks), []
