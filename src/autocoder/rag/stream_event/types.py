from typing import List, Dict, Any
from enum import Enum
from pydantic import BaseModel

class EventType(Enum):
    START = "start"
    THOUGHT = "thought"
    CHUNK = "chunk"
    DONE = "done"
    ERROR = "error"

class Event(BaseModel):
    request_id: str
    event_type: EventType
    content: str  
    index: int