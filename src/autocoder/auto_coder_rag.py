import argparse
from typing import Optional, List
import byzerllm
from autocoder.rag.api_server import serve, ServerArgs
from autocoder.rag.rag_entry import RAGFactory
from autocoder.rag.llm_wrapper import LLWrapper
from autocoder.common import AutoCoderArgs
from autocoder.lang import lang_desc
import locale
from autocoder.chat_auto_coder_lang import get_message
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.formatted_text import HTML
import platform
import subprocess
import shlex
from rich.console import Console
from rich.table import Table
import os

from autocoder.rag.document_retriever import process_file_local
from autocoder.rag.token_counter import TokenCounter

if platform.system() == "Windows":
    from colorama import init

    init()


def initialize_system():
    print(f"\n\033[1;34m{get_message('initializing')}\033[0m")

    def print_status(message, status):
        if status == "success":
            print(f"\033[32m✓ {message}\033[0m")
        elif status == "warning":
            print(f"\033[33m! {message}\033[0m")
        elif status == "error":
            print(f"\033[31m✗ {message}\033[0m")
        else:
            print(f"  {message}")

    # Check if Ray is running
    print_status(get_message("checking_ray"), "")
    ray_status = subprocess.run(["ray", "status"], capture_output=True, text=True)
    if ray_status.returncode != 0:
        print_status(get_message("ray_not_running"), "warning")
        try:
            subprocess.run(["ray", "start", "--head"], check=True)
            print_status(get_message("ray_start_success"), "success")
        except subprocess.CalledProcessError:
            print_status(get_message("ray_start_fail"), "error")
            return
    else:
        print_status(get_message("ray_running"), "success")

    # Check if deepseek_chat model is available
    print_status(get_message("checking_model"), "")
    try:
        result = subprocess.run(
            ["easy-byzerllm", "chat", "deepseek_chat", "你好"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print_status(get_message("model_available"), "success")
            print_status(get_message("init_complete_final"), "success")
            return
    except subprocess.TimeoutExpired:
        print_status(get_message("model_timeout"), "error")
    except subprocess.CalledProcessError:
        print_status(get_message("model_error"), "error")

    # If deepseek_chat is not available, prompt user to choose a provider
    print_status(get_message("model_not_available"), "warning")
    choice = radiolist_dialog(
        title=get_message("provider_selection"),
        text=get_message("provider_selection"),
        values=[
            ("1", "Deepseek官方(https://www.deepseek.com/)"),
        ],
    ).run()

    if choice is None:
        print_status(get_message("no_provider"), "error")
        return

    api_key = prompt(HTML(f"<b>{get_message('enter_api_key')} </b>"))

    if choice == "1":
        print_status(get_message("deploying_model").format("Deepseek官方"), "")

        deploy_cmd = [
            "byzerllm",
            "deploy",
            "--pretrained_model_type",
            "saas/openai",
            "--cpus_per_worker",
            "0.001",
            "--gpus_per_worker",
            "0",
            "--worker_concurrency",
            "1000",
            "--num_workers",
            "1",
            "--infer_params",
            f"saas.base_url=https://api.deepseek.com/v1 saas.api_key={api_key} saas.model=deepseek-chat",
            "--model",
            "deepseek_chat",
        ]

    try:
        subprocess.run(deploy_cmd, check=True)
        print_status(get_message("deploy_complete"), "success")
    except subprocess.CalledProcessError:
        print_status(get_message("deploy_fail"), "error")
        return

    # Validate the deployment
    print_status(get_message("validating_deploy"), "")
    try:
        validation_result = subprocess.run(
            ["easy-byzerllm", "chat", "deepseek_chat", "你好"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        print_status(get_message("validation_success"), "success")
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        print_status(get_message("validation_fail"), "error")
        print_status(get_message("manual_start"), "warning")
        print_status("easy-byzerllm chat deepseek_chat 你好", "")

    print_status(get_message("init_complete_final"), "success")


def main(input_args: Optional[List[str]] = None):

    system_lang, _ = locale.getdefaultlocale()
    lang = "zh" if system_lang and system_lang.startswith("zh") else "en"
    desc = lang_desc[lang]
    parser = argparse.ArgumentParser(description="Auto Coder RAG Server")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Serve command
    serve_parser = subparsers.add_parser("serve", help="Start the RAG server")
    serve_parser.add_argument(
        "--quick", action="store_true", help="Skip system initialization"
    )
    serve_parser.add_argument("--file", default="", help=desc["file"])
    serve_parser.add_argument("--model", default="deepseek_chat", help=desc["model"])
    serve_parser.add_argument("--index_model", default="", help=desc["index_model"])
    serve_parser.add_argument("--emb_model", default="", help=desc["emb_model"])
    serve_parser.add_argument("--ray_address", default="auto", help=desc["ray_address"])
    serve_parser.add_argument(
        "--index_filter_workers",
        type=int,
        default=100,
        help=desc["index_filter_workers"],
    )
    serve_parser.add_argument(
        "--index_filter_file_num",
        type=int,
        default=3,
        help=desc["index_filter_file_num"],
    )
    serve_parser.add_argument(
        "--rag_context_window_limit",
        type=int,
        default=110000,
        help="The input context window limit for RAG",
    )
    serve_parser.add_argument(
        "--full_text_ratio",
        type=float,
        default=0.7,
        help="The ratio of full text area in the input context window (0.0 to 1.0)",
    )
    serve_parser.add_argument(
        "--segment_ratio",
        type=float,
        default=0.2,
        help="The ratio of segment area in the input context window (0.0 to 1.0)",
    )
    serve_parser.add_argument(
        "--required_exts", default="", help=desc["doc_build_parse_required_exts"]
    )
    serve_parser.add_argument(
        "--rag_doc_filter_relevance", type=int, default=5, help=""
    )
    serve_parser.add_argument("--source_dir", default=".", help="")
    serve_parser.add_argument("--host", default="", help="")
    serve_parser.add_argument("--port", type=int, default=8000, help="")
    serve_parser.add_argument("--uvicorn_log_level", default="info", help="")
    serve_parser.add_argument("--allow_credentials", action="store_true", help="")
    serve_parser.add_argument("--allowed_origins", default=["*"], help="")
    serve_parser.add_argument("--allowed_methods", default=["*"], help="")
    serve_parser.add_argument("--allowed_headers", default=["*"], help="")
    serve_parser.add_argument("--api_key", default="", help="")
    serve_parser.add_argument("--served_model_name", default="", help="")
    serve_parser.add_argument("--prompt_template", default="", help="")
    serve_parser.add_argument("--ssl_keyfile", default="", help="")
    serve_parser.add_argument("--ssl_certfile", default="", help="")
    serve_parser.add_argument("--response_role", default="assistant", help="")
    serve_parser.add_argument("--doc_dir", default="", help="")
    serve_parser.add_argument("--tokenizer_path", default="", help="")
    serve_parser.add_argument(
        "--collections", default="", help="Collection name for indexing"
    )
    serve_parser.add_argument(
        "--base_dir",
        default="",
        help="Path where the processed text embeddings were stored",
    )
    serve_parser.add_argument(
        "--monitor_mode",
        action="store_true",
        help="Monitor mode for the doc update",
    )

    serve_parser.add_argument(
        "--disable_auto_window",
        action="store_true",
        help="Disable automatic window adaptation for documents",
    )
    serve_parser.add_argument(
        "--disable_segment_reorder",
        action="store_true",
        help="Disable reordering of document segments after retrieval",
    )

    # Tools command
    tools_parser = subparsers.add_parser("tools", help="Various tools")
    tools_subparsers = tools_parser.add_subparsers(dest="tool", help="Available tools")

    # Count tool
    count_parser = tools_subparsers.add_parser("count", help="Count tokens in a file")
    count_parser.add_argument(
        "--tokenizer_path", required=True, help="Path to the tokenizer"
    )
    count_parser.add_argument(
        "--file", required=True, help="Path to the file to count tokens"
    )

    args = parser.parse_args(input_args)

    if args.command == "serve":
        if not args.quick:
            initialize_system()
        server_args = ServerArgs(
            **{
                arg: getattr(args, arg)
                for arg in vars(ServerArgs())
                if hasattr(args, arg)
            }
        )
        auto_coder_args = AutoCoderArgs(
            **{
                arg: getattr(args, arg)
                for arg in vars(AutoCoderArgs())
                if hasattr(args, arg)
            }
        )

        byzerllm.connect_cluster(address=args.ray_address)
        llm = byzerllm.ByzerLLM()
        llm.setup_default_model_name(args.model)

        if server_args.doc_dir:
            auto_coder_args.rag_type = "simple"
            rag = RAGFactory.get_rag(
                llm=llm,
                args=auto_coder_args,
                path=server_args.doc_dir,
                tokenizer_path=server_args.tokenizer_path,
            )
        else:
            rag = RAGFactory.get_rag(llm=llm, args=auto_coder_args, path="")

        llm_wrapper = LLWrapper(llm=llm, rag=rag)
        serve(llm=llm_wrapper, args=server_args)
    elif args.command == "tools" and args.tool == "count":
        # auto-coder.rag tools count --tokenizer_path /Users/allwefantasy/Downloads/tokenizer.json --file /Users/allwefantasy/data/yum/schema/schema.xlsx
        count_tokens(args.tokenizer_path, args.file)


def count_tokens(tokenizer_path: str, file_path: str):
    token_counter = TokenCounter(tokenizer_path)
    source_codes = process_file_local(file_path)

    console = Console()
    table = Table(title="Token Count Results")
    table.add_column("File", style="cyan")
    table.add_column("Characters", justify="right", style="magenta")
    table.add_column("Tokens", justify="right", style="green")

    total_chars = 0
    total_tokens = 0

    for source_code in source_codes:
        content = source_code.source_code
        chars = len(content)
        tokens = token_counter.count_tokens(content)

        total_chars += chars
        total_tokens += tokens

        table.add_row(source_code.module_name, str(chars), str(tokens))

    table.add_row("Total", str(total_chars), str(total_tokens), style="bold")

    console.print(table)


if __name__ == "__main__":
    main()
