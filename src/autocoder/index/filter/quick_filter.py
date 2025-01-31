
from typing import List, Dict, Any, Optional
import json
import time
from autocoder.common import SourceCode, AutoCoderArgs
from autocoder.index.symbols_utils import extract_symbols, SymbolsInfo, SymbolType, symbols_info_to_str
from autocoder.utils.queue_communicate import queue_communicate, CommunicateEvent, CommunicateEventType
from autocoder.index.types import IndexItem, FileNumberList, TargetFile
from loguru import logger

class QuickFilter:
    def __init__(self, index_manager):
        self.index_manager = index_manager

    def quick_filter_files(self, index_items: List[IndexItem], query: str) -> FileNumberList:
        start_time = time.monotonic()
        file_number_list = self.index_manager.quick_filter_files.with_llm(
            self.index_manager.index_filter_llm
        ).with_return_type(FileNumberList).run(index_items, query)
        
        if file_number_list:
            for file_number in file_number_list.file_list:
                logger.info(f"Collected file: {index_items[file_number].module_name}")
        
        end_time = time.monotonic()
        logger.info(f"Quick filter files took: {end_time - start_time:.2f}s")
        
        return file_number_list

