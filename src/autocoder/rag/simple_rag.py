from typing import Any, Dict, List, Optional, Tuple
from autocoder.common import SourceCode, AutoCoderArgs
from autocoder.rag.simple_directory_reader import AutoCoderSimpleDirectoryReader
import fsspec

from byzerllm.apps.llama_index.simple_retrieval import SimpleRetrieval
from byzerllm.apps.llama_index.collection_manager import (
    CollectionManager,
    CollectionItem,
)
from byzerllm.utils.ray_utils import is_ray_in_client_mode

from llama_index.core import QueryBundle, StorageContext
from llama_index.core.readers.file.base import default_file_metadata_func
from llama_index.core import VectorStoreIndex
from llama_index.core.node_parser import HierarchicalNodeParser, get_leaf_nodes
from llama_index.core.base.llms.types import ChatMessage, MessageRole
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine, RouterQueryEngine
from llama_index.core.tools import QueryEngineTool
from llama_index.core.selectors import (
    LLMSingleSelector,
)

import byzerllm
from loguru import logger
import hashlib
import json
from openai import OpenAI
from typing import Union
from llama_index.core.schema import QueryBundle, NodeWithScore


def file_metadata_func(
    file_path: str, fs: Optional[fsspec.AbstractFileSystem] = None
) -> Dict:
    """Get some handy metadata from filesystem.

    Args:
        file_path: str: file path in str
    """

    def generate_file_md5(file_path: str) -> str:
        md5_hash = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                md5_hash.update(chunk)
        return md5_hash.hexdigest()

    return {
        **default_file_metadata_func(file_path=file_path, fs=fs),
        "md5": generate_file_md5(file_path=file_path),
    }


class LLMRerank:
    def __init__(self, llm: byzerllm.ByzerLLM):
        self.llm = llm        

    @byzerllm.prompt(llm=lambda self: self.llm)
    def rereank(self, context_str: str, query_str: str) -> str:
        '''
        以下显示了一份文档列表。每个文档旁边都有一个编号以及该文档的摘要。还提供了一个问题。
        回答问题时，请按照相关性顺序列出你应该参考的文档的编号，并给出相关性评分。相关性评分是一个1-10的数字，基于你认为该文档与问题的相关程度。
        不要包括任何与问题无关的文档。
        示例格式：
        文档1：
        <文档1的摘要>

        文档2：
        <文档2的摘要>

        ...

        文档10：
        <文档10的摘要>

        问题：<问题>
        回答：
        文档：9，相关性：7
        文档：3，相关性：4
        文档：7，相关性：3

        现在让我们试一试：

        {{ context_str }}

        问题：{{ query_str }}
        回答：
        '''

    def postprocess_nodes(self,
                         nodes: List[NodeWithScore], 
                         query_bundle: Union[str, QueryBundle],
                         choice_batch_size: int = 5, 
                         top_n: int = 1,
                         verbose: bool = False) -> List[NodeWithScore]:                          
        if isinstance(query_bundle, str):
            query_bundle = QueryBundle(query_str=query_bundle)

        # 给每个节点添加全局索引
        indexed_nodes = list(enumerate(nodes))

        # 按 choice_batch_size 切分 nodes
        node_batches = [indexed_nodes[i:i+choice_batch_size] for i in range(0, len(indexed_nodes), choice_batch_size)]

        # 合并排序后的结果
        sorted_nodes = []
        for batch in node_batches:
            context_str = "\n\n".join([f"文档{idx}:\n{node.node.get_text()}" for idx, node in batch])            
            rerank_output = self.rereank(context_str, query_bundle.query_str)
            if verbose:
                logger.info(self.rereank.prompt(context_str, query_bundle.query_str))
                logger.info(rerank_output)

            # 解析 rerank 的输出
            rerank_result = []
            for line in rerank_output.split("\n"):
                if line.startswith("文档："):
                    parts = line.split("，")
                    if len(parts) == 2:
                        try:
                            doc_idx = int(parts[0].split("：")[1])
                            relevance = float(parts[1].split("：")[1])
                            rerank_result.append((doc_idx, relevance))
                        except:
                            logger.warning(f"Failed to parse line: {line}")
                            pass

            # 更新 batch 中节点的分数
            for doc_idx, relevance in rerank_result:                  
                indexed_nodes[doc_idx][1].score = relevance

        sorted_nodes.extend([node for _, node in sorted(indexed_nodes, key=lambda x: x[1].score, reverse=True)])

        return sorted_nodes[:top_n]


class SimpleRAG:
    def __init__(self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs, path: str) -> None:
        from byzerllm.apps.llama_index import get_service_context, get_storage_context

        self.llm = llm
        self.args = args
        self.path = path
        self.collection_manager = CollectionManager(args.base_dir)

        self.collections = self.args.collection
        if self.args.collections:
            self.collections = self.args.collections

        self.collections = self.collections.split(",") if self.collections else []

        if not self.collections:
            logger.warning(
                """No RAG collection is set, we will use the `default` collection.
You can set the collection by passing the `--collections`argument in command line or set the `collections` attribute in the config file."""
            )
            self.collections = ["default"]

        if not self.llm.default_emb_model_name:
            raise ValueError("emb_model should be set")

        self.retrieval = byzerllm.ByzerRetrieval()

        if not is_ray_in_client_mode():
            self.retrieval.launch_gateway()
            self.service_context = get_service_context(self.llm)
            self.storage_context_dict: Dict[str, StorageContext] = {}
            for collection in self.collections:
                self.storage_context_dict[collection] = get_storage_context(
                    self.llm,
                    self.retrieval,
                    chunk_collection=collection,
                    namespace=collection,
                )

            self.simple_retrieval_dict: Dict[str, SimpleRetrieval] = {}
            for collection in self.collections:
                self.simple_retrieval_dict[collection] = SimpleRetrieval(
                    llm=llm, retrieval=self.retrieval, chunk_collection=collection
                )
        else:
            if not args.rag_url:
                raise ValueError(
                    "You are in client mode, please provide the RAG URL. e.g. rag_url: http://localhost:8000/v1"
                )
            
            if not args.rag_url.startswith("http://"):
                raise ValueError("The RAG URL should start with http://")
            
            self.client = OpenAI(api_key=args.rag_token, base_url=args.rag_url)

    def _get_indices(self) -> List[Tuple[CollectionItem, VectorStoreIndex]]:
        indices = []
        for collection in self.collections:
            storage_context = self.storage_context_dict[collection]
            index = VectorStoreIndex.from_vector_store(
                vector_store=storage_context.vector_store,
                service_context=self.service_context,
            )
            collection_item = self.collection_manager.get_collection(collection)
            indices.append((collection_item, index))

        return indices

    def _get_query_engine(self, streaming: bool = False):
        indices = self._get_indices()
        retrievers = []

        for collection_item, index in indices:
            retriever = AutoMergingRetriever(
                index.as_retriever(),
                storage_context=self.storage_context_dict[collection_item.name],
            )
            retrievers.append(retriever)

        query_engines = [
            RetrieverQueryEngine.from_args(
                retriever, service_context=self.service_context, streaming=streaming
            )
            for retriever in retrievers
        ]

        if len(query_engines) == 1:
            return query_engines[0]

        tools = []
        for (collection_item, index), query_engine in zip(indices, query_engines):
            tool = QueryEngineTool.from_defaults(
                query_engine=query_engine,
                description=collection_item.description,
            )
            tools.append(tool)

        query_engine = RouterQueryEngine(
            selector=LLMSingleSelector.from_defaults(
                service_context=self.service_context
            ),
            query_engine_tools=tools,
            llm=self.service_context.llm,
            service_context=self.service_context,
            verbose=True,
        )
        return query_engine

    def _get_retriever(self):
        indices = self._get_indices()
        retrievers = []

        for collection_item, index in indices:
            retriever = AutoMergingRetriever(
                index.as_retriever(),
                storage_context=self.storage_context_dict[collection_item.name],
            )
            retrievers.append(retriever)

        return retrievers

    def stream_search(self, query: str):
        query_bundle = QueryBundle(query_str=query)
        query_engine = self._get_query_engine(streaming=True)
        streaming_response = query_engine.query(query_bundle)
        contexts = []
        for node in streaming_response.source_nodes:
            contexts.append(
                {
                    "raw_chunk": node.node.text,
                    "doc_url": node.node.metadata["file_path"],
                    "_id": node.node.id_,
                }
            )
        return streaming_response.response_gen, contexts

    def retrieve(self, query: str) -> List[Dict[str, Any]]:
        query_bundle = QueryBundle(query_str=query)
        retrievers = self._get_retriever()

        result = []

        for retriever in retrievers:
            nodes = retriever.retrieve(query_bundle)

            reranker = LLMRerank(llm=self.llm)
            retrieved_nodes = reranker.postprocess_nodes(
                nodes, query_bundle, choice_batch_size=5, top_n=1
            )
            result.extend(
                [
                    {
                        "raw_chunk": node.node.text,
                        "doc_url": node.node.metadata["file_path"],
                        "_id": node.node.id_,
                    }
                    for node in retrieved_nodes
                ]
            )
        return result

    def stream_chat_oai(
        self,
        conversations,
        model: Optional[str] = None,
        role_mapping=None,
        llm_config: Dict[str, Any] = {},
    ):
        if len(self.collections) != 1:
            raise ValueError("When chat mode, only one collection can be set")

        index = VectorStoreIndex.from_vector_store(
            vector_store=self.storage_context_dict[self.collections[0]].vector_store,
            service_context=self.service_context,
        )
        chat_engine = index.as_chat_engine(
            chat_mode="condense_plus_context",
            verbose=False,
        )
        history = []
        for conv in conversations[:-1]:
            if conv["role"] == "user":
                role = MessageRole.USER
            elif conv["role"] == "assistant":
                role = MessageRole.ASSISTANT
            else:
                role = MessageRole.SYSTEM
            history.append(ChatMessage(role=role, content=conv["content"]))
        return (
            chat_engine.stream_chat(
                conversations[-1]["content"], chat_history=history
            ).response_gen,
            [],
        )

    def stream_chat_repl(self, query: str):
        if len(self.collections) != 1:
            raise ValueError("When chat mode, only one collection can be set")
        from llama_index.core.memory import ChatMemoryBuffer

        memory = ChatMemoryBuffer.from_defaults(token_limit=8092)
        index = VectorStoreIndex.from_vector_store(
            vector_store=self.storage_context_dict[self.collections[0]].vector_store,
            service_context=self.service_context,
        )
        chat_engine = index.as_chat_engine(
            chat_mode="condense_plus_context",
            memory=memory,
            verbose=False,
        )
        chat_engine.streaming_chat_repl()

    def search(self, query: str) -> List[SourceCode]:
        if not is_ray_in_client_mode():
            return self.inner_search(query)

        target_query = query

        if isinstance(self.args.enable_rag_search, str):
            target_query = self.args.enable_rag_search

        response = self.client.chat.completions.create(
            messages=[{"role": "user", "content": target_query}],
            model="xxxx",
        )
        return [
            SourceCode(
                module_name=f"RAG:{target_query}",
                source_code=response.choices[0].message.content,
            )
        ]

    def inner_search(self, query: str) -> List[SourceCode]:
        if self.args.enable_rag_search:
            target_query = query
            if isinstance(self.args.enable_rag_search, str):
                target_query = self.args.enable_rag_search
            texts, contexts = self.stream_search(target_query)
            s = "".join([text for text in texts])
            urls = ",".join(set([context["doc_url"] for context in contexts]))
            ## append RAG: prefix is used to protect avoid the source code is modified by the code auto execute
            return [SourceCode(module_name=f"RAG:{urls}", source_code=s)]
        elif self.args.enable_rag_context:
            target_query = query
            if isinstance(self.args.enable_rag_context, str):
                target_query = self.args.enable_rag_context
            contexts = self.retrieve(target_query)
            for context in contexts:
                context["raw_chunk"]
                try:
                    with open(context["doc_url"], "r") as f:
                        context["raw_chunk"] = f.read()
                except Exception as e:
                    logger.warning(f"Error reading file {context['doc_url']}")
                    pass

            return [
                SourceCode(
                    module_name=context["doc_url"], source_code=context["raw_chunk"]
                )
                for context in contexts
            ]
        return []

    def build(self):

        if len(self.collections) != 1:
            raise ValueError("When build, only one collection should be set")

        if is_ray_in_client_mode():
            raise ValueError(
                "You are in client mode, please run the build in the server."
            )

        collection = self.collections[0]

        collection_exists = self.collection_manager.check_collection_exists(collection)
        if not collection_exists:
            logger.warning(
                f"Collection {collection} not found, creating it automatically"
            )
            if not self.args.description:
                logger.error("Please provide a description for the collection")
                return
            item = CollectionItem(
                name=collection, description=self.args.description or ""
            )
            self.collection_manager.add_collection(item)

        retrieval_client = self.simple_retrieval_dict[collection]
        # retrieval_client.delete_from_doc_collection(collection)
        # retrieval_client.delete_from_chunk_collection(collection)

        required_exts = self.args.required_exts or None

        if required_exts:
            required_exts = required_exts.split(",")

        documents = AutoCoderSimpleDirectoryReader(
            self.path,
            recursive=True,
            filename_as_id=True,
            required_exts=required_exts,
            file_metadata=file_metadata_func,
        ).load_data()
        docs_keep = []
        for document in documents:
            doc = retrieval_client.get_doc(
                f"ref_doc_info/{document.doc_id}", collection
            )
            if doc:
                md5 = json.loads(doc["json_data"])["metadata"].get("md5", "")
                file_path = document.metadata["file_path"]
                new__md5 = document.metadata["md5"]
                if md5 != new__md5:
                    retrieval_client.delete_doc_and_chunks_by_filename(
                        collection, file_path
                    )
                    docs_keep.append(document)
            else:
                docs_keep.append(document)

        retrieval_client.commit_doc()
        retrieval_client.commit_chunk()

        for document in docs_keep:
            logger.info(f"\nUpsert {document.doc_id}")

        if docs_keep:
            hirerachical = HierarchicalNodeParser.from_defaults(
                chunk_sizes=[6000, 3000, 1024]
            )
            # sp = SentenceSplitter(chunk_size=1024, chunk_overlap=0)

            nodes = hirerachical.get_nodes_from_documents(docs_keep, show_progress=True)

            leaf_nodes = get_leaf_nodes(nodes)
            self.storage_context_dict[collection].docstore.add_documents(nodes)

            _ = VectorStoreIndex(
                nodes=leaf_nodes,
                store_nodes_override=True,
                storage_context=self.storage_context_dict[collection],
                service_context=self.service_context,
            )

            retrieval_client.commit_doc()
            retrieval_client.commit_chunk()
        else:
            logger.info("There is no new doc to build")
