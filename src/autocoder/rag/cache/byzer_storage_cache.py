from .base_cache import BaseCacheManager
from ..simple_directory_reader import AutoCoderSimpleDirectoryReader
from typing import Generator, List, Dict, Any, Optional
from autocoder.common import SourceCode
from loguru import logger
import pathspec
import os
import uuid
from byzerllm.apps.byzer_storage.simple_api import ByzerStorage, DataType, FieldOption,SortOption



class ByzerStorageCache(BaseCacheManager):
    def __init__(self, path, ignore_spec, required_exts):
        self.path = path
        self.ignore_spec = ignore_spec
        self.required_exts = required_exts
        self.storage = ByzerStorage("byzerai_store", "rag", "files")
        self.chunk_size = 1000
        self._init_schema()


    def _chunk_text(self,text, max_length=1000):
        """Split text into chunks"""
        chunks = []
        current_chunk = []
        current_length = 0
        
        for line in text.split("\n"):
            if current_length + len(line) > max_length and current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
            current_chunk.append(line)
            current_length += len(line)
            
        if current_chunk:
            chunks.append("\n".join(current_chunk))
            
        return chunks    

    def _init_schema(self):
        """Initialize the Byzer Storage schema"""
        _ = (
            self.storage.schema_builder()
            .add_field("_id", DataType.STRING)
            .add_field("file_path", DataType.STRING)
            .add_field("chunk_id", DataType.STRING)
            .add_field("content", DataType.STRING, [FieldOption.ANALYZE])            
            .add_field("raw_content", DataType.STRING, [FieldOption.NO_INDEX])  
            .add_array_field("vector", DataType.FLOAT)          
            .execute()
        )

    def _build_cache(self):
        """Build the cache by reading files and storing in Byzer Storage"""
        logger.info(f"Building cache for path: {self.path}")
        documents = AutoCoderSimpleDirectoryReader(
            self.path,
            recursive=True,
            filename_as_id=True,
            required_exts=self.required_exts,
            exclude=self.ignore_spec,
        ).load_data()

        items = []
        for doc in documents:
            chunks = self._chunk_text(doc.text, self.chunk_size)
            for chunk_idx, chunk in enumerate(chunks):
                chunk_id = str(uuid.uuid4())
                items.append({
                    "_id": f"{doc.doc_id}_{chunk_idx}",
                    "file_path": doc.metadata["file_path"],
                    "chunk_id": chunk_id,
                    "content": chunk,
                    "raw_content": chunk,
                    "vector": chunk  # Byzer Storage will automatically convert text to vector
                })

        if items:
            self.storage.write_builder().add_items(items, vector_fields=["vector"], search_fields=["content"]).execute()
            self.storage.commit()

    def get_cache(self) -> Dict[str, Dict[str, Any]]:
        """Get all cached documents"""
        results = self.storage.query_builder().execute()
        if not results:
            self._build_cache()
            results = self.storage.query_builder().execute()

        cache = {}
        for result in results:
            file_path = result["file_path"]
            if file_path not in cache:
                cache[file_path] = {"content": []}
                
            cache[file_path]["content"].append(
                SourceCode(
                    module_name=file_path,
                    source_code=result["raw_content"],
                    metadata={"chunk_id": result["chunk_id"]}
                )
            )
        return cache

    def search_cache(self, options: Dict[str, Any]) -> Generator[SourceCode, None, None]:
        """Search cached documents using query"""
        query = options.get("query", "")
        if not query:
            return None

        # Build query with both vector search and text search
        query_builder = self.storage.query_builder()
        
        # Add vector search if enabled
        if options.get("enable_vector_search", True):
            query_builder.set_vector_query(query, fields=["vector"])
            
        # Add text search
        if options.get("enable_text_search", True):
            query_builder.set_search_query(query, fields=["content"])
            
        results = query_builder.execute()

        # Group results by file_path and reconstruct documents
        grouped_results = {}
        for result in results:
            file_path = result["file_path"]
            if file_path not in grouped_results:
                grouped_results[file_path] = []
            grouped_results[file_path].append(result)

        # Yield reconstructed documents
        for file_path, chunks in grouped_results.items():
            # Sort chunks by chunk_id to maintain original order
            chunks.sort(key=lambda x: x["chunk_id"])
            combined_content = "\n".join(chunk["raw_content"] for chunk in chunks)
            
            yield SourceCode(
                module_name=file_path,
                source_code=combined_content,
                metadata={
                    "chunk_ids": [chunk["chunk_id"] for chunk in chunks]
                }
            )

    def clear_cache(self):
        """Clear all cached data"""
        self.storage.drop()