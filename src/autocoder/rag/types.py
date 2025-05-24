import os
import json
import time
import pydantic
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
import psutil
import glob

class RecallStat(BaseModel):
    total_input_tokens: int
    total_generated_tokens: int
    model_name: str = "unknown"
    cost:float = 0.0
    duration: float = 0.0


class ChunkStat(BaseModel):
    total_input_tokens: int
    total_generated_tokens: int
    model_name: str = "unknown"
    cost:float = 0.0
    duration: float = 0.0


class AnswerStat(BaseModel):
    total_input_tokens: int
    total_generated_tokens: int
    model_name: str = "unknown"
    cost:float = 0.0
    duration: float = 0.0


class OtherStat(BaseModel):
    total_input_tokens: int = 0
    total_generated_tokens: int = 0
    model_name: str = "unknown"
    cost:float = 0.0
    duration: float = 0.0


class RAGStat(BaseModel):
    recall_stat: RecallStat
    chunk_stat: ChunkStat
    answer_stat: AnswerStat
    other_stats: List[OtherStat] = []
    cost:float = 0.0

class RAGServiceInfo(pydantic.BaseModel):
    host: str
    port: int
    model: str
    args: Dict[str, Any]
    _pid: int 
    _timestamp:str

    def save(self):
        # Get home directory in a cross-platform way
        home_dir = os.path.expanduser("~")
        rag_dir = os.path.join(home_dir, ".auto-coder", "rags")
        os.makedirs(rag_dir, exist_ok=True)
        
        # Generate filename
        filename = f"{self.host}_{self.port}.json"
        filepath = os.path.join(rag_dir, filename)
        
        # Save to JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.model_dump(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, host: str, port: int) -> Optional["RAGServiceInfo"]:
        """Load RAGServiceInfo from file"""
        home_dir = os.path.expanduser("~")
        rag_dir = os.path.join(home_dir, ".auto-coder", "rags")
        filename = f"{host}_{port}.json"
        filepath = os.path.join(rag_dir, filename)
        
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
            return cls(**data)

    def is_alive(self) -> bool:
        """Check if the RAG service process is still running using psutil"""        
        try:
            process = psutil.Process(self._pid)
            return process.is_running()
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            # Process exists but we don't have permission to access it
            return True

    @classmethod
    def load_all(cls) -> List["RAGServiceInfo"]:
        """Load all RAGServiceInfo from ~/.auto-coder/rags directory"""
        home_dir = os.path.expanduser("~")
        rag_dir = os.path.join(home_dir, ".auto-coder", "rags")
        
        if not os.path.exists(rag_dir):
            return []
            
        service_infos = []
        for filepath in glob.glob(os.path.join(rag_dir, "*.json")):
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    service_info = cls(**data)
                    service_infos.append(service_info)
            except Exception as e:
                continue
                
        return service_infos