import os
import json
import time
from typing import List, Dict
from pydantic import BaseModel

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

