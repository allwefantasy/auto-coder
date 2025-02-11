from typing import List, Union, Dict, Any, Optional
from pydantic import BaseModel
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
from autocoder.common.printer import Printer
from concurrent.futures import ThreadPoolExecutor
import threading

from autocoder.utils.llms import get_llm_names


def get_file_path(file_path):
    if file_path.startswith("##"):
        return file_path.strip()[2:]
    return file_path


class QuickFilterResult(BaseModel):
    files: Dict[str, TargetFile]
    has_error: bool
    error_message: Optional[str] = None

class QuickFilter():
    def __init__(self, index_manager: IndexManager,stats:Dict[str,Any],sources:List[SourceCode]):
        self.index_manager = index_manager
        self.args = index_manager.args
        self.stats = stats
        self.sources = sources
        self.printer = Printer()
        self.max_tokens = self.args.index_filter_model_max_input_length


    def big_filter(self, index_items: List[IndexItem],) -> QuickFilterResult:
        
        final_files: Dict[str, TargetFile] = {}
        final_files_lock = threading.Lock()
        has_error = False
        error_message = None
        error_lock = threading.Lock()
        
        chunks = []
        current_chunk = []
                
        # 将 index_items 切分成多个 chunks,第一个chunk尽可能接近max_tokens
        for item in index_items:
            # 使用 quick_filter_files.prompt 生成文本再统计
            temp_chunk = current_chunk + [item]
            prompt_text = self.quick_filter_files.prompt(temp_chunk, self.args.query)
            temp_size = count_tokens(prompt_text)            
            # 如果当前chunk为空,或者添加item后不超过max_tokens,就添加到当前chunk
            if not current_chunk or temp_size <= self.max_tokens:
                current_chunk.append(item)                
            else:
                # 当前chunk已满,创建新chunk
                chunks.append(current_chunk)
                current_chunk = [item]                
            
        if current_chunk:
            chunks.append(current_chunk)
        
        tokens_len = count_tokens(self.quick_filter_files.prompt(index_items, self.args.query))
        self.printer.print_in_terminal(
                "quick_filter_too_long",
                style="yellow",
                tokens_len=tokens_len,
                max_tokens=self.max_tokens,
                split_size=len(chunks)
            )    

        def process_chunk(chunk_index: int, chunk: List[IndexItem]) -> None:
            try:
                model_name = ",".join(get_llm_names(self.index_manager.index_filter_llm))
                
                if chunk_index == 0:
                    # 第一个chunk使用流式输出
                    stream_generator = stream_chat_with_continue(
                        self.index_manager.index_filter_llm,
                        [{"role": "user", "content": self.quick_filter_files.prompt(chunk, self.args.query)}],
                        {}
                    )
                    full_response, _ = stream_out(
                        stream_generator,
                        model_name=model_name,
                        title=self.printer.get_message_from_key_with_format("quick_filter_title", model_name=model_name),
                        args=self.args
                    )
                    file_number_list = to_model(full_response, FileNumberList)
                else:
                    # 其他chunks直接使用with_llm
                    file_number_list = self.quick_filter_files.with_llm(self.index_manager.index_filter_llm).with_return_type(FileNumberList).run(chunk, self.args.query)
                
                if file_number_list:
                    with final_files_lock:
                        for file_number in file_number_list.file_list:
                            file_path = get_file_path(chunk[file_number].module_name)
                            final_files[file_path] = TargetFile(
                                file_path=chunk[file_number].module_name,
                                reason=self.printer.get_message_from_key("quick_filter_reason")
                            )
                            
            except Exception as e:
                self.printer.print_in_terminal(
                    "quick_filter_failed",
                    style="red",
                    error=str(e)
                )
                with error_lock:
                    has_error = True
                    error_message = str(e)

        if chunks:
            with ThreadPoolExecutor() as executor:
                # 提交所有chunks到线程池
                futures = [executor.submit(process_chunk, i, chunk) 
                          for i, chunk in enumerate(chunks)]
                
                # 等待所有任务完成
                for future in futures:
                    future.result()
                
        return QuickFilterResult(
            files=final_files,
            has_error=has_error,
            error_message=error_message
        )    

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

    def filter(self, index_items: List[IndexItem], query: str) -> QuickFilterResult:
        final_files: Dict[str, TargetFile] = {}
        start_time = time.monotonic()        

        prompt_str = self.quick_filter_files.prompt(index_items,query)            
        
        tokens_len = count_tokens(prompt_str)            
        
        # Print current index size
        self.printer.print_in_terminal(
            "quick_filter_tokens_len",
            style="blue",
            tokens_len=tokens_len
        )
        
        if tokens_len > self.max_tokens:                        
            return self.big_filter(index_items)
        
        try:
            model_name = ",".join(get_llm_names(self.index_manager.index_filter_llm))
            
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
                title=self.printer.get_message_from_key_with_format("quick_filter_title", model_name=model_name),
                args=self.args
            )                
            # 解析结果
            file_number_list = to_model(full_response, FileNumberList)
            end_time = time.monotonic()            
            # 打印 token 统计信息
            self.printer.print_in_terminal(
                "quick_filter_stats", 
                style="blue",
                elapsed_time=f"{end_time - start_time:.2f}",
                input_tokens=last_meta.input_tokens_count,
                output_tokens=last_meta.generated_tokens_count
            )
            
        except Exception as e:
            self.printer.print_in_terminal(
                "quick_filter_failed",
                style="red",
                error=str(e)
            )
            return QuickFilterResult(
                files=final_files,
                has_error=True,
                error_message=str(e)
            )
        
        if file_number_list:
            for file_number in file_number_list.file_list:
                final_files[get_file_path(index_items[file_number].module_name)] = TargetFile(
                    file_path=index_items[file_number].module_name,
                    reason=self.printer.get_message_from_key("quick_filter_reason")
                )
        end_time = time.monotonic()            
        self.stats["timings"]["quick_filter"] = end_time - start_time            
        return QuickFilterResult(
            files=final_files,
            has_error=False
        )    
