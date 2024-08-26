from typing import Any, Dict, List, Optional, Tuple, Generator
from autocoder.common import AutoCoderArgs, SourceCode
from concurrent.futures import ThreadPoolExecutor, as_completed
from byzerllm import ByzerLLM
from loguru import logger
import json
import os
from io import BytesIO
from pypdf import PdfReader
import docx2txt
import byzerllm
from openai import OpenAI
import pathspec


class LongContextRAG:
    def __init__(self, llm: ByzerLLM, args: AutoCoderArgs, path: str) -> None:
        self.llm = llm
        self.args = args        
        self.path = path

        self.required_exts = (
            [ext.strip() for ext in self.args.required_exts.split(",")]
            if self.args.required_exts
            else []
        )

        if args.rag_url and args.rag_url.startswith("http://"):
            if not args.rag_token:
                raise ValueError(
                    "You are in client mode, please provide the RAG token. e.g. rag_token: your_token_here"
                )
            self.client = OpenAI(api_key=args.rag_token, base_url=args.rag_url)
        else:
            self.client = None
            # if not pure client mode, then the path should be provided
            if not self.path and args.rag_url and not args.rag_url.startswith("http://"):
                self.path = args.rag_url
        
            if not self.path:
                raise ValueError("Please provide the path to the documents in the local file system.")

        self.gitignore_spec = self._load_gitignore()    

    def extract_text_from_pdf(self, pdf_content):
        pdf_file = BytesIO(pdf_content)
        pdf_reader = PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text

    def extract_text_from_docx(self, docx_content):
        docx_file = BytesIO(docx_content)
        text = docx2txt.process(docx_file)
        return text

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

    def _load_gitignore(self):
        gitignore_path = os.path.join(self.path, '.gitignore')
        if os.path.exists(gitignore_path):
            with open(gitignore_path, 'r') as gitignore_file:
                return pathspec.PathSpec.from_lines('gitwildmatch', gitignore_file)
        return None
    
    def _retrieve_documents(self) -> List[SourceCode]:
        documents = []
        for root, dirs, files in os.walk(self.path):
            # 过滤掉隐藏目录
            dirs[:] = [d for d in dirs if not d.startswith('.')]

            # 应用 .gitignore 规则
            if self.gitignore_spec:
                dirs[:] = [d for d in dirs if not self.gitignore_spec.match_file(os.path.join(root, d))]
                files = [f for f in files if not self.gitignore_spec.match_file(os.path.join(root, f))]
            
            for file in files:
                if self.required_exts:
                    if not any(file.endswith(ext) for ext in self.required_exts):
                        continue
                else:
                    if not file.endswith((".md", ".pdf", ".docx")):
                        continue
                file_path = os.path.join(root, file)
                relative_path = os.path.relpath(file_path, self.path)

                try:
                    if file.endswith(".pdf"):
                        with open(file_path, "rb") as f:
                            content = self.extract_text_from_pdf(f.read())
                    elif file.endswith(".docx"):
                        with open(file_path, "rb") as f:
                            content = self.extract_text_from_docx(f.read())
                    else:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read()

                    documents.append(
                        SourceCode(module_name=relative_path, source_code=content)
                    )
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")

        return documents

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

        logger.info("Search from RAG.....")    
        logger.info(f"Query: {target_query} only_contexts: {only_contexts}")

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
            return [
                SourceCode.model_validate(json_line) for json_line in json_lines
            ]
        else:
            if only_contexts:
                return self._filter_docs(target_query)
            else:
                v, contexts = self.stream_chat_oai(
                    conversations=[{"role": "user", "content": new_query}]
                )
                url = ",".join(contexts)
                return [SourceCode(module_name=f"RAG:{url}", source_code="".join(v))]

    def _filter_docs(self, query: str) -> List[SourceCode]:
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
                if "yes" in v.strip().lower():
                    relevant_docs.append(doc)
            except Exception as exc:
                logger.error(f"Document processing generated an exception: {exc}")
        return relevant_docs

    def stream_chat_oai(
        self,
        conversations,
        model: Optional[str] = None,
        role_mapping=None,
        llm_config: Dict[str, Any] = {},
    ):
        if self.client:
            query = conversations[-1]["content"]
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
            only_contexts = False
            try:
                v = json.loads(query)
                if "only_contexts" in v:
                    query = v["query"]
                    only_contexts = v["only_contexts"]

            except json.JSONDecodeError:
                pass
                        
            relevant_docs: List[SourceCode] = self._filter_docs(query)
            logger.info(f"Query: {query} Relevant docs: {len(relevant_docs)} only_contexts: {only_contexts}")

            if only_contexts:
                return (doc.model_dump_json() + "\n" for doc in relevant_docs), []

            if not relevant_docs:
                return ["没有找到相关的文档来回答这个问题。"], []
            else:
                relevant_docs = relevant_docs[: self.args.index_filter_file_num]
                context = [doc.module_name for doc in relevant_docs]

                # 构建新的对话历史，包含除最后一条外的所有对话
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
