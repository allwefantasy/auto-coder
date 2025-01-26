import os
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from autocoder.common import SourceCode, AutoCoderArgs
from autocoder.index.symbols_utils import (
    extract_symbols,
    SymbolsInfo,
    SymbolType,
    symbols_info_to_str,
)
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import pydantic
import byzerllm
import hashlib
import textwrap
import tabulate
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from loguru import logger
from autocoder.utils.queue_communicate import (
    queue_communicate,
    CommunicateEvent,
    CommunicateEventType,
)
from autocoder.index.types import (
    IndexItem,
    TargetFile,
    VerifyFileRelevance,
    FileList,
)


class IndexManager:
    def __init__(
        self, llm: byzerllm.ByzerLLM, sources: List[SourceCode], args: AutoCoderArgs
    ):
        self.sources = sources
        self.source_dir = args.source_dir
        self.anti_quota_limit = (
            args.index_model_anti_quota_limit or args.anti_quota_limit
        )
        self.index_dir = os.path.join(self.source_dir, ".auto-coder")
        self.index_file = os.path.join(self.index_dir, "index.json")
        if llm and (s := llm.get_sub_client("index_model")):
            self.index_llm = s
        else:
            self.index_llm = llm

        self.llm = llm
        self.args = args
        self.max_input_length = (
            args.index_model_max_input_length or args.model_max_input_length
        )

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
        {符号类型}: {符号名称}, {符号名称}, ...
        ```

        注意：
        1. 直接输出结果，不要尝试使用任何代码
        2. 不要分析代码的内容和目的
        3. 用途的长度不能超过100字符
        4. 导入语句的分隔符为^^

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
        return False

    def build_index_for_single_source(self, source: SourceCode):
        file_path = source.module_name
        if not os.path.exists(file_path):
            return None

        if self.should_skip(file_path):
            return None

        md5 = hashlib.md5(source.source_code.encode("utf-8")).hexdigest()

        try:
            start_time = time.monotonic()
            source_code = source.source_code
            if len(source.source_code) > self.max_input_length:
                logger.warning(
                    f"Warning[Build Index]: The length of source code({source.module_name}) is too long ({len(source.source_code)}) > model_max_input_length({self.max_input_length}), splitting into chunks..."
                )
                chunks = self.split_text_into_chunks(
                    source_code, self.max_input_length - 1000
                )
                symbols = []
                for chunk in chunks:
                    chunk_symbols = self.get_all_file_symbols.with_llm(
                        self.index_llm).run(source.module_name, chunk)
                    time.sleep(self.anti_quota_limit)
                    symbols.append(chunk_symbols)
                symbols = "\n".join(symbols)
            else:
                symbols = self.get_all_file_symbols.with_llm(
                    self.index_llm).run(source.module_name, source_code)
                time.sleep(self.anti_quota_limit)

            logger.info(
                f"Parse and update index for {file_path} md5: {md5} took {time.monotonic() - start_time:.2f}s"
            )

        except Exception as e:
            logger.warning(f"Error: {e}")
            return None

        return {
            "module_name": source.module_name,
            "symbols": symbols,
            "last_modified": os.path.getmtime(file_path),
            "md5": md5,
        }

    def build_index(self):
        if os.path.exists(self.index_file):
            with open(self.index_file, "r") as file:
                index_data = json.load(file)
        else:
            index_data = {}

        @byzerllm.prompt()
        def error_message(source_dir: str, file_path: str):
            """
            The source_dir is different from the path in index file (e.g. file_path:{{ file_path }} source_dir:{{ source_dir }}).
            You may need to replace the prefix with the source_dir in the index file or Just delete the index file to rebuild it.
            """

        for item in index_data.keys():
            if not item.startswith(self.source_dir):
                logger.warning(
                    error_message(source_dir=self.source_dir, file_path=item)
                )
                break

        updated_sources = []

        with ThreadPoolExecutor(max_workers=self.args.index_build_workers) as executor:

            wait_to_build_files = []
            for source in self.sources:
                file_path = source.module_name
                if not os.path.exists(file_path):
                    continue

                if self.should_skip(file_path):
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

            counter = 0
            num_files = len(wait_to_build_files)
            total_files = len(self.sources)
            logger.info(
                f"Total Files: {total_files}, Need to Build Index: {num_files}")

            futures = [
                executor.submit(self.build_index_for_single_source, source)
                for source in wait_to_build_files
            ]
            for future in as_completed(futures):
                result = future.result()
                if result is not None:
                    counter += 1
                    logger.info(f"Building Index:{counter}/{num_files}...")
                    module_name = result["module_name"]
                    index_data[module_name] = result
                    updated_sources.append(module_name)

        if updated_sources:
            with open(self.index_file, "w") as file:
                json.dump(index_data, file, ensure_ascii=False, indent=2)

        return index_data

    def read_index_as_str(self):
        if not os.path.exists(self.index_file):
            return []

        with open(self.index_file, "r") as file:
            return file.read()

    def read_index(self) -> List[IndexItem]:
        if not os.path.exists(self.index_file):
            return []

        with open(self.index_file, "r") as file:
            index_data = json.load(file)

        index_items = []
        for module_name, data in index_data.items():
            index_item = IndexItem(
                module_name=module_name,
                symbols=data["symbols"],
                last_modified=data["last_modified"],
                md5=data["md5"],
            )
            index_items.append(index_item)

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
                logger.warning(
                    f"Fail to find related files for chunk {chunk_count}. This may be caused by the model limit or the query not being suitable for the files."
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
                logger.warning(
                    f"Fail to find target files for chunk. This is caused by the model response not being in JSON format or the JSON being empty."
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

        logger.info(f"Completed {completed_threads}/{total_threads} threads")
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


def build_index_and_filter_files(
    llm, args: AutoCoderArgs, sources: List[SourceCode]
) -> str:
    # Initialize timing and statistics
    total_start_time = time.monotonic()
    stats = {
        "total_files": len(sources),
        "indexed_files": 0,
        "level1_filtered": 0,
        "level2_filtered": 0,
        "verified_files": 0,
        "final_files": 0,
        "timings": {
            "process_tagged_sources": 0.0,
            "build_index": 0.0,
            "level1_filter": 0.0,
            "level2_filter": 0.0,
            "relevance_verification": 0.0,
            "file_selection": 0.0,
            "prepare_output": 0.0,
            "total": 0.0
        }
    }

    def get_file_path(file_path):
        if file_path.startswith("##"):
            return file_path.strip()[2:]
        return file_path

    final_files: Dict[str, TargetFile] = {}

    # Phase 1: Process REST/RAG/Search sources
    logger.info("Phase 1: Processing REST/RAG/Search sources...")
    phase_start = time.monotonic()
    for source in sources:
        if source.tag in ["REST", "RAG", "SEARCH"]:
            final_files[get_file_path(source.module_name)] = TargetFile(
                file_path=source.module_name, reason="Rest/Rag/Search"
            )
    phase_end = time.monotonic()
    stats["timings"]["process_tagged_sources"] = phase_end - phase_start

    if not args.skip_build_index and llm:
        # Phase 2: Build index
        if args.request_id and not args.skip_events:
            queue_communicate.send_event(
                request_id=args.request_id,
                event=CommunicateEvent(
                    event_type=CommunicateEventType.CODE_INDEX_BUILD_START.value,
                    data=json.dumps({"total_files": len(sources)})
                )
            )

        logger.info("Phase 2: Building index for all files...")
        phase_start = time.monotonic()
        index_manager = IndexManager(llm=llm, sources=sources, args=args)
        index_data = index_manager.build_index()
        stats["indexed_files"] = len(index_data) if index_data else 0
        phase_end = time.monotonic()
        stats["timings"]["build_index"] = phase_end - phase_start

        if args.request_id and not args.skip_events:
            queue_communicate.send_event(
                request_id=args.request_id,
                event=CommunicateEvent(
                    event_type=CommunicateEventType.CODE_INDEX_BUILD_END.value,
                    data=json.dumps({
                        "indexed_files": stats["indexed_files"],
                        "build_index_time": stats["timings"]["build_index"],
                    })
                )
            )

        if not args.skip_filter_index:
            if args.request_id and not args.skip_events:
                queue_communicate.send_event(
                    request_id=args.request_id,
                    event=CommunicateEvent(
                        event_type=CommunicateEventType.CODE_INDEX_FILTER_START.value,
                        data=json.dumps({})
                    )
                )
            # Phase 3: Level 1 filtering - Query-based
            logger.info(
                "Phase 3: Performing Level 1 filtering (query-based)...")

            phase_start = time.monotonic()
            target_files = index_manager.get_target_files_by_query(args.query)

            if target_files:
                for file in target_files.file_list:
                    file_path = file.file_path.strip()
                    final_files[get_file_path(file_path)] = file
                stats["level1_filtered"] = len(target_files.file_list)
            phase_end = time.monotonic()
            stats["timings"]["level1_filter"] = phase_end - phase_start

            # Phase 4: Level 2 filtering - Related files
            if target_files is not None and args.index_filter_level >= 2:
                logger.info(
                    "Phase 4: Performing Level 2 filtering (related files)...")
                if args.request_id and not args.skip_events:
                    queue_communicate.send_event(
                        request_id=args.request_id,
                        event=CommunicateEvent(
                            event_type=CommunicateEventType.CODE_INDEX_FILTER_START.value,
                            data=json.dumps({})
                        )
                    )
                phase_start = time.monotonic()
                related_files = index_manager.get_related_files(
                    [file.file_path for file in target_files.file_list]
                )
                if related_files is not None:
                    for file in related_files.file_list:
                        file_path = file.file_path.strip()
                        final_files[get_file_path(file_path)] = file
                    stats["level2_filtered"] = len(related_files.file_list)
                phase_end = time.monotonic()
                stats["timings"]["level2_filter"] = phase_end - phase_start

            if not final_files:
                logger.warning("No related files found, using all files")
                for source in sources:
                    final_files[get_file_path(source.module_name)] = TargetFile(
                        file_path=source.module_name,
                        reason="No related files found, use all files",
                    )

            # Phase 5: Relevance verification
            logger.info("Phase 5: Performing relevance verification...")
            if args.index_filter_enable_relevance_verification:
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
                    for source in sources:
                        if source.module_name == file.file_path:
                            file_content = source.source_code
                            try:
                                result = index_manager.verify_file_relevance.with_llm(llm).with_return_type(VerifyFileRelevance).run(
                                    file_content=file_content,
                                    query=args.query
                                )
                                if result.relevant_score >= args.verify_file_relevance_score:
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

                with ThreadPoolExecutor(max_workers=args.index_filter_workers) as executor:
                    futures = [executor.submit(verify_single_file, file)
                            for file in temp_files]
                    for future in as_completed(futures):
                        result = future.result()
                        if result:
                            verification_results.append(result)
                            time.sleep(args.anti_quota_limit)

                # Print verification results in a table
                print_verification_results(verification_results)
                
                stats["verified_files"] = len(verified_files)
                phase_end = time.monotonic()
                stats["timings"]["relevance_verification"] = phase_end - phase_start

                # Keep all files, not just verified ones
                final_files = verified_files

    def display_table_and_get_selections(data):
        from prompt_toolkit.shortcuts import checkboxlist_dialog
        from prompt_toolkit.styles import Style

        choices = [(file, f"{file} - {reason}") for file, reason in data]
        selected_files = [file for file, _ in choices]

        style = Style.from_dict(
            {
                "dialog": "bg:#88ff88",
                "dialog frame.label": "bg:#ffffff #000000",
                "dialog.body": "bg:#88ff88 #000000",
                "dialog shadow": "bg:#00aa00",
            }
        )

        result = checkboxlist_dialog(
            title="Target Files",
            text="Tab to switch between buttons, and Space/Enter to select/deselect.",
            values=choices,
            style=style,
            default_values=selected_files,
        ).run()

        return [file for file in result] if result else []

    def print_selected(data):
        console = Console()

        table = Table(
            title="Files Used as Context",
            show_header=True,
            header_style="bold magenta",
        )
        table.add_column("File Path", style="cyan", no_wrap=True)
        table.add_column("Reason", style="green")

        for file, reason in data:
            table.add_row(file, reason)

        panel = Panel(
            table,
            expand=False,
            border_style="bold blue",
            padding=(1, 1),
        )

        console.print(panel)

    # Phase 6: File selection and limitation
    logger.info("Phase 6: Processing file selection and limits...")
    phase_start = time.monotonic()

    if args.index_filter_file_num > 0:
        logger.info(
            f"Limiting files from {len(final_files)} to {args.index_filter_file_num}")

    if args.skip_confirm:
        final_filenames = [file.file_path for file in final_files.values()]
        if args.index_filter_file_num > 0:
            final_filenames = final_filenames[: args.index_filter_file_num]
    else:
        target_files_data = [
            (file.file_path, file.reason) for file in final_files.values()
        ]
        if not target_files_data:
            logger.warning(
                "No target files found, you may need to rewrite the query and try again."
            )
            final_filenames = []
        else:
            final_filenames = display_table_and_get_selections(
                target_files_data)

        if args.index_filter_file_num > 0:
            final_filenames = final_filenames[: args.index_filter_file_num]

    phase_end = time.monotonic()
    stats["timings"]["file_selection"] = phase_end - phase_start

    # Phase 7: Display results and prepare output
    logger.info("Phase 7: Preparing final output...")
    phase_start = time.monotonic()    
    try:
        print_selected(
            [
                (file.file_path, file.reason)
                for file in final_files.values()
                if file.file_path in final_filenames
            ]
        )
    except Exception as e:
        logger.warning(
            "Failed to display selected files in terminal mode. Falling back to simple print."
        )
        print("Target Files Selected:")
        for file in final_filenames:
            print(f"{file} - {final_files[file].reason}")

    source_code = ""
    depulicated_sources = set()

    for file in sources:
        if file.module_name in final_filenames:
            if file.module_name in depulicated_sources:
                continue
            depulicated_sources.add(file.module_name)
            source_code += f"##File: {file.module_name}\n"
            source_code += f"{file.source_code}\n\n"

    if args.request_id and not args.skip_events:
        queue_communicate.send_event(
            request_id=args.request_id,
            event=CommunicateEvent(
                event_type=CommunicateEventType.CODE_INDEX_FILTER_FILE_SELECTED.value,
                data=json.dumps([
                    (file.file_path, file.reason)
                    for file in final_files.values()
                    if file.file_path in depulicated_sources
                ])
            )
        )        

    stats["final_files"] = len(depulicated_sources)
    phase_end = time.monotonic()
    stats["timings"]["prepare_output"] = phase_end - phase_start

    # Calculate total time and print summary
    total_end_time = time.monotonic()
    total_time = total_end_time - total_start_time
    stats["timings"]["total"] = total_time
    
    # Calculate total filter time
    total_filter_time = (
        stats["timings"]["level1_filter"] +
        stats["timings"]["level2_filter"] +
        stats["timings"]["relevance_verification"]
    )

    # Print final statistics in a more structured way
    summary = f"""
=== Indexing and Filtering Summary ===
• Total files scanned: {stats['total_files']}
• Files indexed: {stats['indexed_files']}
• Files filtered:
  - Level 1 (query-based): {stats['level1_filtered']}
  - Level 2 (related files): {stats['level2_filtered']}
  - Relevance verified: {stats.get('verified_files', 0)}
• Final files selected: {stats['final_files']}

=== Time Breakdown ===
• Index build: {stats['timings'].get('build_index', 0):.2f}s
• Level 1 filter: {stats['timings'].get('level1_filter', 0):.2f}s
• Level 2 filter: {stats['timings'].get('level2_filter', 0):.2f}s
• Relevance check: {stats['timings'].get('relevance_verification', 0):.2f}s
• File selection: {stats['timings'].get('file_selection', 0):.2f}s
• Total time: {total_time:.2f}s
====================================
"""
    logger.info(summary)

    if args.request_id and not args.skip_events:
        queue_communicate.send_event(
            request_id=args.request_id,
            event=CommunicateEvent(
                event_type=CommunicateEventType.CODE_INDEX_FILTER_END.value,
                data=json.dumps({
                    "filtered_files": stats["final_files"],
                    "filter_time": total_filter_time
                })
            )
        )

    return source_code
