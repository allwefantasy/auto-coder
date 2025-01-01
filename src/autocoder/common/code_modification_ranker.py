import byzerllm
from typing import List,Union
from autocoder.common import AutoCoderArgs
from autocoder.common.types import CodeGenerateResult
from pydantic import BaseModel
from loguru import logger

class RankResult(BaseModel):
    rank_result:List[int]

class CodeModificationRanker:
    def __init__(self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs):
        self.llm = llm
        self.args = args        
    
    @byzerllm.prompt()
    def _rank_modifications(self, s:CodeGenerateResult) -> str:
        '''
        对一组代码修改进行质量评估，并返回索引排序，最好的修改排在最前面。

        下面是修改需求：
        
        <edit_requirement>
        {{ s.conversations[0][-2]["content"] }}
        </edit_requirement>
        
        下面是相应的代码修改：
        {% for content in s.contents %}
        <edit_block id="{{ loop.index0 }}">
        {{content}}
        </edit_block>
        {% endfor %}
        
        返回格式如下JSON格式数据：
        
        ```json
        {
            "rank_result": [id3, id2, id1]
        }
        ```

        其中rank_result包含修改质量的排序序号，最好的修改排在最前面。
        '''
        

    def rank_modifications(self, generate_result: CodeGenerateResult) -> CodeGenerateResult:
        logger.info(f"Rank candidates={len(generate_result.contents)}")
        generate_times = self.args.generate_times_same_model                
        v =  self._rank_modifications.with_llm(self.llm).with_return_type(RankResult).run(generate_result)
        rerank_contents = [generate_result.contents[i] for i in v.rank_result]
        rerank_conversations = [generate_result.conversations[i] for i in v.rank_result]
        return CodeGenerateResult(contents=rerank_contents,conversations=rerank_conversations)

from typing import Optional, List
from concurrent.futures import ThreadPoolExecutor, as_completed
import byzerllm
from autocoder.common.types import RankResult, GenerateResult

class CodeModificationRanker:
    def __init__(self, llm: Optional[byzerllm.ByzerLLM] = None):
        self.llm = llm
        self._rank_modifications = None  # This should be initialized with the actual ranking logic

    def rank_modifications(self, generate_result: GenerateResult) -> RankResult:
        if not self.llm or not self._rank_modifications:
            raise ValueError("LLM and ranking logic must be initialized")

        generate_times = getattr(generate_result, "generate_times", 1)
        if generate_times <= 1:
            return self._rank_modifications.with_llm(self.llm).with_return_type(RankResult).run(generate_result)

        def run_ranking():
            try:
                return self._rank_modifications.with_llm(self.llm).with_return_type(RankResult).run(generate_result)
            except Exception as e:
                return e

        with ThreadPoolExecutor(max_workers=generate_times) as executor:
            futures = [executor.submit(run_ranking) for _ in range(generate_times)]
            
            for future in as_completed(futures):
                result = future.result()
                if not isinstance(result, Exception):
                    return result

        raise Exception("All ranking attempts failed")