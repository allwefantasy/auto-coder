from typing import Dict, Any, Optional
import typing
from autocoder.agent.base_agentic.tools.base_tool_resolver import BaseToolResolver
from autocoder.agent.base_agentic.types import UseMcpTool, ToolResult # Import ToolResult from types
from autocoder.common import AutoCoderArgs
from loguru import logger

if typing.TYPE_CHECKING:
    from ..base_agent import BaseAgent


class UseMcpToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional['BaseAgent'], tool: UseMcpTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: UseMcpTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        """
        Executes a tool via the Model Context Protocol (MCP) server.
        """
        final_query = ""
        server_name = self.tool.server_name
        tool_name = self.tool.tool_name

        if server_name:
            final_query += f"{server_name}\n"
        
        if tool_name:
            final_query += f"{tool_name} is recommended for the following query:\n"
        
        final_query += f"{self.tool.query}"

        logger.info(f"Resolving UseMcpTool: Server='{server_name}', Tool='{tool_name}', Query='{final_query}'")

        mcp_server = get_mcp_server()
        response = mcp_server.send_request(
            McpRequest(
                query=final_query,
                model=self.args.inference_model or self.args.model,
                product_mode=self.args.product_mode
            )
        )
        return ToolResult(success=True, message=response.result)

