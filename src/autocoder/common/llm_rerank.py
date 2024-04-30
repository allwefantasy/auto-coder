import byzerllm
from typing import Union,List
from loguru import logger
from llama_index.core.schema import QueryBundle,NodeWithScore

class LLMRerank():
    def __init__(self,llm:byzerllm.ByzerLLM):
        self.llm = llm        

    @byzerllm.prompt(llm=lambda self: self.llm)
    def rereank(self,context_str:str, query_str:str)->str:
        '''
        以下显示了一份文档列表。每个文档旁边都有一个编号以及该文档的摘要。还提供了一个问题。
        回答问题时，请按照相关性顺序列出你应该参考的文档的编号，并给出相关性评分。相关性评分是一个1-10的数字，基于你认为该文档与问题的相关程度。
        不要包括任何与问题无关的文档。
        示例格式：
        文档1：
        <文档1的摘要>

        文档2：
        <文档2的摘要>

        ...

        文档10：
        <文档10的摘要>

        问题：<问题>
        回答：
        文档：9，相关性：7
        文档：3，相关性：4
        文档：7，相关性：3

        现在让我们试一试：

        {{ context_str }}

        问题：{{ query_str }}
        回答：
        '''

    def postprocess_nodes(self,
                          nodes:List[NodeWithScore], 
                          query_bundle:Union[str,QueryBundle],
                          choice_batch_size:int=5, top_n:int=1,verbose:bool=False)->List[NodeWithScore]:                          
        if isinstance(query_bundle, str):
            query_bundle = QueryBundle(query_str=query_bundle)

        # 给每个节点添加全局索引
        indexed_nodes = list(enumerate(nodes))

        # 按 choice_batch_size 切分 nodes
        node_batches = [indexed_nodes[i:i+choice_batch_size] for i in range(0, len(indexed_nodes), choice_batch_size)]

        # 合并排序后的结果
        sorted_nodes = []
        for batch in node_batches:
            context_str = "\n\n".join([f"文档{idx}:\n{node.node.get_text()}" for idx, node in batch])            
            rerank_output = self.rereank(context_str, query_bundle.query_str)
            if verbose:
                logger.info(self.rereank.prompt(context_str, query_bundle.query_str))
                logger.info(rerank_output)

            # 解析 rerank 的输出
            rerank_result = []
            for line in rerank_output.split("\n"):
                if line.startswith("文档："):
                    parts = line.split("，")
                    if len(parts) == 2:
                        try:
                            doc_idx = int(parts[0].split("：")[1])
                            relevance = float(parts[1].split("：")[1])
                            rerank_result.append((doc_idx, relevance))
                        except:
                            logger.warning(f"Failed to parse line: {line}")
                            pass

            # 更新 batch 中节点的分数
            for doc_idx, relevance in rerank_result:                  
                indexed_nodes[doc_idx][1].score = relevance

        sorted_nodes.extend([node for _, node in sorted(indexed_nodes, key=lambda x: x[1].score, reverse=True)])

        return sorted_nodes[:top_n]