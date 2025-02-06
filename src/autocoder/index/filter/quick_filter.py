from typing import List, Union, Dict, Any
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.utils_code_auto_generate import stream_chat_with_continue
from byzerllm.utils.str2model import to_model
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
from autocoder.common.printer import Printer


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
        self.printer = Printer()

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

        特别注意
        1. 如果用户的query里 @文件 或者 @@符号，那么被@的文件或者@@的符号必须要返回，并且查看他们依赖的文件是否相关。        
        2. 如果 query 里是一段历史对话，那么对话里的内容提及的文件路径必须要返回。
        3. json格式数据不允许有注释        
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
            
            tokens_len = count_tokens(prompt_str)            
            
            if tokens_len > 55*1024:
                logger.warning(f"Quick filter prompt is too long, tokens_len: {tokens_len}/{55*1024} fallback to normal filter")
                return final_files
            
            try:
                model_name = getattr(self.index_manager.index_filter_llm, 'default_model_name', None)
                if not model_name:
                    model_name = "unknown(without default model name)"
                
                # 渲染 Prompt 模板
                query = self.quick_filter_files.prompt(index_items, self.args.query)
                
                # 使用流式输出处理
                stream_generator = stream_chat_with_continue(
                    self.index_manager.index_filter_llm,
                    [{"role": "user", "content": query}],
                    {}
                )
                
                # 获取完整响应
                full_response, last_meta = stream_out(
                    stream_generator,
                    model_name=model_name,
                    title=self.printer.get_message_from_key_with_format("quick_filter_title", model_name=model_name)
                )                
                # 解析结果
                file_number_list = to_model(full_response, FileNumberList)

                # 打印 token 统计信息
                self.printer.print_in_terminal(
                    "quick_filter_stats", 
                    style="blue",
                    elapsed_time=f"{end_time - start_time:.2f}",
                    input_tokens=last_meta.input_tokens_count,
                    output_tokens=last_meta.generated_tokens_count
                )
                
            except Exception as e:
                self.printer.print_error(self.printer.get_message_from_key_with_format("quick_filter_failed", error=str(e)))
                return final_files
            
            if file_number_list:
                for file_number in file_number_list.file_list:
                    final_files[get_file_path(index_items[file_number].module_name)] = TargetFile(
                        file_path=index_items[file_number].module_name,
                        reason=self.printer.get_message_from_key("quick_filter_reason")
                    )
            end_time = time.monotonic()            
            self.stats["timings"]["quick_filter"] = end_time - start_time            
        return final_files
