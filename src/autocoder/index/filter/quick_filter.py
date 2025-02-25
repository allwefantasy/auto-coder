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
from loguru import logger
from byzerllm.utils.client.code_utils import extract_code
import json


def get_file_path(file_path):
    if file_path.startswith("##"):
        return file_path.strip()[2:]
    return file_path


class QuickFilterResult(BaseModel):
    files: Dict[str, TargetFile]
    has_error: bool
    error_message: Optional[str] = None
    file_positions: Optional[Dict[str, int]] = {}

    def get_sorted_file_positions(self) -> List[str]:
        """
        返回按 value 排序的文件列表
        """
        if not self.file_positions:
            return []
        return [file_path for file_path, _ in sorted(self.file_positions.items(), key=lambda x: x[1])]


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
                file_positions: Dict[str, int] = {}

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
                    for index,file_number in enumerate(file_number_list.file_list):
                        if file_number < 0 or file_number >= len(chunk):
                            self.printer.print_in_terminal(
                                "invalid_file_number",
                                style="yellow",
                                file_number=file_number,
                                total_files=len(chunk)
                            )
                            continue
                        file_path = get_file_path(
                            chunk[file_number].module_name)
                        files[file_path] = TargetFile(
                            file_path=chunk[file_number].module_name,
                            reason=self.printer.get_message_from_key(
                                "quick_filter_reason")
                        )
                        file_positions[file_path] = index
                return QuickFilterResult(
                    files=files,
                    has_error=False,
                    file_positions=file_positions
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
        final_file_positions: Dict[str, int] = {}
        has_error = False
        error_messages: List[str] = []

        for result in results:
            if result.has_error:
                has_error = True
                if result.error_message:
                    error_messages.append(result.error_message)
            final_files.update(result.files)


        for result in results:
            if result.has_error:
                has_error = True
                if result.error_message:
                    error_messages.append(result.error_message)
            ## 实现多个 result.file_positions 交织排序
            # 比如第一个是 {file_path_1_0: 0, file_path_1_1: 1, file_path_1_2: 2}    
            # 第二个是 {file_path_2_0: 0, file_path_2_1: 1}
            # 第三个是 {file_path_3_0: 0, file_path_3_1: 1, file_path_3_2: 2, file_path_3_3: 3}
            # 收集逻辑为所以 0 的为一组，然后序号为 0,1,2, 所有1 的为一组，序号是 3,4,5,依次往下推
            # {file_path_1_0: 0, file_path_2_0: 1, file_path_3_0: 2, file_path_1_1: 3, file_path_2_1: 4, file_path_3_1: 5}            
            # 
            # 获取所有结果的最大 position 值
            max_position = max([max(pos.values()) for pos in [result.file_positions for result in results if result.file_positions]] + [0])

            # 创建一个映射表，用于记录每个 position 对应的文件路径
            position_map = {}
            for result in results:
                if result.file_positions:
                    for file_path, position in result.file_positions.items():
                        if position not in position_map:
                            position_map[position] = []
                        position_map[position].append(file_path)

            # 重新排序文件路径
            new_file_positions = {}
            current_index = 0
            for position in range(max_position + 1):
                if position in position_map:
                    for file_path in position_map[position]:
                        new_file_positions[file_path] = current_index
                        current_index += 1

            # 更新 final_file_positions
            final_file_positions.update(new_file_positions)

        return QuickFilterResult(
            files=final_files,
            has_error=has_error,
            error_message="\n".join(error_messages) if error_messages else None
        )
    

    @byzerllm.prompt()
    def quick_filter_files(self, file_meta_list: List[IndexItem], query: str) -> str:
        '''
        当用户提一个需求的时候，我们要找到两种类型的源码文件：
        1. 根据需求需要被修改的文件，我们叫 edited_files
        2. 为了能够完成修改这些文件，还需要的一些额外参考文件, 我们叫 reference_files
        3. 因为修改了 edited_files 文件，可能有一些依赖 edited_files 的文件也需要被修改，我们叫 dependent_files

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

        特别注意:    
        1. 如果用户的query里有 @文件 或者 @@符号，并且他们在索引文件中，那么被@的文件或者@@的符号必须要返回。
        2. 根据需求以及根据 @文件 或者 @@符号 找到的文件，猜测需要被修改的edited_files文件，然后尝试通过索引文件诸如导入语句等信息找到这些文件依赖的其他文件得到 reference_files,dependent_files。
        3. file_list 里的文件序号，按被 @ 或者 @@ 文件，edited_files文件，reference_files,dependent_files文件的顺序排列。注意，reference_files 你要根据需求来猜测是否需要，过滤掉不相关的，避免返回文件数过多。
        4. 如果 query 里是一段历史对话，那么对话里的内容提及的文件路径必须要返回。        
        5. 如果用户需求为空，则直接返回空列表即可。        
        6. 返回的 json格式数据不允许有注释
        '''

        file_meta_str = "\n".join(
            [f"##[{index}]{item.module_name}\n{item.symbols}" for index, item in enumerate(file_meta_list)])
        context = {
            "content": file_meta_str,
            "query": query            
        }
        return context
    

    def _extract_code_snippets_from_overflow_files(self, validated_file_numbers: List[int],index_items: List[IndexItem], conversations: List[Dict[str, str]]):
        token_count = 0        
        selected_files = []
        selected_file_contents = []
        full_file_tokens = int(self.max_tokens * 0.8)
        for file_number in validated_file_numbers:
            file_path = get_file_path(index_items[file_number].module_name)
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            tokens = count_tokens(content)
            if token_count + tokens <= full_file_tokens:
                selected_files.append(file_number)
                selected_file_contents.append(content)
                token_count += tokens
            else:
                # 对超出部分抽取代码片段
                try:
                    extracted_info = (
                        self.extract_code_snippets_from_files.options(
                            {"llm_config": {"max_length": 100}}
                        )
                        .with_llm(self.index_manager.index_filter_llm)
                        .run(conversations, [content])
                    )
                    json_str = extract_code(extracted_info)[0][1]
                    json_objs = json.loads(json_str)

                    new_content = ""

                    if json_objs:                        
                        for json_obj in json_objs:
                            start_line = json_obj["start_line"] - 1
                            end_line = json_obj["end_line"]
                            chunk = "\n".join(content.split("\n")[start_line:end_line])
                            new_content += chunk + "\n"
                      
                        token_count += count_tokens(new_content)
                        if token_count >= self.max_tokens:
                            break
                        else:
                            selected_files.append(file_number)
                            selected_file_contents.append(new_content)
                except Exception as e:
                    logger.error(f"Failed to extract code snippets from {file_path}: {e}")
        return selected_files


    def filter(self, index_items: List[IndexItem], query: str) -> QuickFilterResult:
        final_files: Dict[str, TargetFile] = {}
        final_file_positions: Dict[str, int] = {}
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
                    logger.error(f"Error extracting file number list: {e}")
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
            speed = last_meta.generated_tokens_count / (end_time - start_time)

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
            validated_file_numbers = []
            for file_number in file_number_list.file_list:
                if file_number < 0 or file_number >= len(index_items):
                    self.printer.print_in_terminal(
                        "invalid_file_number",
                        style="yellow",
                        file_number=file_number,
                        total_files=len(index_items)
                    )
                    continue
                validated_file_numbers.append(file_number)
                                
            # 将最终选中的文件加入final_files
            for index,file_number in enumerate(validated_file_numbers):
                file_path = get_file_path(index_items[file_number].module_name)
                final_files[file_path] = TargetFile(
                    file_path=index_items[file_number].module_name,
                    reason=self.printer.get_message_from_key("quick_filter_reason")
                )
                final_file_positions[file_path] = index

        end_time = time.monotonic()
        self.stats["timings"]["quick_filter"] = end_time - start_time
        return QuickFilterResult(
            files=final_files,
            has_error=False,
            file_positions=final_file_positions
        )
