import os
import json
import time
from typing import List, Dict, Optional, Any
from pydantic import BaseModel
from datetime import datetime

class MemoryItem(BaseModel):
    content: Any
    role: str

class MemoryEntry(BaseModel):
    timestamp: datetime
    conversation: List[MemoryItem]


def save_to_memory_file(ask_conversation,query:str,response:str):
    # Save to memory file                
    memory_dir = os.path.join(os.path.expanduser("~"), ".auto-coder", "memory")
    os.makedirs(memory_dir, exist_ok=True)
    memory_file = os.path.join(memory_dir, "memory.json")
    
    # Read existing memory or create new
    if os.path.exists(memory_file):
        with open(memory_file, 'r') as f:
            try:
                memory_data = json.load(f)
            except json.JSONDecodeError:
                memory_data = {}
    else:
        memory_data = {}
    
    # Add new conversation
    current_time = str(int(time.time()))
    memory_data[current_time] = [
        {"content": ask_conversation, "role": "background"},
        {"content": query, "role": "user"},
        {"content": response, "role": "assistant"}
    ]
    
    # Save memory
    with open(memory_file, 'w') as f:
        json.dump(memory_data, f, ensure_ascii=False, indent=2) 

    get_global_memory_file_paths()          
    tmp_dir = os.path.join(memory_dir, ".tmp")
    return tmp_dir

def load_from_memory_file() -> List[MemoryEntry]:
    """Load memory data from file and return as list of MemoryEntry objects"""
    memory_dir = os.path.join(os.path.expanduser("~"), ".auto-coder", "memory")
    memory_file = os.path.join(memory_dir, "memory.json")
    
    if not os.path.exists(memory_file):
        return []
    
    with open(memory_file, 'r') as f:
        try:
            memory_data = json.load(f)
        except json.JSONDecodeError:
            return []
    
    entries = []
    for timestamp_str, conversation in memory_data.items():
        try:
            timestamp = datetime.fromtimestamp(int(timestamp_str))
            memory_items = [MemoryItem(**item) for item in conversation]
            entries.append(MemoryEntry(
                timestamp=timestamp,
                conversation=memory_items
            ))
        except (ValueError, TypeError):
            continue
            
    # Sort entries by timestamp (oldest first)
    entries.sort(key=lambda x: x.timestamp)
    
    return entries

def get_global_memory_file_paths() -> List[str]:
    """Get global memory and generate temporary files in ~/.auto-coder/memory/.tmp
    
    Returns:
        List[str]: List of file paths for the generated temporary files
    """
    entries = load_from_memory_file()
    memory_dir = os.path.join(os.path.expanduser("~"), ".auto-coder", "memory")
    tmp_dir = os.path.join(memory_dir, ".tmp")
    os.makedirs(tmp_dir, exist_ok=True)
    
    file_paths = []
    
    for entry in entries:
        # Find assistant responses
        assistant_contents = [
            item.content for item in entry.conversation 
            if item.role == "assistant"
        ]
        
        if assistant_contents:
            timestamp_str = str(int(entry.timestamp.timestamp()))
            content = "\n".join(assistant_contents)
            file_path = os.path.join(tmp_dir, os.path.join("memory",f"{timestamp_str}.txt"))
            
            # Create parent directory if it doesn't exist
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            # Only write file if it doesn't exist
            if not os.path.exists(file_path):
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)
            
            file_paths.append(file_path)
    
    return file_paths

