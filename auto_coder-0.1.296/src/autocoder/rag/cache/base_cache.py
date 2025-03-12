from pydantic import BaseModel
from typing import List, Tuple,Dict,Optional,Any
from abc import ABC, abstractmethod

# New model class for file information
class FileInfo(BaseModel):
    file_path: str
    relative_path: str
    modify_time: float
    file_md5: str

# New model class for cache items
class CacheItem(BaseModel):
    file_path: str
    relative_path: str
    content: List[Dict[str, Any]]  # Serialized SourceCode objects
    modify_time: float
    md5: str

class DeleteEvent(BaseModel):
    file_paths: List[str]

class AddOrUpdateEvent(BaseModel):
    file_infos: List[FileInfo]

class BaseCacheManager(ABC):
    @abstractmethod
    def get_cache(self,options:Optional[Dict[str,Any]]=None) -> Dict[str, Dict]:
        pass
