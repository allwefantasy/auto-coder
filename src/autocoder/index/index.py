import os
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from autocoder.common import SourceCode, AutoCoderArgs
from autocoder.index.symbols_utils import (
    extract_symbols,
    SymbolType,
    symbols_info_to_str,
)
from autocoder.privacy.model_filter import ModelPathFilter
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import re

import byzerllm
import hashlib

from autocoder.common.printer import Printer
from autocoder.common.auto_coder_lang import get_message
from autocoder.utils.llms import get_llm_names, get_model_info
from autocoder.index.types import (
    IndexItem,
    TargetFile,
    FileList,
)
from autocoder.common.global_cancel import global_cancel
from autocoder.utils.llms import get_llm_names
from autocoder.rag.token_counter import count_tokens
from autocoder.common.stream_out_type import IndexStreamOutType
from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events import event_content as EventContentCreator
from loguru import logger

class IndexManager:
    def __init__(
        self, llm: byzerllm.ByzerLLM, sources: List[SourceCode], args: AutoCoderArgs
    ):
        self.sources = sources
        self.source_dir = args.source_dir
        # Initialize model filter for index_llm and index_filter_llm
        self.index_model_filter = None
        self.index_filter_model_filter = None
        self.anti_quota_limit = (
            args.index_model_anti_quota_limit or args.anti_quota_limit
        )
        self.index_dir = os.path.join(self.source_dir, ".auto-coder")
        self.index_file = os.path.join(self.index_dir, "index.json")
        if llm and (s := llm.get_sub_client("index_model")):
            self.index_llm = s
        else:
            self.index_llm = llm

        if llm and (s := llm.get_sub_client("index_filter_model")):
            self.index_filter_llm = s
        else:
            self.index_filter_llm = llm

        self.llm = llm

        # Initialize model filters
        if self.index_llm:
            self.index_model_filter = ModelPathFilter.from_model_object(
                self.index_llm, args)
        if self.index_filter_llm:
            self.index_filter_model_filter = ModelPathFilter.from_model_object(
                self.index_filter_llm, args)
        self.args = args
        self.max_input_length = (
            args.index_model_max_input_length or args.model_max_input_length
        )
        self.printer = Printer()

        # 如果索引目录不存在,则创建它
        if not os.path.exists(self.index_dir):
            os.makedirs(self.index_dir)

    @byzerllm.prompt()
    def verify_file_relevance(self, file_content: str, query: str) -> str:
        """
        请验证下面的文件内容是否与用户问题相关:

        文件内容:
        {{ file_content }}

        用户问题:
        {{ query }}

        相关是指，需要依赖这个文件提供上下文，或者需要修改这个文件才能解决用户的问题。
        请给出相应的可能性分数：0-10，并结合用户问题，理由控制在50字以内。格式如下:

        ```json
        {
            "relevant_score": 0-10,
            "reason": "这是相关的原因（不超过10个中文字符）..."
        }
        ```
        """

    @byzerllm.prompt()
    def _get_related_files(self, indices: str, file_paths: str) -> str:
        """
        下面是所有文件以及对应的符号信息：

        {{ indices }}        

        请参考上面的信息，找到被下列文件使用或者引用到的文件列表：

        {{ file_paths }}

        请按如下格式进行输出：

        ```json
        {
            "file_list": [
                {
                    "file_path": "path/to/file1.py",
                    "reason": "这是被选择的原因（不超过10个中文字符）"
                },
                {
                    "file_path": "path/to/file2.py",
                    "reason": "这是被选择的原因（不超过10个中文字符）"
                }
            ]
        }
        ```

        注意，
        1. 找到的文件名必须出现在上面的文件列表中
        2. 原因控制在20字以内
        3. 如果没有相关的文件，输出如下 json 即可：

        ```json
        {"file_list": []}
        ```
        """

    @byzerllm.prompt()
    def get_all_file_symbols(self, path: str, code: str) -> str:
        """
        你的目标是从给定的代码中获取代码里的符号，需要获取的符号类型包括：

        1. 函数
        2. 类
        3. 变量
        4. 所有导入语句

        如果没有任何符号,返回空字符串就行。
        如果有符号，按如下格式返回:

        ```
        用途：主要用于提供自动实现函数模板的功能。
        {符号类型}: {符号名称}, {符号名称}, ...
        ```

        注意：
        1. 直接输出结果，不要尝试使用任何代码
        2. 不要分析代码的内容和目的
        3. 用途的长度不能超过100字符
        4. 导入语句的分隔符为^^

        一些根据指定条件需要遵守的特殊规则：
        - 当你遇到文件.jsp文件, 导入语句中需要包含 jsp:include 标签中的文件

        下面是一段示例：

        ## 输入
        下列是文件 /test.py 的源码：

        import os
        import time
        from loguru import logger
        import byzerllm

        a = ""

        @byzerllm.prompt(render="jinja")
        def auto_implement_function_template(instruction:str, content:str)->str:

        ## 输出
        用途：主要用于提供自动实现函数模板的功能。
        函数：auto_implement_function_template
        变量：a
        类：
        导入语句：import os^^import time^^from loguru import logger^^import byzerllm

        现在，让我们开始一个新的任务:

        ## 输入
        下列是文件 {{ path }} 的源码：

        {{ code }}

        ## 输出
        """

    @byzerllm.prompt()
    def jsp_get_all_file_symbols(self, path: str, code: str) -> str:
        """
        你的目标是从给定的jsp代码中获取代码里的符号，需要获取的符号类型包括：

        1. 函数
        2. 类
        3. 变量
        4. 所有导入语句

        如果没有任何符号,返回空字符串就行。
        如果有符号，按如下格式返回:

        ```
        用途：主要用于提供自动实现函数模板的功能。
        {符号类型}: {符号名称}, {符号名称}, ...
        ```

        注意：
        1. 直接输出结果，不要尝试使用任何代码
        2. 不要分析代码的内容和目的
        3. 用途的长度不能超过100字符
        4. 导入语句的分隔符为^^
        5. 导入语句中需要包含 jsp:include 整个标签，类似 <jsp:include page="/jspf/prelude.jspf" />
        6. 导入语句中需要包含 form 标签，类似 <form name="ActionPlanLinkedForm" action="/ri/ActionPlanController.do" method="post">
        7. 导入语句中需要包含 有 src 属性的 script 标签。比如 <script language="script" src="xxx">        
        8. 导入语句中需要包含 有 src 属性的 link 标签。 比如 <link rel="stylesheet" type="text/css" href="/ri/ui/styles/xptheme.css">
        9. 导入语句中需要包含 ajax 请求里的url,比如 $.ajax({  
        type : "post",  
        url : "admWorkingDay!updateAdmWorkingDayList.action",  中，那么对应的为 <ajax method="post" url="admWorkingDay!updateAdmWorkingDayList.action">
        10. 导入语句中需要包含超连接，比如 <a href="admRiskLimits!queryAdmRiskLimitsById.action?admRiskLimits.id=${fn:escapeXml(item.id)}">${fn:escapeXml(item.classification)}， 对应的为 <a href="admRiskLimits!queryAdmRiskLimitsById.action"}
        11. 导入语句中需要包含一些js函数里的值，比如 window.onbeforeunload = function()  {
        var actionType = document.ap_ActionPlanForm.action.value;
        if(typeof(window.opener.reloadApCount)!="undefined"&&(actionType&&actionType!='Discard')){
                }
}  对应为 <window.onbeforeunload url="from 表单名字为ap_ActionPlanForm的action的值">

        下面是一段示例：

        ## 输入
        下列是文件 /test.py 的源码：

        import os
        import time
        from loguru import logger
        import byzerllm

        a = ""

        @byzerllm.prompt(render="jinja")
        def auto_implement_function_template(instruction:str, content:str)->str:

        ## 输出
        用途：主要用于提供自动实现函数模板的功能。
        函数：auto_implement_function_template
        变量：a
        类：
        导入语句：import os^^import time^^from loguru import logger^^import byzerllm

        现在，让我们开始一个新的任务:

        ## 输入
        下列是文件 {{ path }} 的源码：

        {{ code }}

        ## 输出
        """

    def split_text_into_chunks(self, text, max_chunk_size=4096):
        lines = text.split("\n")
        chunks = []
        current_chunk = []
        current_length = 0
        for line in lines:
            if current_length + len(line) + 1 <= self.max_input_length:
                current_chunk.append(line)
                current_length += len(line) + 1
            else:
                chunks.append("\n".join(current_chunk))
                current_chunk = [line]
                current_length = len(line) + 1
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        return chunks

    def should_skip(self, file_path: str):
        ext = os.path.splitext(file_path)[1].lower()
        if ext in [".md", ".html", ".txt", ".doc", ".pdf"]:
            return True

        # Check model filter restrictions
        if self.index_model_filter and not self.index_model_filter.is_accessible(file_path):
            self.printer.print_in_terminal(
                "index_file_filtered",
                style="yellow",
                file_path=file_path,
                model_name=",".join(get_llm_names(self.index_llm))
            )
            return True

        return False

    def build_index_for_single_source(self, source: SourceCode):
        global_cancel.check_and_raise(token=self.args.event_file)

        file_path = source.module_name
        if not os.path.exists(file_path):
            return None

        if self.should_skip(file_path):
            return None

        md5 = hashlib.md5(source.source_code.encode("utf-8")).hexdigest()

        model_name = ",".join(get_llm_names(self.index_llm))

        try:
            # 获取模型名称列表
            model_names = get_llm_names(self.index_llm)
            model_name = ",".join(model_names)

            # 获取模型价格信息
            model_info_map = {}
            for name in model_names:
                info = get_model_info(name, self.args.product_mode)
                if info:
                    model_info_map[name] = {
                        "input_price": info.get("input_price", 0.0),
                        "output_price": info.get("output_price", 0.0)
                    }

            start_time = time.monotonic()
            source_code = source.source_code

            # 统计token和成本
            total_input_tokens = 0
            total_output_tokens = 0
            total_input_cost = 0.0
            total_output_cost = 0.0

            if count_tokens(source.source_code) > self.args.conversation_prune_safe_zone_tokens:
                self.printer.print_in_terminal(
                    "index_file_too_large",
                    style="yellow",
                    file_path=source.module_name,
                    file_size=len(source.source_code),
                    max_length=self.args.conversation_prune_safe_zone_tokens
                )
                chunks = self.split_text_into_chunks(
                    source_code, self.max_input_length - 1000
                )
                symbols = []
                for chunk in chunks:
                    meta_holder = byzerllm.MetaHolder()
                    chunk_symbols = self.get_all_file_symbols.with_llm(
                        self.index_llm).with_meta(meta_holder).run(source.module_name, chunk)
                    time.sleep(self.anti_quota_limit)
                    symbols.append(chunk_symbols)

                    if meta_holder.get_meta():
                        meta_dict = meta_holder.get_meta()
                        total_input_tokens += meta_dict.get(
                            "input_tokens_count", 0)
                        total_output_tokens += meta_dict.get(
                            "generated_tokens_count", 0)

                symbols = "\n".join(symbols)
            else:
                meta_holder = byzerllm.MetaHolder()
                ext = os.path.splitext(file_path)[1].lower()
                # 需要有特殊prompt
                if ext == ".jsp":
                    symbols = self.jsp_get_all_file_symbols.with_llm(
                        self.index_llm).with_meta(meta_holder).run(source.module_name, source_code)
                else:
                    symbols = self.get_all_file_symbols.with_llm(
                        self.index_llm).with_meta(meta_holder).run(source.module_name, source_code)

                time.sleep(self.anti_quota_limit)

                if meta_holder.get_meta():
                    meta_dict = meta_holder.get_meta()
                    total_input_tokens += meta_dict.get(
                        "input_tokens_count", 0)
                    total_output_tokens += meta_dict.get(
                        "generated_tokens_count", 0)

            # 计算总成本
            for name in model_names:
                info = model_info_map.get(name, {})
                total_input_cost += (total_input_tokens *
                                     info.get("input_price", 0.0)) / 1000000
                total_output_cost += (total_output_tokens *
                                      info.get("output_price", 0.0)) / 1000000

            # 四舍五入到4位小数
            total_input_cost = round(total_input_cost, 4)
            total_output_cost = round(total_output_cost, 4)

            self.printer.print_in_terminal(
                "index_update_success",
                style="green",
                file_path=file_path,
                md5=md5,
                duration=time.monotonic() - start_time,
                model_name=model_name,
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                input_cost=total_input_cost,
                output_cost=total_output_cost
            )

        except Exception as e:
            # import traceback
            # traceback.print_exc()
            self.printer.print_in_terminal(
                "index_build_error",
                style="red",
                file_path=file_path,
                error=str(e),
                model_name=model_name
            )
            return None

        return {
            "module_name": source.module_name,
            "symbols": symbols,
            "last_modified": os.path.getmtime(file_path),
            "md5": md5,
            "input_tokens_count": total_input_tokens,
            "generated_tokens_count": total_output_tokens,
            "input_tokens_cost": total_input_cost,
            "generated_tokens_cost": total_output_cost
        }

    def parse_exclude_files(self, exclude_files):
        if not exclude_files:
            return []

        if isinstance(exclude_files, str):
            exclude_files = [exclude_files]

        exclude_patterns = []
        for pattern in exclude_files:
            if pattern.startswith("regex://"):
                pattern = pattern[8:]
                exclude_patterns.append(re.compile(pattern))
            elif pattern.startswith("human://"):
                pattern = pattern[8:]
                v = (
                    self.generate_regex_pattern.with_llm(self.llm)
                    .with_extractor(self.extract_regex_pattern)
                    .run(desc=pattern)
                )
                if not v:
                    raise ValueError(
                        "Fail to generate regex pattern, try again.")
                exclude_patterns.append(re.compile(v))
            else:
                raise ValueError(
                    "Invalid exclude_files format. Expected 'regex://<pattern>' or 'human://<description>' "
                )
        return exclude_patterns

    def filter_exclude_files(self, file_path, exclude_patterns):
        # 增加 ignore_file_utils 的过滤
        try:
            from autocoder.common.ignorefiles import ignore_file_utils
            if ignore_file_utils.should_ignore(file_path):
                return True
        except Exception:
            pass

        for pattern in exclude_patterns:
            if pattern.search(file_path):
                return True
        return False

    def build_index(self):
        if os.path.exists(self.index_file):
            with open(self.index_file, "r", encoding="utf-8") as file:
                index_data = json.load(file)
        else:
            index_data = {}

        # 清理已不存在的文件索引
        keys_to_remove = []
        for file_path in index_data:
            if not os.path.exists(file_path):
                keys_to_remove.append(file_path)

        # 删除被排除的文件
        exclude_patterns = []
        try:
            exclude_patterns = self.parse_exclude_files(
                self.args.exclude_files)
            for file_path in index_data:
                if self.filter_exclude_files(file_path, exclude_patterns):
                    keys_to_remove.append(file_path)
        except Exception as e:
            self.printer.print_in_terminal(
                "index_exclude_files_error",
                style="red",
                error=str(e)
            )            

        # 删除无效条目并记录日志
        for key in set(keys_to_remove):
            if key in index_data:
                del index_data[key]
                self.printer.print_in_terminal(
                    "index_file_removed",
                    style="yellow",
                    file_path=key
                )

        updated_sources = []

        total_input_tokens = 0
        total_output_tokens = 0
        total_input_cost = 0.0
        total_output_cost = 0.0

        with ThreadPoolExecutor(max_workers=self.args.index_build_workers) as executor:

            wait_to_build_files = []
            for source in self.sources:
                file_path = source.module_name
                if not os.path.exists(file_path):
                    continue

                if self.should_skip(file_path):
                    continue

                if self.filter_exclude_files(file_path, exclude_patterns):
                    continue

                source_code = source.source_code
                if self.args.auto_merge == "strict_diff":
                    v = source.source_code.splitlines()
                    new_v = []
                    for line in v:
                        new_v.append(line[line.find(":"):])
                    source_code = "\n".join(new_v)

                md5 = hashlib.md5(source_code.encode("utf-8")).hexdigest()
                if (
                    source.module_name not in index_data
                    or index_data[source.module_name]["md5"] != md5
                ):
                    wait_to_build_files.append(source)

            # Remove duplicates based on module_name
            wait_to_build_files = list(
                {source.module_name: source for source in wait_to_build_files}.values())

            counter = 0
            num_files = len(wait_to_build_files)
            total_files = len(self.sources)
            self.printer.print_in_terminal(
                "index_build_summary",
                style="bold blue",
                total_files=total_files,
                num_files=num_files
            )

            get_event_manager(self.args.event_file).write_result(
                EventContentCreator.create_result(
                    content=EventContentCreator.IndexBuildStartContent(
                        file_number=num_files,
                        total_files=total_files
                    ).to_dict(),
                    metadata={
                        "stream_out_type": IndexStreamOutType.INDEX_BUILD.value,
                        "action_file": self.args.file
                    }
                )
            )

            futures = [
                executor.submit(self.build_index_for_single_source, source)
                for source in wait_to_build_files
            ]
            for future in as_completed(futures):
                global_cancel.check_and_raise(token=self.args.event_file)
                result = future.result()
                if result is not None:
                    counter += 1
                    self.printer.print_in_terminal(
                        "building_index_progress",
                        style="blue",
                        counter=counter,
                        num_files=num_files
                    )
                    module_name = result["module_name"]
                    total_input_tokens += result["input_tokens_count"]
                    total_output_tokens += result["generated_tokens_count"]
                    total_input_cost += result["input_tokens_cost"]
                    total_output_cost += result["generated_tokens_cost"]
                    index_data[module_name] = result
                    updated_sources.append(module_name)
                    if len(updated_sources) > 5:
                        with open(self.index_file, "w", encoding="utf-8") as file:
                            json.dump(index_data, file,
                                      ensure_ascii=False, indent=2)
                        updated_sources = []

        # 如果 updated_sources 或 keys_to_remove 有值，则保存索引文件
        if updated_sources or keys_to_remove:
            with open(self.index_file, "w", encoding="utf-8") as file:
                json.dump(index_data, file, ensure_ascii=False, indent=2)

            print("")
            self.printer.print_in_terminal(
                "index_file_saved",
                style="green",
                updated_files=len(updated_sources),
                removed_files=len(keys_to_remove),
                input_tokens=total_input_tokens,
                output_tokens=total_output_tokens,
                input_cost=total_input_cost,
                output_cost=total_output_cost
            )
            print("")

            # 记录索引构建完成事件                            
            get_event_manager(self.args.event_file).write_result(
                EventContentCreator.create_result(
                    content=EventContentCreator.IndexBuildEndContent(
                        updated_files=len(updated_sources),
                        removed_files=len(keys_to_remove),
                        input_tokens=total_input_tokens,
                        output_tokens=total_output_tokens,
                        input_cost=total_input_cost,
                        output_cost=total_output_cost
                    ).to_dict(),
                    metadata={}
                    ).to_dict(),
                    metadata={
                        "stream_out_type": IndexStreamOutType.INDEX_BUILD.value,
                        "action_file": self.args.file
                    }
                )            
        return index_data

    def read_index_as_str(self):
        if not os.path.exists(self.index_file):
            return []

        with open(self.index_file, "r", encoding="utf-8") as file:
            return file.read()

    def read_index(self) -> List[IndexItem]:
        if not os.path.exists(self.index_file):
            return []

        with open(self.index_file, "r", encoding="utf-8") as file:
            index_data = json.load(file)

        index_items = []
        for module_name, data in index_data.items():
            try:                                
                index_item = IndexItem(
                    module_name=module_name,
                    symbols=data["symbols"],
                    last_modified=data["last_modified"],
                    md5=data["md5"],
                )
                index_items.append(index_item)
            except Exception as e:
                logger.warning(f"处理索引条目 {module_name} 时出错: {str(e)}")
                logger.exception(e)
                continue

        return index_items

    def _get_meta_str(
        self,
        max_chunk_size=4096,
        skip_symbols: bool = False,
        includes: Optional[List[SymbolType]] = None,
    ):
        index_items = self.read_index()
        current_chunk = []
        current_size = 0

        if max_chunk_size == -1:
            for item in index_items:
                symbols_str = item.symbols
                if includes:
                    symbol_info = extract_symbols(symbols_str)
                    symbols_str = symbols_info_to_str(symbol_info, includes)

                item_str = f"##{item.module_name}\n{symbols_str}\n\n"

                if skip_symbols:
                    item_str = f"{item.module_name}\n"

                if len(current_chunk) > self.args.filter_batch_size:
                    yield "".join(current_chunk)
                    current_chunk = [item_str]
                else:
                    current_chunk.append(item_str)

            if current_chunk:
                yield "".join(current_chunk)
        else:
            for item in index_items:
                symbols_str = item.symbols
                if includes:
                    symbol_info = extract_symbols(symbols_str)
                    symbols_str = symbols_info_to_str(symbol_info, includes)

                item_str = f"##{item.module_name}\n{symbols_str}\n\n"

                if skip_symbols:
                    item_str = f"{item.module_name}\n"
                item_size = len(item_str)

                if current_size + item_size > max_chunk_size:
                    yield "".join(current_chunk)
                    current_chunk = [item_str]
                    current_size = item_size
                else:
                    current_chunk.append(item_str)
                    current_size += item_size

            if current_chunk:
                yield "".join(current_chunk)

    def get_related_files(self, file_paths: List[str]):
        all_results = []
        lock = threading.Lock()

        def process_chunk(chunk, chunk_count):
            result = self._get_related_files.with_llm(self.llm).with_return_type(
                FileList).run(chunk, "\n".join(file_paths))
            if result is not None:
                with lock:
                    all_results.extend(result.file_list)
            else:
                self.printer.print_in_terminal(
                    "index_related_files_fail",
                    style="yellow",
                    chunk_count=chunk_count
                )
            time.sleep(self.args.anti_quota_limit)

        with ThreadPoolExecutor(max_workers=self.args.index_filter_workers) as executor:
            futures = []
            chunk_count = 0
            for chunk in self._get_meta_str(
                max_chunk_size=-1
            ):
                future = executor.submit(process_chunk, chunk, chunk_count)
                futures.append(future)
                chunk_count += 1

            for future in as_completed(futures):
                future.result()

        all_results = list(
            {file.file_path: file for file in all_results}.values())
        return FileList(file_list=all_results)

    def _query_index_with_thread(self, query, func):
        all_results = []
        lock = threading.Lock()
        completed_threads = 0
        total_threads = 0

        def process_chunk(chunk):
            nonlocal completed_threads
            result = self._get_target_files_by_query.with_llm(
                self.llm).with_return_type(FileList).run(chunk, query)

            if result is not None:
                with lock:
                    all_results.extend(result.file_list)
                    completed_threads += 1
            else:
                self.printer.print_in_terminal(
                    "index_related_files_fail",
                    style="yellow",
                    chunk_count="unknown"
                )
            time.sleep(self.args.anti_quota_limit)

        with ThreadPoolExecutor(max_workers=self.args.index_filter_workers) as executor:
            futures = []
            for chunk in func():
                future = executor.submit(process_chunk, chunk)
                futures.append(future)
                total_threads += 1

            for future in as_completed(futures):
                future.result()

        self.printer.print_in_terminal(
            "index_threads_completed",
            style="green",
            completed_threads=completed_threads,
            total_threads=total_threads
        )
        return all_results, total_threads, completed_threads

    def get_target_files_by_query(self, query: str) -> FileList:
        '''
        根据用户查询过滤文件。
        1. 必选，根据文件名和路径，以及文件用途说明，过滤出相关文件。
        2. index_filter_level>=1，根据文件名和路径，文件说明以及符号列表过滤出相关文件。
        '''
        all_results: List[TargetFile] = []
        if self.args.index_filter_level == 0:
            def w():
                return self._get_meta_str(
                    skip_symbols=False,
                    max_chunk_size=-1,
                    includes=[SymbolType.USAGE],
                )

            temp_result, total_threads, completed_threads = self._query_index_with_thread(
                query, w)
            all_results.extend(temp_result)

        if self.args.index_filter_level >= 1:

            def w():
                return self._get_meta_str(
                    skip_symbols=False, max_chunk_size=-1
                )

            temp_result, total_threads, completed_threads = self._query_index_with_thread(
                query, w)
            all_results.extend(temp_result)

        all_results = list(
            {file.file_path: file for file in all_results}.values())
        # Limit the number of files based on index_filter_file_num
        limited_results = all_results[: self.args.index_filter_file_num]
        return FileList(file_list=limited_results)

    @byzerllm.prompt()
    def _get_target_files_by_query(self, indices: str, query: str) -> str:
        """
        下面是已知文件以及对应的符号信息：

        {{ indices }}

        用户的问题是：

        {{ query }}

        现在，请根据用户的问题以及前面的文件和符号信息，寻找相关文件路径。返回结果按如下格式：        

        ```json
        {
            "file_list": [
                {
                    "file_path": "path/to/file1.py",
                    "reason": "这是被选择的原因（不超过10个中文字符）"
                },
                {
                    "file_path": "path/to/file2.py",
                    "reason": "这是被选择的原因（不超过10个中文字符）"
                }
            ]
        }
        ```

        如果没有找到，返回如下 json 即可：

        ```json
            {"file_list": []}
        ```

        请严格遵循以下步骤：

        1. 识别特殊标记：
           - 查找query中的 `@` 符号，它后面的内容是用户关注的文件路径。
           - 查找query中的 `@@` 符号，它后面的内容是用户关注的符号（如函数名、类名、变量名）。

        2. 匹配文件路径：
           - 对于 `@` 标记，在indices中查找包含该路径的所有文件。
           - 路径匹配应该是部分匹配，因为用户可能只提供了路径的一部分。

        3. 匹配符号：
           - 对于 `@@` 标记，在indices中所有文件的符号信息中查找该符号。
           - 检查函数、类、变量等所有符号类型。

        4. 分析依赖关系：
           - 利用 "导入语句" 信息确定文件间的依赖关系。
           - 如果找到了相关文件，也包括与之直接相关的依赖文件。

        5. 考虑文件用途：
           - 使用每个文件的 "用途" 信息来判断其与查询的相关性。 

        6. 按格式要求返回结果

        请确保结果的准确性和完整性，包括所有可能相关的文件。
        """
