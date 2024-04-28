from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from autocoder.common import SourceCode,AutoCoderArgs
from autocoder.common.llm_rerank import LLMRerank
import fsspec
import os

from byzerllm.apps.llama_index.simple_retrieval import SimpleRetrieval
from byzerllm.apps.llama_index import get_service_context,get_storage_context
from llama_index.core import QueryBundle
from llama_index.core.readers.file.base import default_file_metadata_func
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, ServiceContext
from llama_index.core.node_parser import SentenceSplitter,HierarchicalNodeParser,get_leaf_nodes, get_root_nodes
from llama_index.core.base.llms.types import ChatMessage,MessageRole
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
import byzerllm
from loguru import logger
import hashlib
import json


def file_metadata_func(
    file_path: str, fs: Optional[fsspec.AbstractFileSystem] = None
) -> Dict:
    """Get some handy metadata from filesystem.

    Args:
        file_path: str: file path in str
    """    
    def generate_file_md5(file_path: str) -> str:
        md5_hash = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                md5_hash.update(chunk)
        return md5_hash.hexdigest() 
        
    return { ** default_file_metadata_func(file_path=file_path,fs=fs),
        "md5":generate_file_md5(file_path=file_path)
    }



class SimpleRAG:
    def __init__(self,llm:byzerllm.ByzerLLM,args:AutoCoderArgs,path:str) -> None:
        self.llm = llm
        self.args = args
        self.retrieval = byzerllm.ByzerRetrieval()
        self.retrieval.launch_gateway()        
        self.path = path
        self.namespace = "default"
        self.chunk_collection = "default"
        if not self.llm.default_emb_model_name:
            raise ValueError("emb_model should be set")

        self.service_context = get_service_context(self.llm)
        self.storage_context = get_storage_context(self.llm,self.retrieval,
                                                   chunk_collection=self.chunk_collection,
                                                   namespace=self.namespace)
        self.simple_retrieval = SimpleRetrieval(llm=llm, retrieval=self.retrieval,chunk_collection=self.chunk_collection)        

    def stream_search(self,query:str):     
        query_bundle = QueryBundle(query_str=query)   
        index = VectorStoreIndex.from_vector_store(vector_store = self.storage_context.vector_store,
                                                   service_context=self.service_context)
        retriever = AutoMergingRetriever(index.as_retriever(),storage_context=self.storage_context,verbose=True)
        query_engine = RetrieverQueryEngine.from_args(retriever,
                                                      service_context=self.service_context,
                                                      streaming=True)
        # query_engine = index.as_query_engine(streaming=True)       
        
        streaming_response = query_engine.query(query_bundle)
        contexts = []
        for node in streaming_response.source_nodes:
            contexts.append({
                "raw_chunk":node.node.text,
                "doc_url":node.node.metadata["file_path"],
                "_id":node.node.id_,
                
            })
        return streaming_response.response_gen,contexts 
    
    def retrieve(self,query:str)->List[SourceCode]:
        query_bundle = QueryBundle(query_str=query)
        index = VectorStoreIndex.from_vector_store(vector_store = self.storage_context.vector_store,
                                                   service_context=self.service_context)
        retrieval_engine = AutoMergingRetriever(index.as_retriever(),storage_context=self.storage_context)
        nodes = retrieval_engine.retrieve(query_bundle) 

        reranker = LLMRerank(llm=self.llm)
        retrieved_nodes = reranker.postprocess_nodes(nodes, query_bundle,choice_batch_size=5, top_n=1)
        return [
            {
                "raw_chunk":node.node.text,
                "doc_url":node.node.metadata["file_path"],
                "_id":node.node.id_,
                
            } for node in retrieved_nodes
        ]
    
    def stream_chat_oai(self,conversations, model:Optional[str]=None, role_mapping=None,llm_config:Dict[str,Any]={}):        
        index = VectorStoreIndex.from_vector_store(vector_store = self.storage_context.vector_store,
                                                   service_context=self.service_context)
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
            history.append(ChatMessage(role=role,content=conv["content"]))
        return chat_engine.stream_chat(conversations[-1]["content"],chat_history=history).response_gen,[]
        

    def stream_chat_repl(self,query:str):
        from llama_index.core.memory import ChatMemoryBuffer

        memory = ChatMemoryBuffer.from_defaults(token_limit=8092)
        index = VectorStoreIndex.from_vector_store(vector_store = self.storage_context.vector_store,
                                                   service_context=self.service_context)

        chat_engine = index.as_chat_engine(
            chat_mode="condense_plus_context",
            memory=memory,            
            verbose=False,
        )
        chat_engine.streaming_chat_repl()  
    
    def search(self,query:str) -> List[SourceCode]:
        if self.args.enable_rag_search:
            target_query = query
            if isinstance(self.args.enable_rag_search,str):
                target_query = self.args.enable_rag_search
            texts,contexts = self.stream_search(target_query)
            s = "".join([text for text in texts])
            urls = ",".join(set([context["doc_url"] for context in contexts]))
            ## append RAG: prefix is used to protect avoid the source code is modified by the code auto execute
            return [SourceCode(module_name=f"RAG:{urls}", source_code=s)]
        elif self.args.enable_rag_context:
            target_query = query            
            if isinstance(self.args.enable_rag_context,str):
                target_query = self.args.enable_rag_context            
            contexts = self.retrieve(target_query) 
            for context in contexts:  
                context["raw_chunk"]
                try:
                    with open(context["doc_url"],"r") as f:
                        context["raw_chunk"] = f.read()
                except Exception as e:
                    logger.warning(f"Error reading file {context['doc_url']}")
                    pass

            return [SourceCode(module_name=context["doc_url"], source_code=context["raw_chunk"]) for context in contexts]
        return []

    def build(self):            
        retrieval_client = SimpleRetrieval(llm=self.llm,retrieval=self.retrieval)
        # retrieval_client.delete_from_doc_collection(self.namespace)
        # retrieval_client.delete_from_chunk_collection(self.chunk_collection)
        
        required_exts = self.args.required_exts or None
        documents = SimpleDirectoryReader(self.path,
                                          recursive=True,
                                          filename_as_id=True,
                                          required_exts=required_exts,
                                          file_metadata=file_metadata_func
                                          ).load_data()    
        docs_keep = []
        for document in documents:            
            doc = retrieval_client.get_doc(f"ref_doc_info/{document.doc_id}",self.namespace)                      
            if doc:
                md5 = json.loads(doc["json_data"])["metadata"].get("md5","")
                file_path = document.metadata["file_path"]
                new__md5 = document.metadata["md5"]
                if md5 != new__md5:                    
                    retrieval_client.delete_doc_and_chunks_by_filename(self.namespace,file_path)
                    docs_keep.append(document)
            else:
                docs_keep.append(document)  

        retrieval_client.commit_doc()
        retrieval_client.commit_chunk()

        for document in docs_keep:
            logger.info(f'\nUpsert {document.doc_id}')

        if docs_keep:    
            hirerachical = HierarchicalNodeParser.from_defaults(chunk_sizes=[6000,3000,1024])
            # sp = SentenceSplitter(chunk_size=1024, chunk_overlap=0)             

            nodes = hirerachical.get_nodes_from_documents(
                docs_keep, show_progress=True
            )
            
            leaf_nodes = get_leaf_nodes(nodes)     
            self.storage_context.docstore.add_documents(nodes)  

            _ = VectorStoreIndex(nodes=leaf_nodes,
                                store_nodes_override=True,
                                storage_context=self.storage_context, 
                                service_context=self.service_context) 

            retrieval_client.commit_doc()
            retrieval_client.commit_chunk() 
        else:
            logger.info("There is no new doc to build")          
        
                
        
                    