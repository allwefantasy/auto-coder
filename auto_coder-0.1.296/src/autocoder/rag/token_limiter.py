import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Dict
from loguru import logger
from autocoder.common import SourceCode
from byzerllm.utils.client.code_utils import extract_code
import byzerllm
from byzerllm import ByzerLLM
from autocoder.rag.relevant_utils import TaskTiming
from byzerllm import MetaHolder
from autocoder.rag.token_limiter_utils import TokenLimiterResult

class TokenLimiter:
    def __init__(
        self,
        count_tokens: Callable[[str], int],
        full_text_limit: int,
        segment_limit: int,
        buff_limit: int,
        llm:ByzerLLM,
        disable_segment_reorder: bool,
    ):
        self.count_tokens = count_tokens
        self.full_text_limit = full_text_limit
        self.segment_limit = segment_limit
        self.buff_limit = buff_limit
        self.llm = llm
        if self.llm.get_sub_client("chunk_model"):
            self.chunk_llm = self.llm.get_sub_client("chunk_model")
        else:
            self.chunk_llm = self.llm
        self.first_round_full_docs = []
        self.second_round_extracted_docs = []
        self.sencond_round_time = 0
        self.disable_segment_reorder = disable_segment_reorder

    @byzerllm.prompt()
    def extract_relevance_range_from_docs_with_conversation(
        self, conversations: List[Dict[str, str]], documents: List[str]
    ) -> str:
        """
        根据提供的文档和对话历史提取相关信息范围。

        输入:
        1. 文档内容:
        {% for doc in documents %}
        {{ doc }}
        {% endfor %}

        2. 对话历史:
        {% for msg in conversations %}
        <{{ msg.role }}>: {{ msg.content }}
        {% endfor %}

        任务:
        1. 分析最后一个用户问题及其上下文。
        2. 在文档中找出与问题相关的一个或多个重要信息段。
        3. 对每个相关信息段，确定其起始行号(start_line)和结束行号(end_line)。
        4. 信息段数量不超过4个。

        输出要求:
        1. 返回一个JSON数组，每个元素包含"start_line"和"end_line"。
        2. start_line和end_line必须是整数，表示文档中的行号。
        3. 行号从1开始计数。
        4. 如果没有相关信息，返回空数组[]。

        输出格式:
        严格的JSON数组，不包含其他文字或解释。

        示例:
        1.  文档：
            1 这是这篇动物科普文。
            2 大象是陆地上最大的动物之一。
            3 它们生活在非洲和亚洲。
            问题：大象生活在哪里？
            返回：[{"start_line": 2, "end_line": 3}]

        2.  文档：
            1 地球是太阳系第三行星，
            2 有海洋、沙漠，温度适宜，
            3 是已知唯一有生命的星球。
            4 太阳则是太阳系的唯一恒心。
            问题：地球的特点是什么？
            返回：[{"start_line": 1, "end_line": 3}]

        3.  文档：
            1 苹果富含维生素。
            2 香蕉含有大量钾元素。
            问题：橙子的特点是什么？
            返回：[]
        """

    def limit_tokens(
        self,
        relevant_docs: List[SourceCode],
        conversations: List[Dict[str, str]],
        index_filter_workers: int,
    ) -> TokenLimiterResult:
        logger.info(f"=== TokenLimiter Starting ===")
        logger.info(f"Configuration: full_text_limit={self.full_text_limit}, segment_limit={self.segment_limit}, buff_limit={self.buff_limit}")
        logger.info(f"Processing {len(relevant_docs)} source code documents")
        
        start_time = time.time()
        final_relevant_docs = []
        token_count = 0
        doc_num_count = 0
        model_name = self.chunk_llm.default_model_name or "unknown"
        token_limiter_result = TokenLimiterResult(
                docs=[],
                raw_docs=[],
                input_tokens_counts=[],
                generated_tokens_counts=[],
                durations=[],
                model_name=model_name
            )

        reorder_relevant_docs = []

        ## 文档分段（单个文档过大）和重排序逻辑
        ## 1. 背景：在检索过程中，许多文档被切割成多个段落（segments）
        ## 2. 问题：这些segments在召回时因为是按相关分做了排序可能是乱序的，不符合原文顺序，会强化大模型的幻觉。
        ## 3. 目标：重新排序这些segments，确保来自同一文档的segments保持连续且按正确顺序排列。
        ## 4. 实现方案：
        ##    a) 方案一（保留位置）：统一文档的不同segments 根据chunk_index 来置换位置
        ##    b) 方案二（当前实现）：遍历文档，发现某文档的segment A，立即查找该文档的所有其他segments，
        ##       对它们进行排序，并将排序后多个segments插入到当前的segment A 位置中。
        ## TODO:
        ##     1. 未来根据参数决定是否开启重排以及重排的策略
        if not self.disable_segment_reorder:
            logger.info("Document reordering enabled - organizing segments by original document order")
            num_count = 0
            for doc in relevant_docs:
                num_count += 1
                reorder_relevant_docs.append(doc)
                if "original_doc" in doc.metadata and "chunk_index" in doc.metadata:
                    original_doc_name = doc.metadata["original_doc"]

                    temp_docs = []
                    for temp_doc in relevant_docs[num_count:]:
                        if (
                            "original_doc" in temp_doc.metadata
                            and "chunk_index" in temp_doc.metadata
                        ):
                            if (
                                temp_doc.metadata["original_doc"]
                                == original_doc_name
                            ):
                                if temp_doc not in reorder_relevant_docs:
                                    temp_docs.append(temp_doc)

                    temp_docs.sort(key=lambda x: x.metadata["chunk_index"])
                    reorder_relevant_docs.extend(temp_docs)
        else:
            logger.info("Document reordering disabled - using original retrieval order")
            reorder_relevant_docs = relevant_docs

        logger.info(f"After reordering: {len(reorder_relevant_docs)} documents to process")

        ## 非窗口分区实现
        for doc in reorder_relevant_docs:
            doc_tokens = self.count_tokens(doc.source_code)
            doc_num_count += 1
            if token_count + doc_tokens <= self.full_text_limit + self.segment_limit:
                final_relevant_docs.append(doc)
                token_count += doc_tokens
            else:
                break

        ## 如果窗口无法放下所有的相关文档，则需要分区
        if len(final_relevant_docs) < len(reorder_relevant_docs):
            logger.info(f"Token limit exceeded: {len(final_relevant_docs)}/{len(reorder_relevant_docs)} docs fit in window")
            logger.info(f"=== Starting First Round: Full Text Loading ===")
            
            ## 先填充full_text分区
            token_count = 0
            new_token_limit = self.full_text_limit
            doc_num_count = 0
            first_round_start_time = time.time()
            
            for doc in reorder_relevant_docs:
                doc_tokens = self.count_tokens(doc.source_code)
                doc_num_count += 1
                if token_count + doc_tokens <= new_token_limit:
                    self.first_round_full_docs.append(doc)
                    token_count += doc_tokens
                else:
                    break
            
            first_round_duration = time.time() - first_round_start_time
            logger.info(
                f"First round complete: loaded {len(self.first_round_full_docs)} documents"
                f" ({token_count} tokens) in {first_round_duration:.2f}s"
            )

            if len(self.first_round_full_docs) > 0:
                remaining_tokens = (
                    self.full_text_limit + self.segment_limit - token_count
                )
                logger.info(f"Remaining token budget: {remaining_tokens}")
            else:
                logger.warning(
                    "Full text area is empty, this is may caused by the single doc is too long"
                )
                remaining_tokens = self.full_text_limit + self.segment_limit

            ## 继续填充segment分区
            sencond_round_start_time = time.time()
            remaining_docs = reorder_relevant_docs[len(self.first_round_full_docs) :]
            
            logger.info(
                f"=== Starting Second Round: Chunk Extraction ==="
                f"\n  * Documents to process: {len(remaining_docs)}"
                f"\n  * Remaining token budget: {remaining_tokens}"
                f"\n  * Thread pool size: {index_filter_workers or 5}"
            )

            total_processed = 0
            successful_extractions = 0
            
            
            with ThreadPoolExecutor(max_workers=index_filter_workers or 5) as executor:
                future_to_doc = {}
                for doc in remaining_docs:
                    submit_time = time.time()
                    future = executor.submit(self.process_range_doc, doc, conversations)
                    future_to_doc[future] = (doc, submit_time)

                for future in as_completed(future_to_doc):
                    doc, submit_time = future_to_doc[future]
                    end_time = time.time()
                    total_processed += 1
                    progress_percent = (total_processed / len(remaining_docs)) * 100
                    
                    try:
                        result = future.result()
                        task_duration = end_time - submit_time
                        
                        if result and remaining_tokens > 0:
                            self.second_round_extracted_docs.append(result)
                            token_limiter_result.raw_docs.append(result)
                            
                            if "rag" in result.metadata and "chunk" in result.metadata["rag"]:
                                chunk_meta = result.metadata["rag"]["chunk"]
                                token_limiter_result.input_tokens_counts.append(chunk_meta.get("input_tokens_count", 0))
                                token_limiter_result.generated_tokens_counts.append(chunk_meta.get("generated_tokens_count", 0))
                                token_limiter_result.durations.append(chunk_meta.get("duration", 0))
                            
                            tokens = result.tokens
                            successful_extractions += 1
                            
                            logger.info(
                                f"Document extraction [{progress_percent:.1f}%] - {total_processed}/{len(remaining_docs)}:"
                                f"\n  - File: {doc.module_name}"
                                f"\n  - Chunks: {len(result.metadata.get('chunk_ranges', []))}"
                                f"\n  - Extracted tokens: {tokens}"
                                f"\n  - Remaining tokens: {remaining_tokens - tokens if tokens > 0 else remaining_tokens}"
                                f"\n  - Processing time: {task_duration:.2f}s"
                            )
                            
                            if tokens > 0:
                                remaining_tokens -= tokens
                            else:
                                logger.warning(
                                    f"Token count for doc {doc.module_name} is 0 or negative"
                                )
                        elif result:
                            logger.info(
                                f"Document extraction [{progress_percent:.1f}%] - {total_processed}/{len(remaining_docs)}:"
                                f"\n  - File: {doc.module_name}"
                                f"\n  - Skipped: Token budget exhausted ({remaining_tokens} remaining)"
                                f"\n  - Processing time: {task_duration:.2f}s"
                            )
                        else:
                            logger.warning(
                                f"Document extraction [{progress_percent:.1f}%] - {total_processed}/{len(remaining_docs)}:"
                                f"\n  - File: {doc.module_name}"
                                f"\n  - Result: No content extracted"
                                f"\n  - Processing time: {task_duration:.2f}s"
                            )
                    except Exception as exc:
                        logger.error(
                            f"Document extraction [{progress_percent:.1f}%] - {total_processed}/{len(remaining_docs)}:"
                            f"\n  - File: {doc.module_name}"
                            f"\n  - Error: {exc}"
                            f"\n  - Processing time: {end_time - submit_time:.2f}s"
                        )

            final_relevant_docs = (
                self.first_round_full_docs + self.second_round_extracted_docs
            )
            self.sencond_round_time = time.time() - sencond_round_start_time
            total_time = time.time() - start_time
            
            logger.info(
                f"=== Second round complete ==="
                f"\n  * Time: {self.sencond_round_time:.2f}s"
                f"\n  * Documents processed: {total_processed}/{len(remaining_docs)}"
                f"\n  * Successful extractions: {successful_extractions}"
                f"\n  * Extracted tokens: {sum(doc.tokens for doc in self.second_round_extracted_docs)}"
            )
        else:
            logger.info(f"All {len(reorder_relevant_docs)} documents fit within token limits")
            total_time = time.time() - start_time
        
        logger.info(
            f"=== TokenLimiter Complete ==="
            f"\n  * Total time: {total_time:.2f}s"
            f"\n  * Documents selected: {len(final_relevant_docs)}/{len(relevant_docs)}"
            f"\n  * Total tokens: {sum(doc.tokens for doc in final_relevant_docs)}"
        )
        token_limiter_result.docs = final_relevant_docs
        return token_limiter_result

    def process_range_doc(
        self, doc: SourceCode, conversations: List[Dict[str, str]], max_retries=3
    ) -> SourceCode:
        for attempt in range(max_retries):
            content = ""
            start_time = time.time()
            try:
                source_code_with_line_number = ""
                source_code_lines = doc.source_code.split("\n")
                for idx, line in enumerate(source_code_lines):
                    source_code_with_line_number += f"{idx+1} {line}\n"
                
                llm = self.chunk_llm
                model_name = llm.default_model_name or "unknown"
                meta_holder = MetaHolder()

                extraction_start_time = time.time()
                extracted_info = (
                    self.extract_relevance_range_from_docs_with_conversation.options(
                        {"llm_config": {"max_length": 100}}
                    )
                    .with_llm(llm).with_meta(meta_holder)
                    .run(conversations, [source_code_with_line_number])
                )
                extraction_duration = time.time() - extraction_start_time
                
                json_str = extract_code(extracted_info)[0][1]
                json_objs = json.loads(json_str)

                for json_obj in json_objs:
                    start_line = json_obj["start_line"] - 1
                    end_line = json_obj["end_line"]
                    chunk = "\n".join(source_code_lines[start_line:end_line])
                    content += chunk + "\n"

                total_duration = time.time() - start_time
                

                meta = meta_holder.get_meta_model()
                
                input_tokens_count = 0
                generated_tokens_count = 0                                

                if meta:
                    input_tokens_count = meta.input_tokens_count
                    generated_tokens_count = meta.generated_tokens_count                    
                
                logger.debug(
                    f"Document {doc.module_name} chunk extraction details:"
                    f"\n  - Chunks found: {len(json_objs)}"
                    f"\n  - Input tokens: {input_tokens_count}"
                    f"\n  - Generated tokens: {generated_tokens_count}" 
                    f"\n  - LLM time: {extraction_duration:.2f}s"                    
                    f"\n  - Total processing time: {total_duration:.2f}s"
                )

                if "rag" not in doc.metadata:
                    doc.metadata["rag"] = {}
                
                doc.metadata["rag"]["chunk"] = {
                    "original_doc": doc.module_name,
                    "chunk_ranges": json_objs,
                    "processing_time": total_duration,
                    "llm_time": extraction_duration,  

                    "input_tokens_count": input_tokens_count,
                    "generated_tokens_count": generated_tokens_count,
                    "duration": extraction_duration,  
                    "chunk_model":model_name                                                                             
                }
                                
                return SourceCode(
                    module_name=doc.module_name,
                    source_code=content.strip(),
                    tokens=input_tokens_count + generated_tokens_count,
                    metadata={
                        **doc.metadata                        
                    },
                )
            except Exception as e:
                err_duration = time.time() - start_time
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Error processing doc {doc.module_name}, retrying... (Attempt {attempt + 1}) Error: {str(e)}, duration: {err_duration:.2f}s"
                    )
                else:
                    logger.error(
                        f"Failed to process doc {doc.module_name} after {max_retries} attempts: {str(e)}, total duration: {err_duration:.2f}s"
                    )
                    return SourceCode(
                        module_name=doc.module_name, source_code="", tokens=0
                    )
