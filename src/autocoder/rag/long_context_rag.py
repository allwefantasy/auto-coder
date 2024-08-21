from typing import Any, Dict, List, Optional, Tuple, Generator
from autocoder.common import AutoCoderArgs
from concurrent.futures import ThreadPoolExecutor, as_completed
from byzerllm import ByzerLLM
from loguru import logger
import json

class LongContextRAG:
    def __init__(self, llm: ByzerLLM, args: AutoCoderArgs, path: str) -> None:
        self.llm = llm
        self.args = args
        self.path = path

    def _check_relevance(self, query: str, document: str) -> bool:
        prompt = f"""
        请判断以下文档是否与给定的问题相关。
        只需回答"是"或"否"。

        问题：{query}

        文档：
        {document}

        回答：
        """
        response = self.llm.chat_oai(model=self.args.model, conversations=[
            {"role": "user", "content": prompt}
        ])
        return response[0].output.strip().lower() == "是"

    def _answer_question(self, query: str, relevant_docs: List[str]) -> Generator[str, None, None]:
        context = "\n\n".join(relevant_docs)
        prompt = f"""
        使用以下文档来回答问题。如果文档中没有相关信息，请说"我没有足够的信息来回答这个问题"。

        文档：
        {context}

        问题：{query}

        回答：
        """
        response = self.llm.stream_chat_oai(model=self.args.model, conversations=[
            {"role": "user", "content": prompt}
        ])
        for chunk in response:
            yield chunk[0]

    def stream_chat_oai(
        self,
        conversations,
        model: Optional[str] = None,
        role_mapping=None,
        llm_config: Dict[str, Any] = {},
    ) -> Tuple[Generator[str, None, None], List[Dict[str, Any]]]:
        query = conversations[-1]["content"]
        documents = self._retrieve_documents(query)

        with ThreadPoolExecutor(max_workers=self.args.max_workers or 5) as executor:
            future_to_doc = {executor.submit(self._check_relevance, query, doc): doc for doc in documents}
            relevant_docs = []
            for future in as_completed(future_to_doc):
                doc = future_to_doc[future]
                try:
                    if future.result():
                        relevant_docs.append(doc)
                except Exception as exc:
                    logger.error(f"Document processing generated an exception: {exc}")

        if not relevant_docs:
            return (yield "没有找到相关的文档来回答这个问题。"), []

        return self._answer_question(query, relevant_docs), []

    def _retrieve_documents(self, query: str) -> List[str]:
        # 这里应该实现文档检索的逻辑
        # 为了示例，我们返回一些虚拟的文档
        return [
            "这是第一篇文档，讨论了人工智能的发展。",
            "这是第二篇文档，介绍了机器学习的基本概念。",
            "这是第三篇文档，探讨了深度学习在图像识别中的应用。"
        ]
