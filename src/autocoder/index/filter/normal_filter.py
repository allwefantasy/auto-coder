from typing import List, Union,Dict,Any,Optional

from pydantic import BaseModel
from autocoder.index.types import IndexItem
from autocoder.common import SourceCode, AutoCoderArgs
import byzerllm
import time
from autocoder.index.index import IndexManager
from autocoder.index.types import (
    IndexItem,
    TargetFile,
    VerifyFileRelevance,
    FileList,
    FileNumberList
)
from loguru import logger
from autocoder.utils.queue_communicate import (
    queue_communicate,
    CommunicateEvent,
    CommunicateEventType,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import json

def get_file_path(file_path):
    if file_path.startswith("##"):
        return file_path.strip()[2:]
    return file_path

class NormalFilterResult(BaseModel):
    files: Dict[str, TargetFile]
    has_error: bool
    error_message: Optional[str] = None
    file_positions: Optional[Dict[str, int]] = {}

class NormalFilter():
    def __init__(self, index_manager: IndexManager,stats:Dict[str,Any],sources:List[SourceCode]):
        self.index_manager = index_manager
        self.args = index_manager.args
        self.stats = stats
        self.sources = sources

    def filter(self, index_items: List[IndexItem], query: str) -> Dict[str, TargetFile]:
        
        final_files: Dict[str, TargetFile] = {}
        if not self.args.skip_filter_index:
            # Phase 3: Level 1 filtering - Query-based
            logger.info(
                "Phase 3: Performing Level 1 filtering (query-based)...")

            phase_start = time.monotonic()
            target_files = self.index_manager.get_target_files_by_query(self.args.query)

            if target_files:
                for file in target_files.file_list:
                    file_path = file.file_path.strip()
                    final_files[get_file_path(file_path)] = file
                self.stats["level1_filtered"] = len(target_files.file_list)
            phase_end = time.monotonic()
            self.stats["timings"]["normal_filter"]["level1_filter"] = phase_end - phase_start

            # Phase 4: Level 2 filtering - Related files                        
            if target_files is not None and self.args.index_filter_level >= 2:
                logger.info(
                    "Phase 4: Performing Level 2 filtering (related files)...")
                phase_start = time.monotonic()
                related_files = self.index_manager.get_related_files(
                    [file.file_path for file in target_files.file_list]
                )
                if related_files is not None:
                    for file in related_files.file_list:
                        file_path = file.file_path.strip()
                        final_files[get_file_path(file_path)] = file
                    self.stats["level2_filtered"] = len(related_files.file_list)
                phase_end = time.monotonic()
                self.stats["timings"]["normal_filter"]["level2_filter"] = phase_end - phase_start

            # if not final_files:
            #     logger.warning("No related files found, using all files")
            #     for source in self.sources:
            #         final_files[get_file_path(source.module_name)] = TargetFile(
            #             file_path=source.module_name,
            #             reason="No related files found, use all files",
            #         )


            # Phase 5: Relevance verification
            logger.info("Phase 5: Performing relevance verification...")
            if self.args.index_filter_enable_relevance_verification:
                phase_start = time.monotonic()
                verified_files = {}
                temp_files = list(final_files.values())
                verification_results = []
                
                def print_verification_results(results):
                    from rich.table import Table
                    from rich.console import Console
                    
                    console = Console()
                    table = Table(title="File Relevance Verification Results", show_header=True, header_style="bold magenta")
                    table.add_column("File Path", style="cyan", no_wrap=True)
                    table.add_column("Score", justify="right", style="green")
                    table.add_column("Status", style="yellow")
                    table.add_column("Reason/Error")
                    
                    for file_path, score, status, reason in results:
                        table.add_row(
                            file_path,
                            str(score) if score is not None else "N/A",
                            status,
                            reason
                        )
                    
                    console.print(table)

                def verify_single_file(file: TargetFile):
                    for source in self.sources:
                        if source.module_name == file.file_path:
                            file_content = source.source_code
                            try:
                                result = self.index_manager.verify_file_relevance.with_llm(self.index_manager.llm).with_return_type(VerifyFileRelevance).run(
                                    file_content=file_content,
                                    query=self.args.query
                                )
                                if result.relevant_score >= self.args.verify_file_relevance_score:
                                    verified_files[file.file_path] = TargetFile(
                                        file_path=file.file_path,
                                        reason=f"Score:{result.relevant_score}, {result.reason}"
                                    )
                                    return file.file_path, result.relevant_score, "PASS", result.reason
                                else:
                                    return file.file_path, result.relevant_score, "FAIL", result.reason
                            except Exception as e:
                                error_msg = str(e)
                                verified_files[file.file_path] = TargetFile(
                                    file_path=file.file_path,
                                    reason=f"Verification failed: {error_msg}"
                                )
                                return file.file_path, None, "ERROR", error_msg
                    return None

                with ThreadPoolExecutor(max_workers=self.args.index_filter_workers) as executor:
                    futures = [executor.submit(verify_single_file, file)
                            for file in temp_files]
                    for future in as_completed(futures):
                        result = future.result()
                        if result:
                            verification_results.append(result)
                            time.sleep(self.args.anti_quota_limit)

                # Print verification results in a table
                print_verification_results(verification_results)
                
                self.stats["verified_files"] = len(verified_files)
                phase_end = time.monotonic()
                self.stats["timings"]["normal_filter"]["relevance_verification"] = phase_end - phase_start

                # Keep all files, not just verified ones
                final_files = verified_files
        
        return NormalFilterResult(
            files=final_files,
            has_error=False,
            error_message=None
        )
