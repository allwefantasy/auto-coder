import argparse
from typing import Optional, List
import byzerllm
from autocoder.rag.api_server import serve, ServerArgs
from autocoder.rag.rag_entry import RAGFactory
from autocoder.rag.llm_wrapper import LLWrapper
from autocoder.common import AutoCoderArgs
from autocoder.lang import lang_desc
import locale


def main(input_args: Optional[List[str]] = None):
    system_lang, _ = locale.getdefaultlocale()
    lang = "zh" if system_lang and system_lang.startswith("zh") else "en"
    desc = lang_desc[lang]
    doc_serve_parse = argparse.ArgumentParser(description="Auto Coder RAG Server")
    doc_serve_parse.add_argument("--file", default="", help=desc["file"])
    doc_serve_parse.add_argument("--model", default="", help=desc["model"])
    doc_serve_parse.add_argument("--index_model", default="", help=desc["index_model"])
    doc_serve_parse.add_argument("--emb_model", default="", help=desc["emb_model"])
    doc_serve_parse.add_argument(
        "--ray_address", default="auto", help=desc["ray_address"]
    )
    doc_serve_parse.add_argument(
        "--index_filter_workers",
        type=int,
        default=10,
        help=desc["index_filter_workers"],
    )
    doc_serve_parse.add_argument(
        "--index_filter_file_num",
        type=int,
        default=3,
        help=desc["index_filter_file_num"],
    )

    doc_serve_parse.add_argument(
        "--rag_context_window_limit",
        type=int,
        default=120000,
        help="",
    )

    doc_serve_parse.add_argument(
        "--required_exts", default="", help=desc["doc_build_parse_required_exts"]
    )
    doc_serve_parse.add_argument(
        "--rag_doc_filter_relevance", type=int, default=5, help=""
    )
    doc_serve_parse.add_argument("--source_dir", default=".", help="")
    doc_serve_parse.add_argument("--host", default="", help="")
    doc_serve_parse.add_argument("--port", type=int, default=8000, help="")
    doc_serve_parse.add_argument("--uvicorn_log_level", default="info", help="")
    doc_serve_parse.add_argument("--allow_credentials", action="store_true", help="")
    doc_serve_parse.add_argument("--allowed_origins", default=["*"], help="")
    doc_serve_parse.add_argument("--allowed_methods", default=["*"], help="")
    doc_serve_parse.add_argument("--allowed_headers", default=["*"], help="")
    doc_serve_parse.add_argument("--api_key", default="", help="")
    doc_serve_parse.add_argument("--served_model_name", default="", help="")
    doc_serve_parse.add_argument("--prompt_template", default="", help="")
    doc_serve_parse.add_argument("--ssl_keyfile", default="", help="")
    doc_serve_parse.add_argument("--ssl_certfile", default="", help="")
    doc_serve_parse.add_argument("--response_role", default="assistant", help="")
    doc_serve_parse.add_argument("--doc_dir", default="", help="")
    doc_serve_parse.add_argument("--tokenizer_path", default="", help="")
    doc_serve_parse.add_argument(
        "--collections", default="", help="Collection name for indexing"
    )
    doc_serve_parse.add_argument(
        "--base_dir",
        default="",
        help="Path where the processed text embeddings were stored",
    )
    doc_serve_parse.add_argument(
        "--monitor_mode",
        action="store_true",
        help="Monitor mode for the doc update",
    )

    args = doc_serve_parse.parse_args(input_args)

    server_args = ServerArgs(
        **{arg: getattr(args, arg) for arg in vars(ServerArgs()) if hasattr(args, arg)}
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


if __name__ == "__main__":
    main()
