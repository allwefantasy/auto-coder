from typing import Dict, Any, Optional
from autocoder.common import AutoCoderArgs
from .base_tool_resolver import BaseToolResolver
from autocoder.agent.agentic_edit_types import UseMcpTool, ToolResult # Import ToolResult from types
from autocoder.common.mcp_server import get_mcp_server
from loguru import logger


class UseMcpToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional[Any], tool: UseMcpTool, args: AutoCoderArgs):
        super().__init__(agent, tool, args)
        self.tool: UseMcpTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        """
        Executes a tool via the Model Context Protocol (MCP) server.
        """
        server_name = self.tool.server_name
        tool_name = self.tool.tool_name
        arguments = self.tool.arguments        
        model = self.args.model 
        product_mode = self.args.product_mode


        logger.info(f"Resolving UseMcpTool: Server='{server_name}', Tool='{tool_name}', Args={arguments}")

        # if not server_name or not tool_name:
        return ToolResult(success=False, message="Error: MCP server name and tool name are required.")

        # try:
        #     mcp_server = get_mcp_server()
        #     if not mcp_server:
        #          return ToolResult(success=False, message="Error: MCP server is not available or configured.")

        #     request = McpExecuteToolRequest(
        #         server_name=server_name,
        #         tool_name=tool_name,
        #         arguments=arguments,
        #         model=model, # Pass model info if required by MCP server
        #         product_mode=product_mode
        #     )

        #     logger.debug(f"Sending MCP request: {request.dict()}")
        #     response: McpExecuteToolResponse = mcp_server.send_request(request)
        #     logger.debug(f"Received MCP response: Success={response.success}, Message={response.message}")


        #     if response.success:
        #         return ToolResult(success=True, message=f"MCP tool '{tool_name}' executed successfully. {response.message}", content=response.result)
        #     else:
        #         return ToolResult(success=False, message=f"MCP tool '{tool_name}' failed: {response.message}", content=response.result)

        # except Exception as e:
        #     logger.error(f"Error executing MCP tool '{tool_name}' on server '{server_name}': {str(e)}")
        #     return ToolResult(success=False, message=f"An unexpected error occurred while executing the MCP tool: {str(e)}")
