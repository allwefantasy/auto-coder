from typing import Dict, Any, Optional
from .base_tool_resolver import BaseToolResolver, ToolResult
from autocoder.agent.agentic_edit_types import UseMcpTool
from autocoder.common.mcp_server import get_mcp_server, McpExecuteToolRequest, McpExecuteToolResponse # Assuming these exist
from loguru import logger


class UseMcpToolResolver(BaseToolResolver):
    def __init__(self, agent: Optional[Any], tool: UseMcpTool, args: Dict[str, Any]):
        super().__init__(agent, tool, args)
        self.tool: UseMcpTool = tool # For type hinting

    def resolve(self) -> ToolResult:
        """
        Executes a tool via the Model Context Protocol (MCP) server.
        """
        server_name = self.tool.server_name
        tool_name = self.tool.tool_name
        arguments = self.tool.arguments
        # Assuming agent has access to args which might contain model info etc.
        agent_args = self.args.get("agent_args", None)
        model = agent_args.model if agent_args else None
        product_mode = agent_args.product_mode if agent_args else False


        logger.info(f"Resolving UseMcpTool: Server='{server_name}', Tool='{tool_name}', Args={arguments}")

        if not server_name or not tool_name:
            return ToolResult(success=False, message="Error: MCP server name and tool name are required.")

        try:
            mcp_server = get_mcp_server()
            if not mcp_server:
                 return ToolResult(success=False, message="Error: MCP server is not available or configured.")

            request = McpExecuteToolRequest(
                server_name=server_name,
                tool_name=tool_name,
                arguments=arguments,
                model=model, # Pass model info if required by MCP server
                product_mode=product_mode
            )

            logger.debug(f"Sending MCP request: {request.dict()}")
            response: McpExecuteToolResponse = mcp_server.send_request(request)
            logger.debug(f"Received MCP response: Success={response.success}, Message={response.message}")


            if response.success:
                return ToolResult(success=True, message=f"MCP tool '{tool_name}' executed successfully. {response.message}", content=response.result)
            else:
                return ToolResult(success=False, message=f"MCP tool '{tool_name}' failed: {response.message}", content=response.result)

        except Exception as e:
            logger.error(f"Error executing MCP tool '{tool_name}' on server '{server_name}': {str(e)}")
            return ToolResult(success=False, message=f"An unexpected error occurred while executing the MCP tool: {str(e)}")
