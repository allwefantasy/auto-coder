import os
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from autocoder.common import SourceCode, AutoCoderArgs

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from autocoder.common.printer import Printer
from autocoder.events.event_types import EventMetadata
from autocoder.utils.queue_communicate import (
    queue_communicate,
    CommunicateEvent,
    CommunicateEventType,
)
from autocoder.index.types import (
    TargetFile
)

from autocoder.index.filter.quick_filter import QuickFilter
from autocoder.index.filter.normal_filter import NormalFilter
from autocoder.index.index import IndexManager
from loguru import logger
from autocoder.common import SourceCodeList
from autocoder.common.context_pruner import PruneContext
from autocoder.common.action_yml_file_manager import ActionYmlFileManager

from autocoder.events.event_manager_singleton import get_event_manager
from autocoder.events import event_content as EventContentCreator
from autocoder.agent.agentic_filter import AgenticFilter


def build_index_and_filter_files(
    llm, args: AutoCoderArgs, sources: List[SourceCode]
) -> SourceCodeList:

    action_yml_file_manager = ActionYmlFileManager(args.source_dir)
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
            "quick_filter": 0.0,
            "normal_filter": {
                "level1_filter": 0.0,
                "level2_filter": 0.0,
                "relevance_verification": 0.0,
            },
            "file_selection": 0.0,
            "prepare_output": 0.0,
            "total": 0.0
        }
    }

    def get_file_path(file_path):
        if file_path.startswith("##"):
            return file_path.strip()[2:]
        return file_path

    # 文件路径 -> TargetFile
    final_files: Dict[str, TargetFile] = {}

    # 文件路径 -> 文件在文件列表中的位置（越前面表示越相关）
    file_positions: Dict[str, int] = {}

    # Phase 1: Process REST/RAG/Search sources
    printer = Printer()
    printer.print_in_terminal("phase1_processing_sources")
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
        printer.print_in_terminal("phase2_building_index")
        phase_start = time.monotonic()
        index_manager = IndexManager(llm=llm, sources=sources, args=args)
        index_data = index_manager.build_index()
        stats["indexed_files"] = len(index_data) if index_data else 0
        phase_end = time.monotonic()
        stats["timings"]["build_index"] = phase_end - phase_start

        if not args.skip_filter_index and args.index_filter_model:

            model_name = getattr(
                index_manager.index_filter_llm, 'default_model_name', None)
            if not model_name:
                model_name = "unknown(without default model name)"

            if args.enable_agentic_filter:
                from autocoder.agent.agentic_filter import AgenticFilterRequest, AgenticFilter, CommandConfig, MemoryConfig
                from autocoder.common.conf_utils import load_memory

                _memory = load_memory(args)

                def save_memory_func():
                    pass

                tuner = AgenticFilter(index_manager.index_filter_llm,
                                      args=args,
                                      conversation_history=[],
                                      memory_config=MemoryConfig(
                                          memory=_memory, save_memory_func=save_memory_func),
                                      command_config=None)
                response = tuner.analyze(
                    AgenticFilterRequest(user_input=args.query))
                if response:
                    print("收集文件。。。。。。")
                    print(response)
                    for file in response.files:
                        final_files[file.path] = TargetFile(
                            file_path=file.path, reason="Agentic Filter")
            else:
                printer.print_in_terminal(
                    "quick_filter_start", style="blue", model_name=model_name)

                quick_filter = QuickFilter(index_manager, stats, sources)
                quick_filter_result = quick_filter.filter(
                    index_manager.read_index(), args.query)

                final_files.update(quick_filter_result.files)

                if quick_filter_result.file_positions:
                    file_positions.update(quick_filter_result.file_positions)

        if not args.skip_filter_index and not args.index_filter_model:
            model_name = getattr(index_manager.llm, 'default_model_name', None)
            if not model_name:
                model_name = "unknown(without default model name)"
            printer.print_in_terminal(
                "normal_filter_start", style="blue", model_name=model_name)
            normal_filter = NormalFilter(index_manager, stats, sources)
            normal_filter_result = normal_filter.filter(
                index_manager.read_index(), args.query)
            # Merge normal filter results into final_files
            final_files.update(normal_filter_result.files)

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

    def shorten_path(path: str, keep_levels: int = 3) -> str:
        """
        优化长路径显示，保留最后指定层级
        示例：/a/b/c/d/e/f.py -> .../c/d/e/f.py
        """
        parts = path.split(os.sep)
        if len(parts) > keep_levels:
            return ".../" + os.sep.join(parts[-keep_levels:])
        return path

    def print_selected(data):
        console = Console()

        # 获取终端宽度
        console_width = console.width

        table = Table(
            title="Files Used as Context",
            show_header=True,
            header_style="bold magenta",
            # 设置表格最大宽度为终端宽度（留 10 字符边距）
            width=min(console_width - 10, 120),
            expand=True
        )

        # 优化列配置
        table.add_column("File Path",
                         style="cyan",
                         # 分配 60% 宽度给文件路径
                         width=int((console_width - 10) * 0.6),
                         overflow="fold",  # 自动折叠过长的路径
                         no_wrap=False)  # 允许换行

        table.add_column("Reason",
                         style="green",
                         width=int((console_width - 10) * 0.4),  # 分配 40% 宽度给原因
                         no_wrap=False)

        # 添加处理过的文件路径
        for file, reason in data:
            # 路径截取优化：保留最后 3 级路径
            processed_path = shorten_path(file, keep_levels=3)
            table.add_row(processed_path, reason)

        panel = Panel(
            table,
            expand=False,
            border_style="bold blue",
            padding=(1, 1),
        )

        console.print(panel)

    # Phase 6: File selection and limitation
    printer.print_in_terminal("phase6_file_selection")
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
    printer.print_in_terminal("phase7_preparing_output")
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

    # source_code = ""
    source_code_list = SourceCodeList(sources=[])
    depulicated_sources = set()

    # 先去重
    temp_sources = []
    for file in sources:
        if file.module_name in final_filenames:
            if file.module_name in depulicated_sources:
                continue
            depulicated_sources.add(file.module_name)
            # source_code += f"##File: {file.module_name}\n"
            # source_code += f"{file.source_code}\n\n"
            temp_sources.append(file)

    # 开启了裁剪，则需要做裁剪，不过目前只针对 quick filter 生效
    if args.context_prune:
        context_pruner = PruneContext(
            max_tokens=args.conversation_prune_safe_zone_tokens, args=args, llm=llm)
        # 如果 file_positions 不为空，则通过 file_positions 来获取文件
        if file_positions:
            # 拿到位置列表，然后根据位置排序 得到 [(pos,file_path)]
            # 将 [(pos,file_path)] 转换为 [file_path]
            # 通过 [file_path] 顺序调整 temp_sources 的顺序
            # MARK
            # 将 file_positions 转换为 [(pos, file_path)] 的列表
            position_file_pairs = [(pos, file_path)
                                   for file_path, pos in file_positions.items()]
            # 按位置排序
            position_file_pairs.sort(key=lambda x: x[0])
            # 提取排序后的文件路径列表
            sorted_file_paths = [file_path for _,
                                 file_path in position_file_pairs]
            # 根据 sorted_file_paths 重新排序 temp_sources
            temp_sources.sort(key=lambda x: sorted_file_paths.index(
                x.module_name) if x.module_name in sorted_file_paths else len(sorted_file_paths))

        pruned_files = context_pruner.handle_overflow(
            temp_sources, [{"role": "user", "content": args.query}], args.context_prune_strategy)
        source_code_list.sources = pruned_files

    stats["final_files"] = len(source_code_list.sources)
    phase_end = time.monotonic()
    stats["timings"]["prepare_output"] = phase_end - phase_start

    # Calculate total time and print summary
    total_end_time = time.monotonic()
    total_time = total_end_time - total_start_time
    stats["timings"]["total"] = total_time

    # Calculate total filter time
    total_filter_time = (
        stats["timings"]["quick_filter"] +
        stats["timings"]["normal_filter"]["level1_filter"] +
        stats["timings"]["normal_filter"]["level2_filter"] +
        stats["timings"]["normal_filter"]["relevance_verification"]
    )

    # Print final statistics in a more structured way
    summary = f"""
=== File Stat ===    
• Total files scanned: {stats['total_files']}
• Files indexed: {stats['indexed_files']}
• Files filtered:
  - Level 1 (query-based): {stats['level1_filtered']}
  - Level 2 (related files): {stats['level2_filtered']}
  - Relevance verified: {stats.get('verified_files', 0)}
• Final files selected: {stats['final_files']}

=== Time Stat ===
• Index build: {stats['timings'].get('build_index', 0):.2f}s
• Quick filter: {stats['timings'].get('quick_filter', 0):.2f}s
• Normal filter: 
    - Level 1 filter: {stats['timings']["normal_filter"].get('level1_filter', 0):.2f}s
    - Level 2 filter: {stats['timings']["normal_filter"].get('level2_filter', 0):.2f}s
    - Relevance check: {stats['timings']["normal_filter"].get('relevance_verification', 0):.2f}s
• File selection: {stats['timings'].get('file_selection', 0):.2f}s
• Total time: {total_time:.2f}s

"""
    # printer.print_panel(
    #     summary,
    #     text_options={"justify": "left", "style": "bold white"},
    #     panel_options={
    #         "title": "Indexing and Filtering Summary",
    #         "border_style": "bold blue",
    #         "padding": (1, 2),
    #         "expand": False
    #     }
    # )

    get_event_manager(args.event_file).write_result(
        EventContentCreator.create_result(
            content=EventContentCreator.ResultContextUsedContent(
                files=final_filenames,
                title="Files Used as Context",
                description=""
            ).to_dict()
        ),
        metadata=EventMetadata(
            action_file=args.file
        ).to_dict()
    )

    if args.file:
        action_file_name = os.path.basename(args.file)
        dynamic_urls = []

        for file in source_code_list.sources:
            dynamic_urls.append(file.module_name)

        args.dynamic_urls = dynamic_urls

        update_yaml_success = action_yml_file_manager.update_yaml_field(
            action_file_name, "dynamic_urls", args.dynamic_urls)
        if not update_yaml_success:
            printer = Printer()
            printer.print_in_terminal(
                "yaml_save_error", style="red", yaml_file=action_file_name)

    return source_code_list
