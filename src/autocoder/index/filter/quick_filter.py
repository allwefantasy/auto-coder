from typing import List, Union,Dict,Any
from autocoder.index.types import IndexItem
from autocoder.common import AutoCoderArgs,SourceCode
import byzerllm
import time
from autocoder.index.index import IndexManager
from autocoder.index.types import (
    IndexItem,
    TargetFile,    
    FileNumberList
)
from autocoder.rag.token_counter import count_tokens
from loguru import logger


def get_file_path(file_path):
    if file_path.startswith("##"):
        return file_path.strip()[2:]
    return file_path


class QuickFilter():
    def __init__(self, index_manager: IndexManager,stats:Dict[str,Any],sources:List[SourceCode]):
        self.index_manager = index_manager
        self.args = index_manager.args
        self.stats = stats
        self.sources = sources

    @byzerllm.prompt()
    def quick_filter_files(self,file_meta_list:List[IndexItem],query:str) -> str:
        '''
        当用户提一个需求的时候，我们需要找到相关的文件，然后阅读这些文件，并且修改其中部分文件。
        现在，给定下面的索引文件：

        <index>
        {{ content }}
        </index>

        索引文件包含文件序号(##[]括起来的部分)，文件路径，文件符号信息等。
        下面是用户的查询需求：
        
        <query>
        {{ query }}
        </query>

        请根据用户的需求，找到相关的文件，并给出文件序号列表。请返回如下json格式：

        ```json
        {
            "file_list": [
                file_index1,
                file_index2,
                ...
            ]
        }
        ```

        特别注意,如果用户的query里 @文件 或者 @@符号，那么被@的文件或者@@的符号必须要返回，并且查看他们依赖的文件是否相关。        
        '''
        file_meta_str = "\n".join([f"##[{index}]{item.module_name}\n{item.symbols}" for index,item in enumerate(file_meta_list)])
        context = {
            "content": file_meta_str,
            "query": query
        }
        return context    

    def filter(self, index_items: List[IndexItem], query: str) -> Dict[str, TargetFile]:
        final_files: Dict[str, TargetFile] = {}
        if not self.args.skip_filter_index and self.args.index_filter_model:
            start_time = time.monotonic()
            index_items = self.index_manager.read_index()

            prompt_str = self.quick_filter_files.prompt(index_items,query)

            print(prompt_str)
            
            tokens_len = count_tokens(prompt_str)
            
            if tokens_len > 55*1024:
                logger.warning(f"Quick filter prompt is too long, tokens_len: {tokens_len}/{55*1024} fallback to normal filter")
                return final_files
            
            try:
                file_number_list = self.quick_filter_files.with_llm(
                    self.index_manager.index_filter_llm).with_return_type(FileNumberList).run(index_items, self.args.query)
            except Exception as e:
                logger.error(f"Quick filter failed, error: {str(e)} fallback to normal filter")
                return final_files
            
            if file_number_list:
                for file_number in file_number_list.file_list:
                    final_files[get_file_path(index_items[file_number].module_name)] = TargetFile(
                        file_path=index_items[file_number].module_name,
                        reason="Quick Filter"
                    )
            end_time = time.monotonic()            
            self.stats["timings"]["quick_filter"] = end_time - start_time            
        return final_files
