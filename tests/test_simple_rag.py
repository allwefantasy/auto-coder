import tempfile
import shutil
from autocoder.rag.simple_rag import SimpleRAG
from autocoder.common import AutoCoderArgs
import pytest
from loguru import logger
from .base import get_llm,MODEL,EMB_MODEL,RAY_ADDRESS,QUERY

@pytest.fixture
def rag():
    temp_dir = tempfile.mkdtemp()
    args = AutoCoderArgs(source_dir=temp_dir,
                         model=MODEL,
                         emb_model=EMB_MODEL,
                         enable_rag_search=False,enable_rag_context=True,
                         query=QUERY,
                         ray_address=RAY_ADDRESS
                         ) 
    llm = get_llm(args)              
    rag = SimpleRAG(llm, args, temp_dir)
    yield rag
    shutil.rmtree(temp_dir)
    
def test_retrieve(rag):
    results = rag.retrieve('启动kimi_chat')  
    print(results)