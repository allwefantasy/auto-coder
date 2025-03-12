import os
from autocoder.rag.simple_rag import SimpleRAG
from autocoder.common import AutoCoderArgs
import byzerllm
from loguru import logger
from byzerllm.apps.byzer_storage.env import get_latest_byzer_retrieval_lib

MODEL = "gpt3_5_chat"
EMB_MODEL = "gpt_emb"
RAY_ADDRESS = "auto"
QUERY = "test file"

def get_llm(args:AutoCoderArgs):

    home = os.path.expanduser("~")
    auto_coder_dir = os.path.join(home, ".auto-coder")
    libs_dir = os.path.join(auto_coder_dir, "storage", "libs")                
    code_search_path = None
    if os.path.exists(libs_dir):        
        retrieval_libs_dir = os.path.join(libs_dir,get_latest_byzer_retrieval_lib(libs_dir))            
        if os.path.exists(retrieval_libs_dir):
            code_search_path = [retrieval_libs_dir]

    try:        
        byzerllm.connect_cluster(address=args.ray_address,code_search_path=code_search_path)        
    except Exception as e:
        logger.warning(f"Detecting error when connecting to ray cluster: {e}, try to connect to ray cluster without storage support.")
        byzerllm.connect_cluster(address=args.ray_address)
    
    llm = byzerllm.ByzerLLM()
    llm.setup_default_model_name(args.model)
    llm.setup_default_emb_model_name(args.emb_model)
    llm.setup_template(model=args.model, template='auto')
        
    return llm  

  