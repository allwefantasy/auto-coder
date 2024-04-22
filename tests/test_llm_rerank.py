from autocoder.common.llm_rerank import LLMRerank
from autocoder.common import AutoCoderArgs
import tempfile
from llama_index.core.schema import NodeWithScore,TextNode
import shutil
import pytest
from .base import get_llm,MODEL,EMB_MODEL,RAY_ADDRESS,QUERY


@pytest.fixture
def llm():
    temp_dir = tempfile.mkdtemp()
    args = AutoCoderArgs(source_dir=temp_dir,
                         model=MODEL,
                         emb_model=EMB_MODEL,
                         enable_rag_search=False,enable_rag_context=True,
                         query=QUERY,
                         ray_address=RAY_ADDRESS
                         ) 
    yield get_llm(args)
    shutil.rmtree(temp_dir)

@pytest.fixture
def nodes():
    return [
        NodeWithScore(node=TextNode(text="Python is a high-level, general-purpose programming language."), score=0.5),
        NodeWithScore(node=TextNode(text="It was created by Guido van Rossum and first released in 1991."), score=0.5),
        NodeWithScore(node=TextNode(text="Python has a design philosophy that emphasizes code readability."), score=0.5),
        NodeWithScore(node=TextNode(text="It provides constructs that enable clear programming on both small and large scales."), score=0.5),
        NodeWithScore(node=TextNode(text="Python features a dynamic type system and automatic memory management."), score=0.5),
        NodeWithScore(node=TextNode(text="It supports multiple programming paradigms, including structured, object-oriented, and functional programming."), score=0.5),
        NodeWithScore(node=TextNode(text="Python is often described as a 'batteries included' language due to its comprehensive standard library."), score=0.5),
    ]

def test_postprocess_nodes_single_batch(llm, nodes):
    reranker = LLMRerank(llm)
    query = "What is Python?"

    result = reranker.postprocess_nodes(nodes, query, choice_batch_size=10, top_n=3)

    assert len(result) == 3
    assert all(isinstance(node, NodeWithScore) for node in result)
    assert result[0].score >= result[1].score >= result[2].score

def test_postprocess_nodes_multiple_batches(llm, nodes):
    reranker = LLMRerank(llm)  
    query = "What are the key features of Python?"

    result = reranker.postprocess_nodes(nodes, query, choice_batch_size=3, top_n=5)

    assert len(result) == 5
    assert all(isinstance(node, NodeWithScore) for node in result)
    assert result[0].score >= result[1].score >= result[2].score >= result[3].score >= result[4].score
