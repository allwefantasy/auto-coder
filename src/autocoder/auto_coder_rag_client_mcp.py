from typing import Any, List, Dict, Generator, Optional
import asyncio
import httpx
import argparse
from mcp.server.models import InitializationOptions
import mcp.types as types
from mcp.server import NotificationOptions, Server
import mcp.server.stdio
from autocoder.common import AutoCoderArgs
from byzerllm import ByzerLLM
from autocoder.lang import lang_desc
import locale
import pkg_resources
from openai import OpenAI

class AutoCoderRAGClientMCP:
    def __init__(self, llm: ByzerLLM, args: AutoCoderArgs):
        self.llm = llm
        self.args = args
        
        if not args.rag_url:
            raise ValueError("rag_url is required for RAG client mode")
            
        if not args.rag_url.startswith("http://"):
            args.rag_url = f"http://{args.rag_url}"
            
        if not args.rag_url.endswith("/v1"):
            args.rag_url = args.rag_url.rstrip("/") + "/v1"
            
        if not args.rag_token:
            raise ValueError("rag_token is required for RAG client mode")
            
        self.client = OpenAI(api_key=args.rag_token, base_url=args.rag_url)
        
        self.server = Server("auto_coder_rag_client")

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

                response = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": json.dumps({
                        "query": query,
                        "only_contexts": True
                    })}],
                    model=self.args.model,
                    max_tokens=self.args.rag_params_max_tokens,
                )
                result = response.choices[0].message.content
                
                return [
                    types.TextContent(
                        type="text",
                        text=f"Search results for '{query}':\n\n{result}"
                    )
                ]

            elif name == "rag-chat":
                query = arguments.get("query")
                if not query:
                    raise ValueError("Missing query parameter")

                response = self.client.chat.completions.create(
                    messages=[{"role": "user", "content": query}],
                    model=self.args.model,
                    stream=True,
                    max_tokens=self.args.rag_params_max_tokens
                )
                
                full_response = ""
                for chunk in response:
                    if chunk.choices[0].delta.content is not None:
                        full_response += chunk.choices[0].delta.content
                
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
                    server_name="auto_coder_rag_client",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )

def parse_args(input_args: Optional[List[str]] = None) -> AutoCoderArgs:    
    system_lang, _ = locale.getdefaultlocale()
    lang = "zh" if system_lang and system_lang.startswith("zh") else "en"
    desc = lang_desc[lang]
    
    parser = argparse.ArgumentParser(description="Auto Coder RAG Client MCP Server")
    parser.add_argument("--rag_url", required=True, help="RAG server URL")
    parser.add_argument("--rag_token", required=True, help="RAG server token")
    parser.add_argument("--model", default="deepseek_chat", help=desc["model"])
    parser.add_argument("--rag_params_max_tokens", type=int, default=4096, help="Max tokens for RAG response")
    
    args = parser.parse_args(input_args)
    return AutoCoderArgs(**vars(args))

async def main():
    # Parse command line arguments
    args = parse_args()
    
    # Initialize LLM
    llm = ByzerLLM()
    llm.setup_default_model_name(args.model)
    
    # Initialize and run server
    server = AutoCoderRAGClientMCP(llm=llm, args=args)
    await server.setup_server()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())