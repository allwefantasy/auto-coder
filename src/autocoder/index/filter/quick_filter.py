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
    def extract_code_snippets_from_files(
        self, conversations: List[Dict[str, str]], documents: List[str]
    ) -> str:
        """
        根据提供的文档和对话历史提取相关代码片段。

        输入:
        1. 文档内容:
        <documents>
        {% for doc in documents %}
        {{ doc }}
        {% endfor %}
        </documents>

        2. 对话历史:
        <conversations>
        {% for msg in conversations %}
        <{{ msg.role }}>: {{ msg.content }}
        {% endfor %}
        </conversations>

        任务:
        1. 分析最后一个用户问题及其上下文。
        2. 在文档中找出与问题相关的一个或多个重要代码片段。
        3. 对每个相关代码片段，确定其起始行号(start_line)和结束行号(end_line)。
        4. 代码片段数量不超过4个。

        输出要求:
        1. 返回一个JSON数组，每个元素包含"start_line"和"end_line"。
        2. start_line和end_line必须是整数，表示文档中的行号。
        3. 行号从1开始计数。
        4. 如果没有相关代码片段，返回空数组[]。

        输出格式:
        严格的JSON数组，不包含其他文字或解释。

        示例:
        1.  文档：
            1 def hello():
            2     print("Hello World")
            3 def goodbye():
            4     print("Goodbye World")
            问题：哪个函数会打印 "Hello World"？
            返回：[{"start_line": 1, "end_line": 2}]

        2.  文档：
            1 class MyClass:
            2     def __init__(self):
            3         pass
            4     def method1(self):
            5         pass
            6     def method2(self):
            7         pass
            问题：MyClass有哪些方法？
            返回：[{"start_line": 4, "end_line": 5}, {"start_line": 6, "end_line": 7}]
        """

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
        1. 如果用户的query里 @文件 或者 @@符号，那么被@的文件或者@@的符号必须要返回，并且尝试通过索引文件诸如导入语句等信息找到这些文件依赖的其他文件，再分析这些文件是否需要提供才能满足后续编码。
        2. 如果 query 里是一段历史对话，那么对话里的内容提及的文件路径必须要返回。
        3. 想想，如果是你需要修改代码，然后满足这个需求，根据索引文件，你希望查看哪些文件，修改哪些文件，然后返回这些文件。
        4. 如果用户需求为空，则直接返回空列表即可。
        6. file_list 返回的文件序号，相关度最高要排在前面
        5. 返回的 json格式数据不允许有注释
        '''

        file_meta_str = "\n".join(
            [f"##[{index}]{item.module_name}\n{item.symbols}" for index, item in enumerate(file_meta_list)])
        context = {
            "content": file_meta_str,
            "query": query            
        }
        return context
    
    def _delete_overflow_files(self, validated_file_numbers: List[int],index_items: List[IndexItem]):
        # 拼接所有文件内容并计算总token数
        total_tokens = 0
        selected_files = []
        for file_number in validated_file_numbers:
            file_path = get_file_path(index_items[file_number].module_name)
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    content = f.read()
                    token_count = count_tokens(content)
                    if total_tokens + token_count <= self.max_tokens:
                        total_tokens += token_count
                        selected_files.append(file_number)
                    else:
                        # 如果加上当前文件后超过max_tokens，则停止添加
                        break
            except Exception as e:
                logger.error(f"Failed to read file {file_path}: {e}")
                selected_files.append(file_number)
                continue 

        return selected_files

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

    def handle_overflow_files(
        self,
        index_items: List[IndexItem],
        conversations: List[Dict[str, str]],
        strategy: str = "delete",
    ) -> List[IndexItem]:
        """
        处理超出token限制的文件，提供两种策略：
        1. delete: 直接删除后面的文件
        2. extract: 对超出部分的文件抽取相关代码片段

        Args:
            index_items: 需要处理的文件列表
            conversations: 对话历史
            strategy: 处理策略，可选值为 "delete" 或 "extract"

        Returns:
            处理后的文件列表
        """
        if strategy == "delete":
            # 简单删除后面的文件
            return self._delete_overflow_files(index_items)
        elif strategy == "extract":
            # 对超出部分的文件抽取代码片段
            return self._extract_code_snippets_from_overflow_files(index_items, conversations)
        else:
            raise ValueError(f"Unknown strategy: {strategy}")

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
            

            # 拼接所有文件内容并计算总token数
            total_tokens = 0
            selected_files = []
            for file_number in validated_file_numbers:
                file_path = get_file_path(index_items[file_number].module_name)
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()
                        token_count = count_tokens(content)
                        if total_tokens + token_count <= self.max_tokens:
                            total_tokens += token_count
                            selected_files.append(file_number)
                        else:
                            # 如果加上当前文件后超过max_tokens，则停止添加
                            break
                except Exception as e:
                    logger.error(f"Failed to read file {file_path}: {e}")
                    selected_files.append(file_number)
                    continue
            
            # 将最终选中的文件加入final_files
            for file_number in selected_files:
                file_path = get_file_path(index_items[file_number].module_name)
                final_files[file_path] = TargetFile(
                    file_path=index_items[file_number].module_name,
                    reason=self.printer.get_message_from_key("quick_filter_reason")
                )

        end_time = time.monotonic()
        self.stats["timings"]["quick_filter"] = end_time - start_time
        return QuickFilterResult(
            files=final_files,
            has_error=False
        )
