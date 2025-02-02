from autocoder.index.index import IndexManager
from autocoder.index.types import TargetFile
from autocoder.suffixproject import SuffixProject
from autocoder.tsproject import TSProject
from autocoder.pyproject import PyProject
import tabulate
import textwrap
from autocoder.common.printer import Printer
import os
from autocoder.utils.request_queue import (
    request_queue,
    RequestValue,
    StreamValue,
    DefaultValue,
    RequestOption,
)


def wrap_text_in_table(data, max_width=60):
    """
    Wraps text in each cell of the table to a specified width.

    :param data: A list of lists, where each inner list represents a row in the table.
    :param max_width: The maximum width of text in each cell.
    :return: A new table data with wrapped text.
    """
    wrapped_data = []
    for row in data:
        wrapped_row = [textwrap.fill(str(cell), width=max_width) for cell in row]
        wrapped_data.append(wrapped_row)

    return wrapped_data


def index_command(args, llm):
    source_dir = os.path.abspath(args.source_dir)
    args.source_dir = source_dir
    printer = Printer()
    printer.print_in_terminal("begin_index_source_code", style="bold green", source_dir=source_dir)
    if args.project_type == "ts":
        pp = TSProject(args=args, llm=llm)
    elif args.project_type == "py":
        pp = PyProject(args=args, llm=llm)
    else:
        pp = SuffixProject(args=args, llm=llm, file_filter=None)
    pp.run()
    sources = pp.sources
    index_manager = IndexManager(llm=llm, sources=sources, args=args)
    index_manager.build_index()


def index_query_command(args, llm):
    if args.project_type == "ts":
        pp = TSProject(args=args, llm=llm)
    elif args.project_type == "py":
        pp = PyProject(args=args, llm=llm)
    else:
        pp = SuffixProject(args=args, llm=llm, file_filter=None)
    pp.run()
    sources = pp.sources

    final_files = []

    index_manager = IndexManager(llm=llm, sources=sources, args=args)
    target_files = index_manager.get_target_files_by_query(args.query)

    if target_files:
        final_files.extend(target_files.file_list)

    if target_files and args.index_filter_level >= 2:

        related_fiels = index_manager.get_related_files(
            [file.file_path for file in target_files.file_list]
        )

        if related_fiels is not None:
            final_files.extend(related_fiels.file_list)

    all_results = list({file.file_path: file for file in final_files}.values())

    print("===================Filter FILEs=========================", flush=True)

    print(
        f"index_filter_level:{args.index_filter_level}, total files: {len(all_results)} filter files by query: {args.query}",
        flush=True,
    )

    headers = TargetFile.model_fields.keys()
    table_data = wrap_text_in_table(
        [[getattr(file_item, name) for name in headers] for file_item in all_results]
    )
    table_output = tabulate.tabulate(table_data, headers, tablefmt="grid")
    print(table_output, flush=True)
    request_queue.add_request(
        args.request_id,
        RequestValue(
            value=DefaultValue(value=table_output), status=RequestOption.COMPLETED
        ),
    )
    return
