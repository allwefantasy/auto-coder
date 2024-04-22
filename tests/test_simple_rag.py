import os
os.environ["JAVA_HOME"] = "/Users/allwefantasy/Library/Java/JavaVirtualMachines/openjdk-21/Contents/Home"

import tempfile
import shutil
from autocoder.rag.simple_rag import SimpleRAG
from autocoder.common import AutoCoderArgs
import byzerllm
import pytest
from loguru import logger
from byzerllm.apps.command import get_latest_byzer_retrieval_lib



@pytest.fixture
def rag():
    temp_dir = tempfile.mkdtemp()
    
    # Create some test files
    with open(os.path.join(temp_dir, 'file1.txt'), 'w') as f:
        f.write('This is a test file.')
    with open(os.path.join(temp_dir, 'file2.txt'), 'w') as f:  
        f.write('Another test file.')
    
    args = AutoCoderArgs(source_dir=temp_dir,
                         model="gpt3_5_chat",
                         emb_model="gpt_emb",
                         enable_rag_search=False,enable_rag_context=True,
                         query="test file",
                         ray_address="auto"
                         )  
    
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
    llm.setup_template(model='haiku_chat', template='auto')
    llm.setup_default_emb_model_name('gpt_emb')
    llm.setup_default_model_name("haiku_chat")
              
    rag = SimpleRAG(llm, args, temp_dir)
    yield rag
    shutil.rmtree(temp_dir)
    
def test_retrieve(rag):
    results = rag.retrieve('启动kimi_chat')  
    print(results)