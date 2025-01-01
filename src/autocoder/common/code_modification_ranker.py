import byzerllm
from typing import List,Union
from autocoder.common import AutoCoderArgs
from autocoder.common.types import CodeGenerateResult
from pydantic import BaseModel
from loguru import logger
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback

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
                       
        # Create a thread pool with generate_times workers
        with ThreadPoolExecutor(max_workers=generate_times) as executor:
            # Submit tasks
            futures = [
                executor.submit(
                    self._rank_modifications.with_llm(self.llm).with_return_type(RankResult).run,
                    generate_result
                ) for _ in range(generate_times)
            ]
            
            # Process results as they complete
            for future in as_completed(futures):
                try:
                    v = future.result()
                    # If we get a valid result, use it and cancel other tasks
                    for f in futures:
                        f.cancel()
                    logger.info(f"Ranking request success, rank_result={v.rank_result}")
                    rerank_contents = [generate_result.contents[i] for i in v.rank_result]
                    rerank_conversations = [generate_result.conversations[i] for i in v.rank_result]
                    return CodeGenerateResult(contents=rerank_contents,conversations=rerank_conversations)
                except Exception as e:
                    logger.warning(f"Ranking request failed: {str(e)}")
                    logger.debug(traceback.format_exc())
                    continue
        
        # If all requests failed, raise the last exception        
        logger.warning("All rerank requests failed, use the original codes")
        return generate_result
