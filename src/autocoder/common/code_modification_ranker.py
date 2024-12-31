import byzerllm
from typing import List
from autocoder.common import AutoCoderArgs
from autocoder.common.code_auto_merge_diff import CodeAutoMergeDiff
from autocoder.common.code_auto_merge_editblock import CodeAutoMergeEditBlock
from autocoder.common.code_auto_merge_strict_diff import CodeAutoMergeStrictDiff
from autocoder.common.code_auto_merge import CodeAutoMerge

class CodeModificationRanker:
    def __init__(self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs):
        self.llm = llm
        self.args = args
        self.merge_diff = CodeAutoMergeDiff(llm, args)
        self.merge_editblock = CodeAutoMergeEditBlock(llm, args)
        self.merge_strict_diff = CodeAutoMergeStrictDiff(llm, args)
        self.merge_code = CodeAutoMerge(llm, args)

    @byzerllm.prompt()
    def rank_modifications(self, modifications: List[str]) -> List[int]:
        '''
        对一组代码修改进行质量评估，并返回索引排序，最好的修改排在最前面。
        
        评估标准：
        1. 修改的完整性：是否完整地实现了需求
        2. 代码质量：代码的可读性、可维护性
        3. 兼容性：是否与现有代码库兼容
        4. 性能影响：是否对性能有负面影响
        
        返回一个索引列表，表示修改质量的排序，最好的修改排在最前面。
        
        示例：
        输入：["修改1", "修改2", "修改3"]
        输出：[2, 0, 1]  # 表示修改3最好，修改1次之，修改2最差
        '''
        
        # 首先对每个修改进行解析和验证
        valid_indices = []
        for idx, mod in enumerate(modifications):
            try:
                # 尝试用不同的解析器解析修改
                if "```diff" in mod:
                    self.merge_diff.get_edits(mod)
                elif "<<<<<<< SEARCH" in mod:
                    self.merge_editblock.get_edits(mod)
                elif "##File:" in mod:
                    self.merge_code.parse_whole_text_v2(mod)
                else:
                    self.merge_strict_diff.parse_diff_block(mod)
                valid_indices.append(idx)
            except Exception as e:
                # 如果解析失败，则跳过该修改
                continue
                
        # 如果没有有效的修改，返回空列表
        if not valid_indices:
            return []
            
        # 让LLM对有效的修改进行排序
        prompt = f"""
        请对以下代码修改进行质量评估，并返回索引排序（最好的修改排在最前面）：
        
        {[modifications[i] for i in valid_indices]}
        
        评估标准：
        1. 修改的完整性：是否完整地实现了需求
        2. 代码质量：代码的可读性、可维护性
        3. 兼容性：是否与现有代码库兼容
        4. 性能影响：是否对性能有负面影响
        
        请直接返回索引列表，例如：[2, 0, 1]
        """
        
        # 获取LLM的排序结果
        result = self.llm.chat_oai([{
            "role": "user",
            "content": prompt
        }])
        
        # 解析LLM返回的索引列表
        try:
            ranked_indices = eval(result[0].output)
            if isinstance(ranked_indices, list) and all(isinstance(i, int) for i in ranked_indices):
                # 将排序结果映射回原始索引
                return [valid_indices[i] for i in ranked_indices]
        except:
            pass
            
        # 如果LLM返回的结果无法解析，则按原始顺序返回
        return valid_indices