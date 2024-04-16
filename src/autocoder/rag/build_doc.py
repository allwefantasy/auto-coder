from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union
from ray.util.client.common import ClientActorHandle, ClientObjectRef

from byzerllm.apps.llama_index.simple_retrieval import SimpleRetrieval
from byzerllm.apps.llama_index import get_service_context,get_storage_context
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, ServiceContext
from llama_index.core.node_parser import SentenceSplitter,SentenceWindowNodeParser
from llama_index.core.indices.document_summary import DocumentSummaryIndex
import byzerllm

class SimpleRAG:
    def __init__(self,llm,path:str) -> None:
        self.llm = llm
        self.retrieval = byzerllm.ByzerRetrieval()
        self.retrieval.launch_gateway()        
        self.path = path
        self.namespace = "default"
        self.chunk_collection = "default"
        self.service_context = get_service_context(self.llm)
        self.storage_context = get_storage_context(self.llm,self.retrieval,chunk_collection="default",namespace="default")

    def search(self,query:str):        
        index = VectorStoreIndex.from_vector_store(vector_store = self.storage_context.vector_store,service_context=self.service_context)
        query_engine = index.as_query_engine(streaming=True)                
        streaming_response = query_engine.query(query)
        contexts = []
        for node in streaming_response.source_nodes:
            contexts.append({
                "raw_chunk":node.node.text,
                "doc_url":node.node.metadata["file_path"],
                "_id":node.node.id_,
                
            })
        return streaming_response.response_gen,contexts   

    def build(self):            
        retrieval_client = SimpleRetrieval(llm=self.llm,retrieval=self.retrieval)
        retrieval_client.delete_from_doc_collection(self.namespace)
        retrieval_client.delete_from_chunk_collection(self.chunk_collection)

        documents = SimpleDirectoryReader(self.path).load_data()        

        sp = SentenceSplitter(chunk_size=1024, chunk_overlap=0)        

        nodes = sp.get_nodes_from_documents(
            documents, show_progress=True
        )
        _ = VectorStoreIndex(nodes=nodes,
                             store_nodes_override=False,
                             storage_context=self.storage_context, 
                             service_context=self.service_context)        
        
                
        
                    