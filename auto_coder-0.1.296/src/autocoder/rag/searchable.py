import json
from collections import Counter
from typing import Dict, List, Any, Optional, Tuple, Set
from pydantic import BaseModel
from autocoder.rag.relevant_utils import FilterDoc


class FileOccurrence(BaseModel):
    """Represents a file and its occurrence count in search results"""
    file_path: str
    count: int
    score: float = 0.0  # Optional relevance score

class FileResult(BaseModel):
    files: List[FileOccurrence]

class SearchableResults:
    """Class to process and organize search results by file frequency"""
    
    def __init__(self):
        """Initialize the SearchableResults instance"""
        pass
    
    def extract_original_docs(self, docs: List[FilterDoc]) -> List[str]:
        """Extract all original_docs from a list of document metadata"""
        all_files = []
        
        for doc in docs:
            # Extract from metadata if available
            metadata = doc.source_code.metadata
            if "original_docs" in metadata:
                all_files.extend(metadata["original_docs"])
            # Also include the module_name from source_code as a fallback
            else:
                all_files.append(doc.source_code.module_name)
        
        return all_files
    
    def count_file_occurrences(self, files: List[str]) -> List[FileOccurrence]:
        """Count occurrences of each file and return sorted list"""
        # Count occurrences
        counter = Counter(files)
        
        # Convert to FileOccurrence objects
        occurrences = [
            FileOccurrence(file_path=file_path, count=count)
            for file_path, count in counter.items()
        ]
        
        # Sort by count (descending)
        return sorted(occurrences, key=lambda x: x.count, reverse=True)
    
    def reorder(self, docs: List[FilterDoc]) -> List[FileOccurrence]:
        """Process search results to extract and rank files by occurrence (main entry point)"""
        all_files = self.extract_original_docs(docs)
        return FileResult(files=self.count_file_occurrences(all_files))
    
    