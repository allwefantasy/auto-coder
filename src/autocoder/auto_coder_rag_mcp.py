from typing import Any, List, Dict, Generator, Optional
import asyncio
import httpx
import argparse
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from autocoder.rag.long_context_rag import LongContextRAG
from autocoder.common import AutoCoderArgs
from byzerllm import ByzerLLM
from autocoder.lang import lang_desc
import locale
import pkg_resources

class AutoCoderRAGMCP:
    def __init__(self, llm: ByzerLLM, args: AutoCoderArgs):
        self.llm = llm
        self.args = args
        self.rag = LongContextRAG(
            llm=llm,
            args=args,
            path=args.source_dir,
            tokenizer_path=args.tokenizer_path
        )
        self.server = Server("auto_coder_rag")

    async def setup_server(self):
        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            return [
                types.Tool(
                    name="rag-search",
                    description="Search documents using RAG",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query",
                            },
                        },
                        "required": ["query"],
                    },
                ),
                types.Tool(
                    name="rag-chat",
                    description="Chat with documents using RAG",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Chat query",
                            },
                        },
                        "required": ["query"],
                    },
                ),
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: Dict[str, Any] | None
        ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            if not arguments:
                raise ValueError("Missing arguments")

            if name == "rag-search":
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing query parameter")

                results = self.rag.search(query)
                return [
                    types.TextContent(
                        type="text",
                        text=f"Search results for '{query}':\n\n" + 
                        "\n".join([f"- {result.module_name}: {result.source_code[:200]}..." 
                                 for result in results])
                    )
                ]

            elif name == "rag-chat":
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing query parameter")

                response, _ = self.rag.stream_chat_oai(
                    conversations=[{"role": "user", "content": query}]
                )
                full_response = "".join([chunk for chunk in response])
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"Chat response for '{query}':\n\n{full_response}"
                    )
                ]

            else:
                raise ValueError(f"Unknown tool: {name}")

    async def run(self):
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="auto_coder_rag",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

def parse_args(input_args: Optional[List[str]] = None) -> AutoCoderArgs:
    try:
        tokenizer_path = pkg_resources.resource_filename(
            "autocoder", "data/tokenizer.json"
        )
    except FileNotFoundError:
        tokenizer_path = None

    system_lang, _ = locale.getdefaultlocale()
    lang = "zh" if system_lang and system_lang.startswith("zh") else "en"
    desc = lang_desc[lang]
    
    parser = argparse.ArgumentParser(description="Auto Coder RAG MCP Server")
    parser.add_argument("--source_dir", default=".", help="Source directory path")
    parser.add_argument("--tokenizer_path", default=tokenizer_path, help="Path to tokenizer file")
    parser.add_argument("--model", default="deepseek_chat", help=desc["model"])
    parser.add_argument("--index_model", default="", help=desc["index_model"])
    parser.add_argument("--emb_model", default="", help=desc["emb_model"])
    parser.add_argument("--ray_address", default="auto", help=desc["ray_address"])
    parser.add_argument("--required_exts", default="", help=desc["doc_build_parse_required_exts"])
    parser.add_argument("--rag_doc_filter_relevance", type=int, default=5, help="Relevance score threshold for document filtering")
    parser.add_argument("--rag_context_window_limit", type=int, default=56000, help="Context window limit for RAG")
    parser.add_argument("--full_text_ratio", type=float, default=0.7, help="Ratio of full text area in context window")
    parser.add_argument("--segment_ratio", type=float, default=0.2, help="Ratio of segment area in context window")
    parser.add_argument("--index_filter_workers", type=int, default=5, help="Number of workers for document filtering")
    parser.add_argument("--index_filter_file_num", type=int, default=3, help="Maximum number of files to filter")
    parser.add_argument("--host", default="", help="Server host address")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--monitor_mode", action="store_true", help="Enable document monitoring mode")
    parser.add_argument("--enable_hybrid_index", action="store_true", help="Enable hybrid index")
    parser.add_argument("--disable_auto_window", action="store_true", help="Disable automatic window adaptation")
    parser.add_argument("--disable_segment_reorder", action="store_true", help="Disable segment reordering")
    parser.add_argument("--disable_inference_enhance", action="store_true", help="Disable inference enhancement")
    parser.add_argument("--inference_deep_thought", action="store_true", help="Enable deep thought in inference")
    parser.add_argument("--inference_slow_without_deep_thought", action="store_true", help="Enable slow inference without deep thought")
    parser.add_argument("--inference_compute_precision", type=int, default=64, help="Inference compute precision")
    parser.add_argument("--data_cells_max_num", type=int, default=2000, help="Maximum number of data cells to process")
    parser.add_argument("--recall_model", default="", help="Model used for document recall")
    parser.add_argument("--chunk_model", default="", help="Model used for document chunking")
    parser.add_argument("--qa_model", default="", help="Model used for question answering")    

    args = parser.parse_args(input_args)
    return AutoCoderArgs(**vars(args)),args

async def main():
    # Parse command line arguments
    args,raw_rags = parse_args()
    
    # Initialize LLM
    llm = ByzerLLM()
    llm.setup_default_model_name(args.model)
    
    # Setup sub models if specified
    if raw_rags.recall_model:
        recall_model = ByzerLLM()
        recall_model.setup_default_model_name(args.recall_model)
        llm.setup_sub_client("recall_model", recall_model)

    if raw_rags.chunk_model:
        chunk_model = ByzerLLM()
        chunk_model.setup_default_model_name(args.chunk_model)
        llm.setup_sub_client("chunk_model", chunk_model)

    if raw_rags.qa_model:
        qa_model = ByzerLLM()
        qa_model.setup_default_model_name(args.qa_model)
        llm.setup_sub_client("qa_model", qa_model)

    # Initialize and run server
    server = AutoCoderRAGMCP(llm=llm, args=args)
    await server.setup_server()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())