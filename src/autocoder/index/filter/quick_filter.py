from typing import List, Union, Dict, Any, Optional
from pydantic import BaseModel
from autocoder.utils.auto_coder_utils.chat_stream_out import stream_out
from autocoder.common.utils_code_auto_generate import stream_chat_with_continue
from byzerllm.utils.str2model import to_model
from autocoder.index.types import IndexItem
from autocoder.common import AutoCoderArgs, SourceCode
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
from byzerllm import MetaHolder

from autocoder.utils.llms import get_llm_names, get_model_info


def get_file_path(file_path):
    if file_path.startswith("##"):
        return file_path.strip()[2:]
    return file_path


class QuickFilterResult(BaseModel):
    files: Dict[str, TargetFile]
    has_error: bool
    error_message: Optional[str] = None


class QuickFilter():
    def __init__(self, index_manager: IndexManager, stats: Dict[str, Any], sources: List[SourceCode]):
        self.index_manager = index_manager
        self.args = index_manager.args
        self.stats = stats
        self.sources = sources
        self.printer = Printer()
        self.max_tokens = self.args.index_filter_model_max_input_length

    def big_filter(self, index_items: List[IndexItem],) -> QuickFilterResult:
        chunks = []
        current_chunk = []

        # 将 index_items 切分成多个 chunks,第一个chunk尽可能接近max_tokens
        for item in index_items:
            # 使用 quick_filter_files.prompt 生成文本再统计
            temp_chunk = current_chunk + [item]
            prompt_text = self.quick_filter_files.prompt(
                temp_chunk, self.args.query)
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

        tokens_len = count_tokens(
            self.quick_filter_files.prompt(index_items, self.args.query))
        self.printer.print_in_terminal(
            "quick_filter_too_long",
            style="yellow",
            tokens_len=tokens_len,
            max_tokens=self.max_tokens,
            split_size=len(chunks)
        )

        def process_chunk(chunk_index: int, chunk: List[IndexItem]) -> QuickFilterResult:
            try:
                # 获取模型名称列表
                model_names = get_llm_names(
                    self.index_manager.index_filter_llm)
                model_name = ",".join(model_names)
                files: Dict[str, TargetFile] = {}

                # 获取模型价格信息
                model_info_map = {}
                for name in model_names:
                    # 第二个参数是产品模式,从args中获取
                    info = get_model_info(name, self.args.product_mode)
                    if info:
                        model_info_map[name] = {
                            # 每百万tokens成本
                            "input_price": info.get("input_price", 0.0),
                            # 每百万tokens成本
                            "output_price": info.get("output_price", 0.0)
                        }

                if chunk_index == 0:
                    # 第一个chunk使用流式输出
                    stream_generator = stream_chat_with_continue(
                        self.index_manager.index_filter_llm,
                        [{"role": "user", "content": self.quick_filter_files.prompt(
                            chunk, self.args.query)}],
                        {}
                    )
                    full_response, last_meta = stream_out(
                        stream_generator,
                        model_name=model_name,
                        title=self.printer.get_message_from_key_with_format(
                            "quick_filter_title", model_name=model_name),
                        args=self.args
                    )
                    file_number_list = to_model(full_response, FileNumberList)

                    # 计算总成本
                    total_input_cost = 0.0
                    total_output_cost = 0.0

                    for name in model_names:
                        info = model_info_map.get(name, {})
                        # 计算公式:token数 * 单价 / 1000000
                        total_input_cost += (last_meta.input_tokens_count *
                                             info.get("input_price", 0.0)) / 1000000
                        total_output_cost += (last_meta.generated_tokens_count *
                                              info.get("output_price", 0.0)) / 1000000

                    # 四舍五入到4位小数
                    total_input_cost = round(total_input_cost, 4)
                    total_output_cost = round(total_output_cost, 4)

                    # 打印 token 统计信息和成本
                    self.printer.print_in_terminal(
                        "quick_filter_stats",
                        style="blue",
                        input_tokens=last_meta.input_tokens_count,
                        output_tokens=last_meta.generated_tokens_count,
                        input_cost=total_input_cost,
                        output_cost=total_output_cost,
                        model_names=model_name
                    )
                else:
                    # 其他chunks直接使用with_llm
                    meta_holder = MetaHolder()
                    start_time = time.monotonic()
                    file_number_list = self.quick_filter_files.with_llm(self.index_manager.index_filter_llm).with_meta(
                        meta_holder).with_return_type(FileNumberList).run(chunk, self.args.query)
                    end_time = time.monotonic()
                    
                    total_input_cost = 0.0
                    total_output_cost = 0.0
                    if meta_holder.get_meta():
                        meta_dict = meta_holder.get_meta()                    
                        total_input_cost = meta_dict.get("input_tokens_count", 0) * model_info_map.get(model_name, {}).get("input_price", 0.0) / 1000000
                        total_output_cost = meta_dict.get("generated_tokens_count", 0) * model_info_map.get(model_name, {}).get("output_price", 0.0) / 1000000
                    
                    self.printer.print_in_terminal(
                        "quick_filter_stats",
                        style="blue",
                        input_tokens=meta_dict.get("input_tokens_count", 0),
                        output_tokens=meta_dict.get("generated_tokens_count", 0),
                        input_cost=total_input_cost,
                        output_cost=total_output_cost,
                        model_names=model_name,
                        elapsed_time=f"{end_time - start_time:.2f}"
                    )

                if file_number_list:
                    for file_number in file_number_list.file_list:
                        file_path = get_file_path(
                            chunk[file_number].module_name)
                        files[file_path] = TargetFile(
                            file_path=chunk[file_number].module_name,
                            reason=self.printer.get_message_from_key(
                                "quick_filter_reason")
                        )
                return QuickFilterResult(
                    files=files,
                    has_error=False
                )

            except Exception as e:
                self.printer.print_in_terminal(
                    "quick_filter_failed",
                    style="red",
                    error=str(e)
                )
                return QuickFilterResult(
                    files={},
                    has_error=True,
                    error_message=str(e)
                )

        results: List[QuickFilterResult] = []
        if chunks:
            with ThreadPoolExecutor() as executor:
                # 提交所有chunks到线程池并收集结果
                futures = [executor.submit(process_chunk, i, chunk)
                           for i, chunk in enumerate(chunks)]

                # 等待所有任务完成并收集结果
                for future in futures:
                    results.append(future.result())

        # 合并所有结果
        final_files: Dict[str, TargetFile] = {}
        has_error = False
        error_messages: List[str] = []

        for result in results:
            if result.has_error:
                has_error = True
                if result.error_message:
                    error_messages.append(result.error_message)
            final_files.update(result.files)

        return QuickFilterResult(
            files=final_files,
            has_error=has_error,
            error_message="\n".join(error_messages) if error_messages else None
        )

    @byzerllm.prompt()
    def quick_filter_files(self, file_meta_list: List[IndexItem], query: str) -> str:
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
        file_meta_str = "\n".join(
            [f"##[{index}]{item.module_name}\n{item.symbols}" for index, item in enumerate(file_meta_list)])
        context = {
            "content": file_meta_str,
            "query": query
        }
        return context

    def filter(self, index_items: List[IndexItem], query: str) -> QuickFilterResult:
        final_files: Dict[str, TargetFile] = {}
        start_time = time.monotonic()

        prompt_str = self.quick_filter_files.prompt(index_items, query)

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
            # 获取模型名称
            model_names = get_llm_names(self.index_manager.index_filter_llm)
            model_name = ",".join(model_names)

            # 获取模型价格信息
            model_info_map = {}
            for name in model_names:
                # 第二个参数是产品模式,从args中获取
                info = get_model_info(name, self.args.product_mode)
                if info:
                    model_info_map[name] = {
                        # 每百万tokens成本
                        "input_price": info.get("input_price", 0.0),
                        # 每百万tokens成本
                        "output_price": info.get("output_price", 0.0)
                    }

            # 渲染 Prompt 模板
            query = self.quick_filter_files.prompt(
                index_items, self.args.query)

            # 使用流式输出处理
            stream_generator = stream_chat_with_continue(
                self.index_manager.index_filter_llm,
                [{"role": "user", "content": query}],
                {}
            )

            def extract_file_number_list(content: str) -> str:
                try:
                    v = to_model(content, FileNumberList)
                    return "\n".join([index_items[file_number].module_name for file_number in v.file_list])
                except Exception as e:
                    return content

            # 获取完整响应
            full_response, last_meta = stream_out(
                stream_generator,
                model_name=model_name,
                title=self.printer.get_message_from_key_with_format(
                    "quick_filter_title", model_name=model_name),
                args=self.args,
                display_func=extract_file_number_list
            )
            # 解析结果
            file_number_list = to_model(full_response, FileNumberList)
            end_time = time.monotonic()

            # 计算总成本
            total_input_cost = 0.0
            total_output_cost = 0.0

            for name in model_names:
                info = model_info_map.get(name, {})
                # 计算公式:token数 * 单价 / 1000000
                total_input_cost += (last_meta.input_tokens_count *
                                     info.get("input_price", 0.0)) / 1000000
                total_output_cost += (last_meta.generated_tokens_count *
                                      info.get("output_price", 0.0)) / 1000000

            # 四舍五入到4位小数
            total_input_cost = round(total_input_cost, 4)
            total_output_cost = round(total_output_cost, 4)
            speed = last_meta.input_tokens_count / (end_time - start_time)

            # 打印 token 统计信息和成本
            self.printer.print_in_terminal(
                "quick_filter_stats",
                style="blue",
                elapsed_time=f"{end_time - start_time:.2f}",
                input_tokens=last_meta.input_tokens_count,
                output_tokens=last_meta.generated_tokens_count,
                input_cost=total_input_cost,
                output_cost=total_output_cost,
                model_names=model_name,
                speed=f"{speed:.2f}"
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
                    reason=self.printer.get_message_from_key(
                        "quick_filter_reason")
                )
        end_time = time.monotonic()
        self.stats["timings"]["quick_filter"] = end_time - start_time
        return QuickFilterResult(
            files=final_files,
            has_error=False
        )
