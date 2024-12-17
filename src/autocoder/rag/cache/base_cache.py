from pydantic import BaseModel
from typing import List, Tuple,Dict,Optional,Any
from abc import ABC, abstractmethod

class DeleteEvent(BaseModel):
    file_paths: List[str]

class AddOrUpdateEvent(BaseModel):
    file_infos: List[Tuple[str, str, float, str]]

class BaseCacheManager(ABC):
    @abstractmethod
    def get_cache(self,options:Optional[Dict[str,Any]]=None) -> Dict[str, Dict]:
        pass
