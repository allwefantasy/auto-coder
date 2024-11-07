import os
from autocoder.rag.stream_event.types import Event

def write_event(event: Event,base_path: str="events"):
    os.makedirs(base_path, exist_ok=True)
    with open(f"{base_path}/{event.request_id}.jsonl", "a") as f:
        f.write(event.model_dump_json() + "\n")

def get_event_file_path(request_id: str,base_path: str="events") -> str:    
    return f"{base_path}/{request_id}.jsonl"
        
    