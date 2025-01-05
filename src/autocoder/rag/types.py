
import os
import json
import time
import pydantic
from typing import Dict, Any
from datetime import datetime

class RAGServiceInfo(pydantic.BaseModel):
    host: str
    port: int
    model: str
    args: Dict[str, Any]
    _pid: int = pydantic.Field(default_factory=lambda: os.getpid())
    _timestamp: str = pydantic.Field(default_factory=lambda: datetime.now().isoformat())

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
            json.dump(self.dict(), f, ensure_ascii=False, indent=2)