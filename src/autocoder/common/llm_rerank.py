import byzerllm
from typing import Union,List
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

        {context_str}
        问题：{query_str}
        回答：
        '''

    def postprocess_nodes(self,nodes:List[NodeWithScore], query_bundle:Union[str,QueryBundle],choice_batch_size:int=5, top_n:int=1):
        if isinstance(query_bundle, str):
            query_bundle = QueryBundle(query_str=query_bundle)


        
        return nodes
        