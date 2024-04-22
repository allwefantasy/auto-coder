from autocoder.common.llm_rerank import LLMRerank
from llama_index.core.schema import NodeWithScore
import byzerllm
import pytest

@pytest.fixture
def llm():
    return byzerllm.ByzerLLM(max_tokens=512)

@pytest.fixture
def nodes():
    return [
        NodeWithScore(node="Node 1 content"),
        NodeWithScore(node="Node 2 content"),
        NodeWithScore(node="Node 3 content"),
        NodeWithScore(node="Node 4 content"),
        NodeWithScore(node="Node 5 content"),
        NodeWithScore(node="Node 6 content"),
        NodeWithScore(node="Node 7 content"),
    ]

def test_postprocess_nodes_single_batch(llm, nodes):
    reranker = LLMRerank(llm)
    query = "Test query"

    result = reranker.postprocess_nodes(nodes, query, choice_batch_size=10, top_n=3)

    assert len(result) == 3
    assert all(isinstance(node, NodeWithScore) for node in result)
    assert result[0].score >= result[1].score >= result[2].score

def test_postprocess_nodes_multiple_batches(llm, nodes):
    reranker = LLMRerank(llm)  
    query = "Test query"

    result = reranker.postprocess_nodes(nodes, query, choice_batch_size=3, top_n=5)

    assert len(result) == 5
    assert all(isinstance(node, NodeWithScore) for node in result)
    assert result[0].score >= result[1].score >= result[2].score >= result[3].score >= result[4].score

def test_postprocess_nodes_top_n_greater_than_nodes(llm, nodes):
    reranker = LLMRerank(llm)
    query = "Test query" 

    result = reranker.postprocess_nodes(nodes, query, choice_batch_size=3, top_n=10)

    assert len(result) == len(nodes)
    assert all(isinstance(node, NodeWithScore) for node in result)
    assert result[0].score >= result[1].score >= result[2].score >= result[3].score >= result[4].score >= result[5].score >= result[6].score