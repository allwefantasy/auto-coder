
import os
import json
import time
import pydantic
from typing import Dict, Any, Optional
from datetime import datetime

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
        import psutil
        try:
            process = psutil.Process(self._pid)
            return process.is_running()
        except psutil.NoSuchProcess:
            return False
        except psutil.AccessDenied:
            # Process exists but we don't have permission to access it
            return True