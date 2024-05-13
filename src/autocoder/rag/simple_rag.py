from typing import Any, Dict, List, Optional, Tuple
from autocoder.common import SourceCode,AutoCoderArgs
from autocoder.common.llm_rerank import LLMRerank
import fsspec

from byzerllm.apps.llama_index.simple_retrieval import SimpleRetrieval
from byzerllm.apps.llama_index import get_service_context,get_storage_context
from byzerllm.apps.llama_index.collection_manager import CollectionManager,CollectionItem
from llama_index.core import QueryBundle,StorageContext
from llama_index.core.readers.file.base import default_file_metadata_func
from llama_index.core import SimpleDirectoryReader, VectorStoreIndex, ServiceContext
from llama_index.core.node_parser import SentenceSplitter,HierarchicalNodeParser,get_leaf_nodes, get_root_nodes
from llama_index.core.base.llms.types import ChatMessage,MessageRole
from llama_index.core.retrievers import AutoMergingRetriever
from llama_index.core.query_engine import RetrieverQueryEngine,RouterQueryEngine
from llama_index.core.tools import QueryEngineTool
from llama_index.core.selectors import (
   LLMSingleSelector,   
)

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
       

       self.collections = self.args.collection
       if self.args.collections:
           self.collections = self.args.collections

       self.collections = self.collections.split(",") if self.collections else []  

       if not self.collections:
           logger.warning('''No RAG collection is set, we will use the `default` collection.
You can set the collection by passing the `--collections`argument in command line or set the `collections` attribute in the config file.''')  
           self.collections = ["default"]

       if not self.llm.default_emb_model_name:
           raise ValueError("emb_model should be set")

       self.service_context = get_service_context(self.llm)
       self.storage_context_dict:Dict[str,StorageContext] = {}
       for collection in self.collections:
            self.storage_context_dict[collection] = get_storage_context(self.llm,
                                                                        self.retrieval,
                                                                        chunk_collection=collection,
                                                                        namespace=collection)
       
       self.simple_retrieval_dict:Dict[str,SimpleRetrieval] = {}
       for collection in self.collections:
              self.simple_retrieval_dict[collection] = SimpleRetrieval(llm=llm, 
                                                                       retrieval=self.retrieval,
                                                                       chunk_collection=collection)              
       self.collection_manager = CollectionManager("")

   def _get_indices(self)->(List[Tuple[CollectionItem,VectorStoreIndex]]):
       indices = []
       for collection in self.collections:
           storage_context = self.storage_context_dict[collection]
           index = VectorStoreIndex.from_vector_store(vector_store = storage_context.vector_store,
                                               service_context=self.service_context)
           collection_item = self.collection_manager.get_collection(collection)       
           indices.append((collection_item,index))
           
       return indices    


   def _get_query_engine(self,streaming:bool=False):
       indices = self._get_indices()
       retrievers = []
       
       for (collection_item,index) in indices:
           retriever = AutoMergingRetriever(index.as_retriever(),storage_context=self.storage_context_dict[collection_item.name])
           retrievers.append(retriever)       
       
       query_engines = [
           RetrieverQueryEngine.from_args(retriever,service_context=self.service_context,streaming=streaming)
           for retriever in retrievers
       ]
       
       if len(query_engines) == 1:
           return query_engines[0]
       
       tools = []
       for (collection_item,index),query_engine in zip(indices,query_engines):           
           tool = QueryEngineTool.from_defaults(
                   query_engine=query_engine,
                   description=collection_item.description,
               )
           tools.append(tool)

       query_engine = RouterQueryEngine(
                       selector=LLMSingleSelector.from_defaults(service_context=self.service_context),
                       query_engine_tools=tools,
                       llm=self.service_context.llm,
                       service_context=self.service_context,
                       verbose=True
                   )    
       return query_engine
       

   def _get_retriever(self):
        indices = self._get_indices()
        retrievers = []

        for (collection_item,index) in indices:
            retriever = AutoMergingRetriever(index.as_retriever(),
                                             storage_context=self.storage_context_dict[collection_item.name])
            retrievers.append(retriever) 

        return retrievers                  
               

   def stream_search(self,query:str):     
       query_bundle = QueryBundle(query_str=query)   
       query_engine = self._get_query_engine(streaming=True)
       streaming_response = query_engine.query(query_bundle)
       contexts = []
       for node in streaming_response.source_nodes:
           contexts.append({
               "raw_chunk":node.node.text,
               "doc_url":node.node.metadata["file_path"],
               "_id":node.node.id_,
               
           })
       return streaming_response.response_gen,contexts 
   
   def retrieve(self,query:str)->List[Dict[str,Any]]:
        query_bundle = QueryBundle(query_str=query)
        retrievers = self._get_retriever()

        result = []

        for retriever in retrievers:
            nodes = retriever.retrieve(query_bundle) 

            reranker = LLMRerank(llm=self.llm)
            retrieved_nodes = reranker.postprocess_nodes(nodes, query_bundle,choice_batch_size=5, top_n=1)
            result.extend([
                {
                    "raw_chunk":node.node.text,
                    "doc_url":node.node.metadata["file_path"],
                    "_id":node.node.id_,
                    
                } for node in retrieved_nodes
            ]) 
        return result    
   
   def stream_chat_oai(self,conversations, model:Optional[str]=None, role_mapping=None,llm_config:Dict[str,Any]={}):        
        if len(self.collections) != 1:
            raise ValueError("When chat mode, only one collection can be set")
        
        index = VectorStoreIndex.from_vector_store(vector_store = self.storage_context_dict[self.collections[0]].vector_store,
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
       if len(self.collections) != 1:
           raise ValueError("When chat mode, only one collection can be set")
       from llama_index.core.memory import ChatMemoryBuffer
       memory = ChatMemoryBuffer.from_defaults(token_limit=8092)
       index = VectorStoreIndex.from_vector_store(vector_store = self.storage_context_dict[self.collections[0]].vector_store,
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
        
        if len(self.collections) != 1:
            raise ValueError("When build, only one collection should be set")
            
        collection = self.collections[0]

        collection_exists = self.collection_manager.check_collection_exists(collection)
        if not collection_exists:
            logger.warning(f"Collection {collection} not found, creating it automatically")
            if not self.args.description:
                logger.error("Please provide a description for the collection")
                return
            item = CollectionItem(
                name=collection,
                description=self.args.description or ""
            )
            self.collection_manager.add_collection(item)

        retrieval_client = self.simple_retrieval_dict[collection]
        # retrieval_client.delete_from_doc_collection(collection)
        # retrieval_client.delete_from_chunk_collection(collection)
        
        required_exts = self.args.required_exts or None
        documents = SimpleDirectoryReader(self.path,
                                            recursive=True,
                                            filename_as_id=True,
                                            required_exts=required_exts,
                                            file_metadata=file_metadata_func
                                            ).load_data()    
        docs_keep = []
        for document in documents:            
            doc = retrieval_client.get_doc(f"ref_doc_info/{document.doc_id}",collection)                      
            if doc:
                md5 = json.loads(doc["json_data"])["metadata"].get("md5","")
                file_path = document.metadata["file_path"]
                new__md5 = document.metadata["md5"]
                if md5 != new__md5:                    
                    retrieval_client.delete_doc_and_chunks_by_filename(collection,file_path)
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
            self.storage_context_dict[collection].docstore.add_documents(nodes)  

            _ = VectorStoreIndex(nodes=leaf_nodes,
                                store_nodes_override=True,
                                storage_context=self.storage_context_dict[collection], 
                                service_context=self.service_context) 

            retrieval_client.commit_doc()
            retrieval_client.commit_chunk() 
        else:
            logger.info("There is no new doc to build")   
                