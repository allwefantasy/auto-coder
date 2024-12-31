import byzerllm
from typing import List,Union
from autocoder.common import AutoCoderArgs
from autocoder.common.code_auto_merge_diff import CodeAutoMergeDiff
from autocoder.common.code_auto_merge_editblock import CodeAutoMergeEditBlock
from autocoder.common.code_auto_merge_strict_diff import CodeAutoMergeStrictDiff
from autocoder.common.code_auto_merge import CodeAutoMerge
from autocoder.common.types import CodeGenerateResult
from pydantic import BaseModel

class RankResult(BaseModel):
    rank_result:List[int]

class CodeModificationRanker:
    def __init__(self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs, merger:Union[CodeAutoMergeDiff,CodeAutoMergeEditBlock,CodeAutoMergeStrictDiff,CodeAutoMerge]):
        self.llm = llm
        self.args = args
        self.merger = merger        
    
    @byzerllm.prompt()
    def _rank_modifications(self, s:CodeGenerateResult) -> str:
        '''
        对一组代码修改进行质量评估，并返回索引排序，最好的修改排在最前面。

        下面是修改需求：
        
        <edit_requirement>
        {{ s.conversations[0][-2]["content"] }}
        </edit_requirement>
        
        下面是相应的代码修改：
        {% for idx, content in enumerate(s.contents) %}
        <edit_block id="{{ idx }}">
        {{content}}
        </edit_block>
        {% endfor %}
        
        返回格式如下JSON数组
        
        ```json
        [id3, id2, id1]
        ```

        包含修改质量的排序序号，最好的修改排在最前面
        '''
        

    def rank_modifications(self, generate_result: CodeGenerateResult) -> CodeGenerateResult:
        v =  self._rank_modifications.with_llm(self.llm).with_return_type(RankResult).run(generate_result)
        rerank_contents = [generate_result.contents[i] for i in v.rank_result]
        rerank_conversations = [generate_result.conversations[i] for i in v.rank_result]
        return CodeGenerateResult(contents=rerank_contents,conversations=rerank_conversations)
