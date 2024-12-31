import byzerllm
from typing import List,Union
from autocoder.common import AutoCoderArgs
from autocoder.common.code_auto_merge_diff import CodeAutoMergeDiff
from autocoder.common.code_auto_merge_editblock import CodeAutoMergeEditBlock
from autocoder.common.code_auto_merge_strict_diff import CodeAutoMergeStrictDiff
from autocoder.common.code_auto_merge import CodeAutoMerge
from autocoder.common.types import CodeGenerateResult

class CodeModificationRanker:
    def __init__(self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs, merger:Union[CodeAutoMergeDiff,CodeAutoMergeEditBlock,CodeAutoMergeStrictDiff,CodeAutoMerge]):
        self.llm = llm
        self.args = args
        self.merger = merger        
    
    @byzerllm.prompt()
    def _rank_modifications(self, s:CodeGenerateResult) -> List[int]:
        '''
        对一组代码修改进行质量评估，并返回索引排序，最好的修改排在最前面。

        下面是修改需求：
        
        <edit_requirement>
        {{ s.conversations[0][-2]["content"] }}
        </edit_requirement>
        
        下面是相应的代码修改：
        {% for content in s.contents %}
        <edit_block>
        {{content}}
        </edit_block>
        {% endfor %}
        
        返回一个索引列表，表示修改质量的排序，最好的修改排在最前面。
        
        示例：
        输入：["修改1", "修改2", "修改3"]
        输出：[2, 0, 1]  # 表示修改3最好，修改1次之，修改2最差
        '''
        

    def rank_modifications(self, generate_result: CodeGenerateResult) -> List[int]:
        return self._rank_modifications.with_llm(self.llm).run(generate_result)