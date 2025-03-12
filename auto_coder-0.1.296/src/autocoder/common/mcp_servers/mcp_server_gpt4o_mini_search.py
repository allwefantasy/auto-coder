from os import getenv
from textwrap import dedent
import sys
import json
from openai import OpenAI
from loguru import logger
import mcp.server.stdio
import mcp.types as types
from mcp.server import NotificationOptions, Server
from mcp.server.models import InitializationOptions



OPENAI_API_KEY = getenv("OPENAI_API_KEY")
# Check if API key is empty or None
if not OPENAI_API_KEY:
    print("Error: OPENAI_API_KEY environment variable is not set. Please set it before running this server.", file=sys.stderr)
    sys.exit(1)

OPENAI_API_BASE_URL = getenv(
    "OPENAI_API_BASE_URL", "https://api.openai.com/v1")

server = Server("mcp-server-gpt4o-mini-search")

client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url=OPENAI_API_BASE_URL
)


@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="gpt4o_mini_search",
            description=dedent(
                """
                GPT-4o mini with search enables agents to gather information from the internet 
                in real-time, providing up-to-date answers with source citations.
                This tool is ideal for fact-checking, research, and accessing current information
                that might not be in the model's training data.
                
                The search-enhanced responses include relevant web sources to support the information
                provided, making it useful for obtaining verified and recent information.
                
                [Response structure]
                - id: A unique identifier for the response
                - model: The model used (gpt-4o-mini-search-preview)
                - object: The object type ("chat.completion")
                - created: The Unix timestamp when the completion was created
                - choices[]: The list of completion choices generated
                - usage: Usage statistics for the completion request
                """
            ),
            inputSchema={
                "type": "object",
                "properties": {
                    "system_message": {
                        "type": "string",
                        "description": "Optional custom system message. If not provided, a default search-optimized system message will be used.",
                    },
                    "messages": {
                        "type": "array",
                        "description": "A list of messages comprising the conversation so far (excluding system message which is handled separately).",
                        "items": {
                            "type": "object",
                            "properties": {
                                "content": {
                                    "type": "string",
                                    "description": "The contents of the message in this turn of conversation.",
                                },
                                "role": {
                                    "type": "string",
                                    "description": "The role of the speaker in this turn of conversation.",
                                    "enum": ["user", "assistant"],
                                },
                            },
                            "required": ["content", "role"],
                        },
                    },
                },
                "required": ["messages"],
            },
        )
    ]


@server.call_tool()
async def handle_call_tool(
    name: str, arguments: dict
) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:
    if name != "gpt4o_mini_search":
        raise ValueError(f"Unknown tool: {name}")

    # Extract user messages
    user_messages = arguments.get("messages", [])

    # Define default system message if not provided
    default_system_message = (
        "你是专业搜索助手，需要：\n"
        "1. 提供基于用户查询的清晰格式化信息\n"
        "2. 使用[标题](URL)格式嵌入链接\n"
        "3. 每条信息后附上来源\n"
        "4. 用'---'分隔不同结果\n"
        "5. 直接在文本中引用，不使用编号引用\n"
        "6. 确保提供完整URL"
    )

    # Use custom system message if provided, otherwise use default
    system_message = arguments.get("system_message", default_system_message)

    # Prepare full message list with system message first
    full_messages = [{"role": "system", "content": system_message}]
    full_messages.extend(user_messages)

    try:
        # Initialize OpenAI client

        # Make the API call using OpenAI SDK
        completion = client.chat.completions.create(
            model="gpt-4o-mini-search-preview",
            messages=full_messages
        )

        # Extract content from response
        content = completion.choices[0].message.content

    except Exception as e:
        raise RuntimeError(f"API error: {str(e)}")

    return [types.TextContent(
            type="text",
            text=content,
            )]


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="mcp-server-gpt4o-mini-search",
                server_version="0.1.0",
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
