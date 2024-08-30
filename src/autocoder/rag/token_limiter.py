import json
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Callable, Dict
from loguru import logger
from autocoder.common import SourceCode
from byzerllm.utils.client.code_utils import extract_code


class TokenLimiter:
    def __init__(
        self,
        count_tokens: Callable[[str], int],
        token_limit: int,
        llm,
        extract_relevance_range_from_docs_with_conversation,
    ):
        self.count_tokens = count_tokens
        self.token_limit = token_limit
        self.llm = llm
        self.extract_relevance_range_from_docs_with_conversation = (
            extract_relevance_range_from_docs_with_conversation
        )
        self.first_round_full_docs = []
        self.second_round_extracted_docs = []
        self.sencond_round_time = 0

    def limit_tokens(
        self,
        relevant_docs: List[SourceCode],
        conversations: List[Dict[str, str]],
        index_filter_workers: int,
    ) -> List[SourceCode]:
        final_relevant_docs = []
        token_count = 0
        doc_num_count = 0
        for doc in relevant_docs:
            doc_tokens = self.count_tokens(doc.source_code)
            doc_num_count += 1
            if token_count + doc_tokens <= self.token_limit:
                final_relevant_docs.append(doc)
                token_count += doc_tokens
            else:
                break

        if len(final_relevant_docs) < len(relevant_docs):

            token_count = 0
            new_token_limit = self.token_limit * 0.8
            doc_num_count = 0
            for doc in relevant_docs:
                doc_tokens = self.count_tokens(doc.source_code)
                doc_num_count += 1
                if token_count + doc_tokens <= new_token_limit:
                    self.first_round_full_docs.append(doc)
                    token_count += doc_tokens
                else:
                    break

            sencond_round_start_time = time.time()
            remaining_tokens = self.token_limit - new_token_limit
            remaining_docs = relevant_docs[len(self.first_round_full_docs) :]
            logger.info(
                f"first round docs: {len(self.first_round_full_docs)} remaining docs: {len(remaining_docs)} index_filter_workers: {index_filter_workers}"
            )

            with ThreadPoolExecutor(max_workers=index_filter_workers or 5) as executor:
                future_to_doc = {
                    executor.submit(self.process_range_doc, doc, conversations): doc
                    for doc in remaining_docs
                }

                for future in as_completed(future_to_doc):
                    doc = future_to_doc[future]
                    try:
                        result = future.result()
                        if result and remaining_tokens > 0:
                            self.second_round_extracted_docs.append(result)
                            tokens = self.count_tokens(result.source_code)
                            if tokens > 0:
                                remaining_tokens -= tokens
                            else:
                                logger.warning(
                                    f"Token count for doc {doc.module_name} is 0 or negative"
                                )
                    except Exception as exc:
                        logger.error(
                            f"Processing doc {doc.module_name} generated an exception: {exc}"
                        )

            final_relevant_docs = (
                self.first_round_full_docs + self.second_round_extracted_docs
            )
            self.sencond_round_time = time.time() - sencond_round_start_time
            logger.info(
                f"Second round processing time: {self.sencond_round_time:.2f} seconds"
            )

        return final_relevant_docs

    def process_range_doc(
        self, doc: SourceCode, conversations: List[Dict[str, str]], max_retries=3
    ) -> SourceCode:
        for attempt in range(max_retries):
            content = ""
            try:
                source_code_with_line_number = ""
                source_code_lines = doc.source_code.split("\n")
                for idx, line in enumerate(source_code_lines):
                    source_code_with_line_number += f"{idx+1} {line}\n"

                extracted_info = (
                    self.extract_relevance_range_from_docs_with_conversation.with_llm(
                        self.llm
                    ).run(conversations, [source_code_with_line_number])
                )                
                json_str = extract_code(extracted_info)[0][1]
                json_objs = json.loads(json_str)

                for json_obj in json_objs:
                    start_line = json_obj["start_line"] - 1
                    end_line = json_obj["end_line"]
                    chunk = "\n".join(source_code_lines[start_line:end_line])
                    content += chunk + "\n"

                return SourceCode(
                    module_name=doc.module_name, source_code=content.strip()
                )
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(
                        f"Error processing doc {doc.module_name}, retrying... (Attempt {attempt + 1}) Error: {str(e)}"
                    )
                else:
                    logger.error(
                        f"Failed to process doc {doc.module_name} after {max_retries} attempts: {str(e)}"
                    )
                    return SourceCode(
                        module_name=doc.module_name, source_code=content.strip()
                    )
