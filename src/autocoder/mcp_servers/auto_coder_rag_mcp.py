from typing import Any, List, Dict, Generator
import asyncio
import httpx
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from autocoder.rag.long_context_rag import LongContextRAG
from autocoder.common import AutoCoderArgs
from byzerllm import ByzerLLM

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

async def main():
    # Initialize LLM and AutoCoderArgs
    llm = ByzerLLM()
    llm.setup_default_model_name("deepseek_chat")
    
    args = AutoCoderArgs(
        source_dir=".",  # Set your document directory
        tokenizer_path=None,  # Set tokenizer path if needed
        rag_doc_filter_relevance=5,
        rag_context_window_limit=56000,
        full_text_ratio=0.7,
        segment_ratio=0.2,
        index_filter_workers=5,
        index_filter_file_num=3
    )

    server = AutoCoderRAGMCP(llm=llm, args=args)
    await server.setup_server()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())