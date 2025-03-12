from os import getenv
from textwrap import dedent

import httpx
import json
from loguru import logger

import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions

PERPLEXITY_API_KEY = getenv("PERPLEXITY_API_KEY")
PERPLEXITY_API_BASE_URL = "https://api.perplexity.ai"


server = Server("mcp-server-perplexity")


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="ask_perplexity",
            description=dedent(
                """
                Perplexity equips agents with a specialized tool for efficiently
                gathering source-backed information from the internet, ideal for
                scenarios requiring research, fact-checking, or contextual data to
                inform decisions and responses.
                Each response includes citations, which provide transparent references
                to the sources used for the generated answer, and choices, which
                contain the model's suggested responses, enabling users to access
                reliable information and diverse perspectives.
                This function may encounter timeout errors due to long processing times,
                but retrying the operation can lead to successful completion.
                [Response structure]
                - id: An ID generated uniquely for each response.
                - model: The model used to generate the response.
                - object: The object type, which always equals `chat.completion`.
                - created: The Unix timestamp (in seconds) of when the completion was
                  created.
                - citations[]: Citations for the generated answer.
                - choices[]: The list of completion choices the model generated for the
                  input prompt.
                - usage: Usage statistics for the completion request.
                """
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "The name of the model that will complete your prompt.",
                        "enum": [
                            # "llama-3.1-sonar-small-128k-online",
                            # Commenting out larger models,which have higher risks of timing out,
                            # until Claude Desktop can handle long-running tasks effectively.
                            # "llama-3.1-sonar-large-128k-online",
                            "sonar-reasoning-pro",
                        ],
                    },
                    "messages": {
                        "type": "array",
                        "description": "A list of messages comprising the conversation so far.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "The contents of the message in this turn of conversation.",
                                },
                                "role": {
                                    "type": "string",
                                    "description": "The role of the speaker in this turn of conversation. After the (optional) system message, user and assistant roles should alternate with user then assistant, ending in user.",
                                    "enum": ["system", "user", "assistant"],
                                },
                            },
                            "required": ["content", "role"],
                        },
                    },
                },
                "required": ["model", "messages"],
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name != "ask_perplexity":
        raise ValueError(f"Unknown tool: {name}")

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PERPLEXITY_API_BASE_URL}/chat/completions",
                headers={
                    "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=arguments,
                timeout=None,
            )
            response.raise_for_status()
    except httpx.HTTPError as e:
        raise RuntimeError(f"API error: {str(e)}")

    result = json.loads(response.text)
    c = result["choices"][0]["message"]["content"]
    return [types.TextContent(
            type="text",
            text= c,
            )]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-server-perplexity",
                server_version="0.1.2",
                capabilities=server.get_capabilities(
                    notification_options=NotificationOptions(
                        tools_changed=True),
                    experimental_capabilities={},
                ),
            ),
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
