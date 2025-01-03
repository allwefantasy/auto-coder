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
        self.llms = self.llm.get_sub_client("generate_rerank_model") or [self.llm]
        if not isinstance(self.llms, list):
            self.llms = [self.llms]
    
    @byzerllm.prompt()
    def _rank_modifications(self, s:CodeGenerateResult) -> str:
        '''
        对一组代码修改进行质量评估并排序。

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
        
        请输出如下格式的评估结果,只包含 JSON 数据:

        ```json
        {
            "rank_result": [id1, id2, id3]  // id 为 edit_block 的 id,按质量从高到低排序
        }
        ```

        注意：        
        1. 只输出前面要求的 Json 格式就好，不要输出其他内容，Json 需要使用 ```json ```包裹        
        '''
        

    def rank_modifications(self, generate_result: CodeGenerateResult) -> CodeGenerateResult:
        import time
        from collections import defaultdict

        start_time = time.time()
        
        # 如果只有一个候选，直接返回
        if len(generate_result.contents) == 1:
            logger.info("Only 1 candidate, skip ranking")
            return generate_result
            
        logger.info(f"Start ranking {len(generate_result.contents)} candidates")
        generate_times = self.args.generate_times_same_model
        total_tasks = len(self.llms) * generate_times
        try:
            # Create a thread pool with (number of models * generate_times) workers            
            with ThreadPoolExecutor(max_workers=total_tasks) as executor:
                # Submit tasks for each model and generate_times
                futures = []
                for llm in self.llms:
                    for _ in range(generate_times):
                        futures.append(
                            executor.submit(
                                self._rank_modifications.with_llm(llm).with_return_type(RankResult).run,
                                generate_result
                            )
                        )
                
                # Collect all results
                results = []
                for future in as_completed(futures):
                    try:
                        v = future.result()
                        results.append(v.rank_result)
                    except Exception as e:
                        logger.warning(f"Ranking request failed: {str(e)}")
                        logger.debug(traceback.format_exc())
                        continue
                
                if not results:
                    raise Exception("All ranking requests failed")
                
                # Calculate scores for each candidate
                candidate_scores = defaultdict(float)
                for rank_result in results:
                    for idx, candidate_id in enumerate(rank_result):
                        # Score is 1/(position + 1) since position starts from 0
                        candidate_scores[candidate_id] += 1.0 / (idx + 1)
                
                # Sort candidates by score in descending order
                sorted_candidates = sorted(candidate_scores.keys(), 
                                         key=lambda x: candidate_scores[x], 
                                         reverse=True)
                
                elapsed = time.time() - start_time
                # Format scores for logging
                score_details = ", ".join([f"candidate {i}: {candidate_scores[i]:.2f}" for i in sorted_candidates])
                logger.info(f"Ranking completed in {elapsed:.2f}s, total voters: {total_tasks}, best candidate index: {sorted_candidates[0]}, scores: {score_details}")
                
                rerank_contents = [generate_result.contents[i] for i in sorted_candidates]
                rerank_conversations = [generate_result.conversations[i] for i in sorted_candidates]
                return CodeGenerateResult(contents=rerank_contents,conversations=rerank_conversations)
                
        except Exception as e:
            logger.error(f"Ranking process failed: {str(e)}")
            logger.debug(traceback.format_exc())
            elapsed = time.time() - start_time
            logger.warning(f"Ranking failed in {elapsed:.2f}s, using original order")
            return generate_result
