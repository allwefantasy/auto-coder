from typing import Dict, Any, List, Optional, Union
from byzerllm import prompt
import json
import byzerllm
import re
from pydantic import BaseModel, Field
from loguru import logger
import os
import time
try:    
    import mcp.types as mcp_types    
except ImportError:
    mcp_types = None
    logger.error("mcp is not installed(which requires python>=3.11), please install it by `pip install mcp`")
from autocoder.common.mcp_hub import McpHub    


class McpToolCall(BaseModel):
    server_name: str = Field(..., description="The name of the MCP server")
    tool_name: str = Field(..., description="The name of the tool to call")
    arguments: Dict[str, Any] = Field(
        default_factory=dict, description="The arguments to pass to the tool")


class McpResourceAccess(BaseModel):
    server_name: str = Field(..., description="The name of the MCP server")
    uri: str = Field(..., description="The URI of the resource to access")


class McpExecutor:
    def __init__(self, mcp_hub: McpHub, llm: byzerllm.ByzerLLM):
        self.mcp_hub = mcp_hub
        self.llm = llm

    def get_server_names(self) -> List[str]:
        """
        Get the names of all connected MCP servers.

        Returns:
            List of server names
            
        """
        server_names = [server.name for server in self.mcp_hub.get_servers()]
        return ",".join(server_names) or "(None running currently)"

    def get_connected_servers_info(self) -> str:
        """Generate formatted information about connected MCP servers

        Args:
            mcp_hub: McpHub instance to get server information from

        Returns:
            Formatted string with server details
        """
        servers = self.mcp_hub.get_servers()
        if not servers:
            return "(No MCP servers currently connected)"

        info = []
        for server in servers:
            if server.status != "connected":
                continue

            # Format tools information
            tools_info = []
            if server.tools:
                for tool in server.tools:
                    tool_str = f"- {tool.name}: {tool.description}"
                    if tool.input_schema:
                        schema_str = "    Input Schema:\n" + \
                            "\n".join(f"    {line}" for line in
                                      json.dumps(tool.input_schema, indent=2).split("\n"))
                        tool_str += f"\n{schema_str}"
                    tools_info.append(tool_str)

            # Format resource templates
            templates_info = []
            if server.resource_templates:
                for template in server.resource_templates:
                    template_str = f"- {template.uri_template} ({template.name}): {template.description}"
                    templates_info.append(template_str)

            # Format direct resources
            resources_info = []
            if server.resources:
                for resource in server.resources:
                    resource_str = f"- {resource.uri} ({resource.name}): {resource.description}"
                    resources_info.append(resource_str)

            # Parse server config
            config = json.loads(server.config)
            command = config['command']
            args = config.get('args', [])
            command_str = f"{command} {' '.join(args)}"

            # Build server section
            server_info = f"## {server.name} (`{command_str}`)"
            if tools_info:
                server_info += "\n\n### Available Tools\n" + \
                    "\n\n".join(tools_info)
            if templates_info:
                server_info += "\n\n### Resource Templates\n" + \
                    "\n".join(templates_info)
            if resources_info:
                server_info += "\n\n### Direct Resources\n" + \
                    "\n".join(resources_info)

            info.append(server_info)

        return "\n\n".join(info)
    
    

    @byzerllm.prompt()
    def mcp_prompt(self,query:str) -> str:
        """    
        TOOL USE

        You have access to a set of tools that are executed upon the user's approval. You can use one tool per message, and will receive the result of that tool use in the user's response. You use tools step-by-step to accomplish a given task, with each tool use informed by the result of the previous tool use.

        # Tool Use Formatting

        Tool use is formatted using XML-style tags. The tool name is enclosed in opening and closing tags, and each parameter is similarly enclosed within its own set of tags. Here's the structure:

        <tool_name>
        <parameter1_name>value1</parameter1_name>
        <parameter2_name>value2</parameter2_name>
        ...
        </tool_name>

        For example:

        <read_file>
        <path>src/main.js</path>
        </read_file>

        Always adhere to this format for the tool use to ensure proper parsing and execution.

        # Tools

        ## use_mcp_tool
        Description: Request to use a tool provided by a connected MCP server. Each MCP server can provide multiple tools with different capabilities. Tools have defined input schemas that specify required and optional parameters.
        Parameters:
        - server_name: (required) The name of the MCP server providing the tool
        - tool_name: (required) The name of the tool to execute
        - arguments: (required) A JSON object containing the tool's input parameters, following the tool's input schema
        Usage:
        <use_mcp_tool>
        <server_name>server name here</server_name>
        <tool_name>tool name here</tool_name>
        <arguments>
        {
          "param1": "value1",
          "param2": "value2"
        }
        </arguments>
        </use_mcp_tool>

        ## access_mcp_resource
        Description: Request to access a resource provided by a connected MCP server. Resources represent data sources that can be used as context, such as files, API responses, or system information.
        Parameters:
        - server_name: (required) The name of the MCP server providing the resource
        - uri: (required) The URI identifying the specific resource to access
        Usage:
        <access_mcp_resource>
        <server_name>server name here</server_name>
        <uri>resource URI here</uri>
        </access_mcp_resource>


        # Tool Use Examples

        ## Example 1: Requesting to use an MCP tool

        <use_mcp_tool>
        <server_name>weather-server</server_name>
        <tool_name>get_forecast</tool_name>
        <arguments>
        {
          "city": "San Francisco",
          "days": 5
        }
        </arguments>
        </use_mcp_tool>

        ## Example 2: Requesting to access an MCP resource

        <access_mcp_resource>
        <server_name>weather-server</server_name>
        <uri>weather://san-francisco/current</uri>
        </access_mcp_resource>


        ====

        MCP SERVERS

        The Model Context Protocol (MCP) enables communication between the system and locally running MCP servers that provide additional tools and resources to extend your capabilities.

        # Connected MCP Servers

        When a server is connected, you can use the server's tools via the `use_mcp_tool` tool, and access the server's resources via the `access_mcp_resource` tool.

        {{ connected_servers_info }}
      
        # MCP Servers Are Not Always Necessary

        The user may not always request the use or creation of MCP servers. Instead, they might provide tasks that can be completed with existing tools. While using the MCP SDK to extend your capabilities can be useful, it's important to understand that this is just one specialized type of task you can accomplish. You should only implement MCP servers when the user explicitly requests it (e.g., "add a tool that...").

        Remember: The MCP documentation and example provided above are to help you understand and work with existing MCP servers or create new ones when requested by the user. You already have access to tools and capabilities that can be used to accomplish a wide range of tasks.

        用户的问题是：
                
        {{query}}

        请选择前面罗列的 MCP Servers 信息，并且按规定格式来选择前面罗列的 MCP Servers，并选择合适的工具来回答。
        注意，如果没有合适的工具，你可以直接回答没有可用工具。
        """
        return {
            "connected_servers_info": self.get_connected_servers_info(),
            "server_names": self.get_server_names()
        }

    async def extract_mcp_calls(self,content: str) -> List[Union[McpToolCall, McpResourceAccess]]:
        """
        Extract MCP tool calls and resource accesses from content.

        Args:
            content: The content to parse for MCP tool calls

        Returns:
            List of McpToolCall and McpResourceAccess objects
        """
        results = []

        # Regex pattern to match tool calls
        tool_pattern = re.compile(
            r"<use_mcp_tool>.*?<server_name>(.*?)</server_name>.*?"
            r"<tool_name>(.*?)</tool_name>.*?"
            r"<arguments>(.*?)</arguments>.*?</use_mcp_tool>",
            re.DOTALL
        )

        # Regex pattern to match resource accesses
        resource_pattern = re.compile(
            r"<access_mcp_resource>.*?<server_name>(.*?)</server_name>.*?"
            r"<uri>(.*?)</uri>.*?</access_mcp_resource>",
            re.DOTALL
        )

        # Extract tool calls
        for match in tool_pattern.finditer(content):
            try:
                arguments = json.loads(match.group(3).strip())
                results.append(McpToolCall(
                    server_name=match.group(1).strip(),
                    tool_name=match.group(2).strip(),
                    arguments=arguments
                ))
            except json.JSONDecodeError:
                continue

        # Extract resource accesses
        for match in resource_pattern.finditer(content):
            results.append(McpResourceAccess(
                server_name=match.group(1).strip(),
                uri=match.group(2).strip()
            ))

        return results

    async def run(self, conversations: List[Dict[str, Any]]):                
        all_tool_results = []

        query = conversations[-1]["content"]
        new_conversations = conversations[0:-1]+[{
            "role": "user",
            "content": self.mcp_prompt.prompt(query=query)
        }]

        v = self.llm.chat_oai(conversations=new_conversations)
        content = v[0].output  

        tools = await self.extract_mcp_calls(content)

        if tools:
            results = await self.execute_mcp_tools(tools)
            all_tool_results += results            
            
        return new_conversations,all_tool_results

    def format_mcp_result(self, result: Any) -> str:
        """
        Format MCP tool or resource result into a human-readable string.

        Args:
            result: The result from MCP tool call or resource access

        Returns:
            Formatted string representation of the result
        """
        if result is None:
            return "(No result)"
        if isinstance(result, mcp_types.CallToolResult):
            if len(result.content) ==1:
                return result.content[0].text
                                                                      
        return json.dumps(result.model_dump(), indent=2, ensure_ascii=False)

    async def execute_mcp_tools(self, tools: List[Union[McpToolCall, McpResourceAccess]]) -> List[Any]:
        """
        Execute MCP tools and return results in order.

        Args:
            mcp_hub: McpHub instance to execute tools
            tools: List of McpToolCall and McpResourceAccess objects

        Returns:
            List of results in the same order as the input tools
        """
        results = []
        for tool in tools:
            try:
                if isinstance(tool, McpToolCall):
                    result = await self.mcp_hub.call_tool(tool.server_name, tool.tool_name, tool.arguments)
                    results.append(result)
                elif isinstance(tool, McpResourceAccess):
                    result = await self.mcp_hub.read_resource(tool.server_name, tool.uri)
                    results.append(result)
                else:
                    results.append(None)
            except Exception as e:
                logger.error(f"Failed to execute MCP tool {tool}: {e}")
                results.append(None)
        return results
