import os
import json
import pkg_resources
from autocoder.common import AutoCoderArgs

## 用于auto-coder 内部使用

def load_tokenizer():
    from autocoder.rag.variable_holder import VariableHolder
    from tokenizers import Tokenizer    
    try:
        tokenizer_path = pkg_resources.resource_filename(
            "autocoder", "data/tokenizer.json"
        )
        VariableHolder.TOKENIZER_PATH = tokenizer_path
        VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(tokenizer_path)
    except FileNotFoundError:
        tokenizer_path = None


def save_memory(args: AutoCoderArgs,memory):    
    with open(os.path.join(args.source_dir, ".auto-coder", "plugins", "chat-auto-coder", "memory.json"), "w",encoding="utf-8") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)    

def load_memory(args: AutoCoderArgs):        
    memory_path = os.path.join(args.source_dir, ".auto-coder", "plugins", "chat-auto-coder", "memory.json")
    if os.path.exists(memory_path):
        with open(memory_path, "r", encoding="utf-8") as f:
            _memory = json.load(f)
        memory = _memory
    else:
        memory = {}        
    return memory

def get_memory(args: AutoCoderArgs):    
    return load_memory(args)    