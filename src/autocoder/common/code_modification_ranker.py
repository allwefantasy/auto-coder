import byzerllm
from typing import List, Union
from autocoder.common import AutoCoderArgs
from autocoder.common.types import CodeGenerateResult
from pydantic import BaseModel
from autocoder.common.printer import Printer
from concurrent.futures import ThreadPoolExecutor, as_completed
import traceback
from autocoder.common.utils_code_auto_generate import chat_with_continue,stream_chat_with_continue
from byzerllm.utils.str2model import to_model
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.utils.llms import get_llm_names, get_model_info
from autocoder.common.types import CodeGenerateResult, MergeCodeWithoutEffect
import os
from autocoder.rag.token_counter import count_tokens
from autocoder.common.stream_out_type import CodeRankStreamOutType

class RankResult(BaseModel):
    rank_result: List[int]


class CodeModificationRanker:
    def __init__(self, llm: byzerllm.ByzerLLM, args: AutoCoderArgs):
        self.llm = llm
        self.args = args
        self.llms = self.llm.get_sub_client("generate_rerank_model") or [self.llm]
        
        if not isinstance(self.llms, list):
            self.llms = [self.llms]
        
        self.printer = Printer()

    @byzerllm.prompt()
    def _rank_modifications(self, s: CodeGenerateResult) -> str:
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
            "rank_result": [id1, id2, id3] 
        }
        ```

        注意：                   
        1. id 为 edit_block 的 id,按质量从高到低排序，并且 id 必须是数字        
        2. 只输出前面要求的 Json 格式就好，不要输出其他内容，Json 需要使用 ```json ```包裹                
        '''

    @byzerllm.prompt()
    def _rank_modifications_with_merge_result(self, s: CodeGenerateResult,merge_results: List[MergeCodeWithoutEffect]) -> str:
        '''
        对一组代码修改进行质量评估并排序。

        下面是修改需求：

        <edit_requirement>
        {{ s.conversations[0][-2]["content"] }}
        </edit_requirement>

        下面是相应的代码修改，如果Before 为空，那么表示是新增文件，如果After 为空，那么表示是删除文件，如果Before 和 After 都不为空，那么表示是修改文件：        
        {% for change in changes %}
        <edit_file id="{{ loop.index0 }}">
        {{change}}
        </edit_file>
        {% endfor %}
        
        请输出如下格式的评估结果,只包含 JSON 数据:

        ```json
        {
            "rank_result": [id1, id2, id3] 
        }
        ```

        注意：     
        1. 像python的缩进，前端诸如 reacjs,vue 的标签闭合匹配，这些很重要，需要在排序中作为重点考虑对象之一。   
        1. id 为 edit_file 的 id,按质量从高到低排序，并且 id 必须是数字        
        2. 只输出前面要求的 Json 格式就好，不要输出其他内容，Json 需要使用 ```json ```包裹                
        '''
        changes = []
        for merge_result in merge_results:
            s = ""
            for block in merge_result.success_blocks:
                file_path,content = block
                s += f"##File: {file_path}\n\n"
                if not os.path.exists(file_path):                    
                    s += f"##Before: \n\n"
                    s += f"##File: {file_path}\n\n"
                    s += f"##After: \n\n"
                    s += content
                else:
                    with open(file_path, "r",encoding="utf-8") as f:
                        original_content = f.read()
                    s += f"##Before: \n\n"
                    s += original_content
                    s += f"##File: {file_path}\n\n"
                    s += f"##After: \n\n"
                    s += content 
            changes.append(s)                       
        return {
            "changes": changes
        }    

    def rank_modifications(self, generate_result: CodeGenerateResult, merge_result: List[MergeCodeWithoutEffect]) -> CodeGenerateResult:
        import time
        from collections import defaultdict

        start_time = time.time()

        # 如果只有一个候选，直接返回
        if len(generate_result.contents) == 1:
            self.printer.print_in_terminal("ranking_skip", style="blue")
            return generate_result
        
        rank_times = self.args.rank_times_same_model
        total_tasks = len(self.llms) * rank_times
        if self.args.rank_strategy == "block":
            query = self._rank_modifications.prompt(generate_result)
        elif self.args.rank_strategy == "file":
            query = self._rank_modifications_with_merge_result.prompt(generate_result, merge_result)            
        else:
            raise Exception(f"Invalid rank strategy: {self.args.rank_strategy}")

        # 计算 query 的 token 数量                
        token_count = count_tokens(query)
        
        # 打印 token 统计信息
        self.printer.print_in_terminal(
            "estimated_input_tokens_in_ranking",            
            estimated_input_tokens=token_count
        )

        input_tokens_count = 0
        generated_tokens_count = 0
        try:
            import traceback
            traceback.print_stack()
            # Create a thread pool with (number of models * generate_times) workers
            with ThreadPoolExecutor(max_workers=total_tasks) as executor:
                # Submit tasks for each model and generate_times
                futures = []
                count = 0
                for llm in self.llms:                                                          
                    model_name = ",".join(get_llm_names(llm))
                    self.printer.print_in_terminal(
                        "ranking_start", style="blue", count=len(generate_result.contents), model_name=model_name)
                    
                    for _ in range(rank_times):
                        if count == 0:
                            futures.append(
                                executor.submit(
                                    stream_chat_with_continue,
                                    llm,
                                    [{"role": "user", "content": query}],
                                    {},
                                    self.args
                                )
                            )
                        else:    
                            futures.append(
                                executor.submit(
                                    chat_with_continue,
                                    llm,
                                    [{"role": "user", "content": query}],
                                    {},
                                    self.args
                                )
                            )
                        count += 1

                # Collect all results
                results = []
                # 获取模型名称列表
                model_names = []
                for llm in self.llms:
                    # 获取当前llm实例对应的模型名称
                    names = get_llm_names(llm)  
                    model_names.extend(names)

                # 获取模型价格信息
                model_info_map = {}
                for name in model_names:
                    # 第二个参数是产品模式,从args中获取
                    info = get_model_info(name, self.args.product_mode)  
                    if info:
                        model_info_map[name] = {
                            "input_cost": info.get("input_price", 0.0),  # 每百万tokens成本
                            "output_cost": info.get("output_price", 0.0) # 每百万tokens成本 
                        }

                # 计算总成本
                total_input_cost = 0.0
                total_output_cost = 0.0

                # 第一个future使用流式输出
                stream_future = futures[0]
                model_name = model_names[0]
                stream_generator = stream_future.result()
                full_response, last_meta = stream_out(
                        stream_generator,
                        model_name=model_name,
                        title=self.printer.get_message_from_key_with_format(
                            "rank_code_modification_title", model_name=model_name),
                        args=self.args,
                        extra_meta={
                            "stream_out_type": CodeRankStreamOutType.CODE_RANK.value
                        }
                    )
                
                if last_meta:
                    input_tokens_count += last_meta.input_tokens_count
                    generated_tokens_count += last_meta.generated_tokens_count
                    # 计算成本                        
                    info = model_info_map.get(model_name, {})
                    # 计算公式:token数 * 单价 / 1000000
                    total_input_cost += (last_meta.input_tokens_count * info.get("input_cost", 0.0)) / 1000000
                    total_output_cost += (last_meta.generated_tokens_count * info.get("output_cost", 0.0)) / 1000000
                
                v = to_model(full_response,RankResult)                        
                results.append(v.rank_result)

                for future, model_name in zip(futures[1:], model_names[1:]):
                    try:
                        result = future.result()
                        input_tokens_count += result.input_tokens_count
                        generated_tokens_count += result.generated_tokens_count
                        v = to_model(result.content,RankResult)                        
                        results.append(v.rank_result)

                        # 计算成本                        
                        info = model_info_map.get(model_name, {})
                        # 计算公式:token数 * 单价 / 1000000
                        total_input_cost += (result.input_tokens_count * info.get("input_cost", 0.0)) / 1000000
                        total_output_cost += (result.generated_tokens_count * info.get("output_cost", 0.0)) / 1000000

                    except Exception as e:
                        self.printer.print_in_terminal(
                            "ranking_failed_request", style="yellow", error=str(e))                        
                        continue

                if not results:
                    raise Exception(
                        self.printer.get_message_from_key("ranking_all_failed"))

                # 四舍五入到4位小数
                total_input_cost = round(total_input_cost, 4)
                total_output_cost = round(total_output_cost, 4)

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
                speed = generated_tokens_count / elapsed
                # Format scores for logging
                score_details = ", ".join(
                    [f"candidate {i}: {candidate_scores[i]:.2f}" for i in sorted_candidates])
                self.printer.print_in_terminal(
                    "ranking_complete",
                    style="green",
                    elapsed=f"{elapsed:.2f}",
                    total_tasks=total_tasks,
                    best_candidate=sorted_candidates[0],
                    scores=score_details,
                    input_tokens=input_tokens_count,
                    output_tokens=generated_tokens_count,
                    input_cost=total_input_cost,
                    output_cost=total_output_cost,
                    model_names=", ".join(model_names),
                    speed=f"{speed:.2f}"
                )

                rerank_contents = [generate_result.contents[i]
                                   for i in sorted_candidates]
                rerank_conversations = [
                    generate_result.conversations[i] for i in sorted_candidates]
                return CodeGenerateResult(contents=rerank_contents, conversations=rerank_conversations)

        except Exception as e:
            self.printer.print_in_terminal(
                "ranking_process_failed", style="red", error=str(e))            
            elapsed = time.time() - start_time
            self.printer.print_in_terminal(
                "ranking_failed", style="yellow", elapsed=f"{elapsed:.2f}")
            return generate_result
