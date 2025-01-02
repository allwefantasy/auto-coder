from typing import Dict, Any, List, Optional, Union
from byzerllm import prompt
from ..common.mcp_hub import McpHub
import json
import byzerllm
import re
from pydantic import BaseModel, Field
from loguru import logger
import mcp.types as mcp_types


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
    def mcp_prompt(self) -> str:
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

        ## Creating an MCP Server

        The user may ask you something along the lines of "add a tool" that does some function, in other words to create an MCP server that provides tools and resources that may connect to external APIs for example. You have the ability to create an MCP server and add it to a configuration file that will then expose the tools and resources for you to use with `use_mcp_tool` and `access_mcp_resource`.

        When creating MCP servers, it's important to understand that they operate in a non-interactive environment. The server cannot initiate OAuth flows, open browser windows, or prompt for user input during runtime. All credentials and authentication tokens must be provided upfront through environment variables in the MCP settings configuration. For example, Spotify's API uses OAuth to get a refresh token for the user, but the MCP server cannot initiate this flow. While you can walk the user through obtaining an application client ID and secret, you may have to create a separate one-time setup script (like get-refresh-token.js) that captures and logs the final piece of the puzzle: the user's refresh token (i.e. you might run the script using execute_command which would open a browser for authentication, and then log the refresh token so that you can see it in the command output for you to use in the MCP settings configuration).

        Unless the user specifies otherwise, new MCP servers should be created in: ${await mcpHub.getMcpServersPath()}

        ### Example MCP Server

        For example, if the user wanted to give you the ability to retrieve weather information, you could create an MCP server that uses the OpenWeather API to get weather information, add it to the MCP settings configuration file, and then notice that you now have access to new tools and resources in the system prompt that you might use to show the user your new capabilities.

        The following example demonstrates how to build an MCP server that provides weather data functionality. While this example shows how to implement resources, resource templates, and tools, in practice you should prefer using tools since they are more flexible and can handle dynamic parameters. The resource and resource template implementations are included here mainly for demonstration purposes of the different MCP capabilities, but a real weather server would likely just expose tools for fetching weather data. (The following steps are for macOS)

        1. Use the `create-typescript-server` tool to bootstrap a new project in the default MCP servers directory:

        ```bash
        cd ${await mcpHub.getMcpServersPath()}
        npx @modelcontextprotocol/create-server weather-server
        cd weather-server
        # Install dependencies
        npm install axios
        ```

        This will create a new project with the following structure:

        ```
        weather-server/
          ├── package.json
              {
                ...
                "type": "module", // added by default, uses ES module syntax (import/export) rather than CommonJS (require/module.exports) (Important to know if you create additional scripts in this server repository like a get-refresh-token.js script)
                "scripts": {
                  "build": "tsc && node -e \"require('fs').chmodSync('build/index.js', '755')\"",
                  ...
                }
                ...
              }
          ├── tsconfig.json
          └── src/
              └── weather-server/
                  └── index.ts      # Main server implementation
        ```

        2. Replace `src/index.ts` with the following:

        ```typescript
        #!/usr/bin/env node
        import { Server } from '@modelcontextprotocol/sdk/server/index.js';
        import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
        import {
          CallToolRequestSchema,
          ErrorCode,
          ListResourcesRequestSchema,
          ListResourceTemplatesRequestSchema,
          ListToolsRequestSchema,
          McpError,
          ReadResourceRequestSchema,
        } from '@modelcontextprotocol/sdk/types.js';
        import axios from 'axios';

        const API_KEY = process.env.OPENWEATHER_API_KEY; // provided by MCP config
        if (!API_KEY) {
          throw new Error('OPENWEATHER_API_KEY environment variable is required');
        }

        interface OpenWeatherResponse {
          main: {
            temp: number;
            humidity: number;
          };
          weather: [{ description: string }];
          wind: { speed: number };
          dt_txt?: string;
        }

        const isValidForecastArgs = (
          args: any
        ): args is { city: string; days?: number } =>
          typeof args === 'object' &&
          args !== null &&
          typeof args.city === 'string' &&
          (args.days === undefined || typeof args.days === 'number');

        class WeatherServer {
          private server: Server;
          private axiosInstance;

          constructor() {
            this.server = new Server(
              {
                name: 'example-weather-server',
                version: '0.1.0',
              },
              {
                capabilities: {
                  resources: {},
                  tools: {},
                },
              }
            );

            this.axiosInstance = axios.create({
              baseURL: 'http://api.openweathermap.org/data/2.5',
              params: {
                appid: API_KEY,
                units: 'metric',
              },
            });

            this.setupResourceHandlers();
            this.setupToolHandlers();

            // Error handling
            this.server.onerror = (error) => console.error('[MCP Error]', error);
            process.on('SIGINT', async () => {
              await this.server.close();
              process.exit(0);
            });
          }

          // MCP Resources represent any kind of UTF-8 encoded data that an MCP server wants to make available to clients, such as database records, API responses, log files, and more. Servers define direct resources with a static URI or dynamic resources with a URI template that follows the format `[protocol]://[host]/[path]`.
          private setupResourceHandlers() {
            // For static resources, servers can expose a list of resources:
            this.server.setRequestHandler(ListResourcesRequestSchema, async () => ({
              resources: [
                // This is a poor example since you could use the resource template to get the same information but this demonstrates how to define a static resource
                {
                  uri: `weather://San Francisco/current`, // Unique identifier for San Francisco weather resource
                  name: `Current weather in San Francisco`, // Human-readable name
                  mimeType: 'application/json', // Optional MIME type
                  // Optional description
                  description:
                    'Real-time weather data for San Francisco including temperature, conditions, humidity, and wind speed',
                },
              ],
            }));

            // For dynamic resources, servers can expose resource templates:
            this.server.setRequestHandler(
              ListResourceTemplatesRequestSchema,
              async () => ({
                resourceTemplates: [
                  {
                    uriTemplate: 'weather://{city}/current', // URI template (RFC 6570)
                    name: 'Current weather for a given city', // Human-readable name
                    mimeType: 'application/json', // Optional MIME type
                    description: 'Real-time weather data for a specified city', // Optional description
                  },
                ],
              })
            );

            // ReadResourceRequestSchema is used for both static resources and dynamic resource templates
            this.server.setRequestHandler(
              ReadResourceRequestSchema,
              async (request) => {
                const match = request.params.uri.match(
                  /^weather:\/\/([^/]+)\/current$/
                );
                if (!match) {
                  throw new McpError(
                    ErrorCode.InvalidRequest,
                    `Invalid URI format: ${request.params.uri}`
                  );
                }
                const city = decodeURIComponent(match[1]);

                try {
                  const response = await this.axiosInstance.get(
                    'weather', // current weather
                    {
                      params: { q: city },
                    }
                  );

                  return {
                    contents: [
                      {
                        uri: request.params.uri,
                        mimeType: 'application/json',
                        text: JSON.stringify(
                          {
                            temperature: response.data.main.temp,
                            conditions: response.data.weather[0].description,
                            humidity: response.data.main.humidity,
                            wind_speed: response.data.wind.speed,
                            timestamp: new Date().toISOString(),
                          },
                          null,
                          2
                        ),
                      },
                    ],
                  };
                } catch (error) {
                  if (axios.isAxiosError(error)) {
                    throw new McpError(
                      ErrorCode.InternalError,
                      `Weather API error: ${
                        error.response?.data.message ?? error.message
                      }`
                    );
                  }
                  throw error;
                }
              }
            );
          }

          /* MCP Tools enable servers to expose executable functionality to the system. Through these tools, you can interact with external systems, perform computations, and take actions in the real world.
          * - Like resources, tools are identified by unique names and can include descriptions to guide their usage. However, unlike resources, tools represent dynamic operations that can modify state or interact with external systems.
          * - While resources and tools are similar, you should prefer to create tools over resources when possible as they provide more flexibility.
          */
          private setupToolHandlers() {
            this.server.setRequestHandler(ListToolsRequestSchema, async () => ({
              tools: [
                {
                  name: 'get_forecast', // Unique identifier
                  description: 'Get weather forecast for a city', // Human-readable description
                  inputSchema: {
                    // JSON Schema for parameters
                    type: 'object',
                    properties: {
                      city: {
                        type: 'string',
                        description: 'City name',
                      },
                      days: {
                        type: 'number',
                        description: 'Number of days (1-5)',
                        minimum: 1,
                        maximum: 5,
                      },
                    },
                    required: ['city'], // Array of required property names
                  },
                },
              ],
            }));

            this.server.setRequestHandler(CallToolRequestSchema, async (request) => {
              if (request.params.name !== 'get_forecast') {
                throw new McpError(
                  ErrorCode.MethodNotFound,
                  `Unknown tool: ${request.params.name}`
                );
              }

              if (!isValidForecastArgs(request.params.arguments)) {
                throw new McpError(
                  ErrorCode.InvalidParams,
                  'Invalid forecast arguments'
                );
              }

              const city = request.params.arguments.city;
              const days = Math.min(request.params.arguments.days || 3, 5);

              try {
                const response = await this.axiosInstance.get<{
                  list: OpenWeatherResponse[];
                }>('forecast', {
                  params: {
                    q: city,
                    cnt: days * 8,
                  },
                });

                return {
                  content: [
                    {
                      type: 'text',
                      text: JSON.stringify(response.data.list, null, 2),
                    },
                  ],
                };
              } catch (error) {
                if (axios.isAxiosError(error)) {
                  return {
                    content: [
                      {
                        type: 'text',
                        text: `Weather API error: ${
                          error.response?.data.message ?? error.message
                        }`,
                      },
                    ],
                    isError: true,
                  };
                }
                throw error;
              }
            });
          }

          async run() {
            const transport = new StdioServerTransport();
            await this.server.connect(transport);
            console.error('Weather MCP server running on stdio');
          }
        }

        const server = new WeatherServer();
        server.run().catch(console.error);
        ```

        (Remember: This is just an example–you may use different dependencies, break the implementation up into multiple files, etc.)

        3. Build and compile the executable JavaScript file

        ```bash
        npm run build
        ```

        4. Whenever you need an environment variable such as an API key to configure the MCP server, walk the user through the process of getting the key. For example, they may need to create an account and go to a developer dashboard to generate the key. Provide step-by-step instructions and URLs to make it easy for the user to retrieve the necessary information. Then use the ask_followup_question tool to ask the user for the key, in this case the OpenWeather API key.

        5. Install the MCP Server by adding the MCP server configuration to the settings file located at '${await mcpHub.getMcpSettingsFilePath()}'. The settings file may have other MCP servers already configured, so you would read it first and then add your new server to the existing `mcpServers` object.

        ```json
        {
          "mcpServers": {
            ...,
            "weather": {
              "command": "node",
              "args": ["/path/to/weather-server/build/index.js"],
              "env": {
                "OPENWEATHER_API_KEY": "user-provided-api-key"
              }
            },
          }
        }
        ```

        (Note: the user may also ask you to install the MCP server to the Claude desktop app, in which case you would read then modify `~/Library/Application\ Support/Claude/claude_desktop_config.json` on macOS for example. It follows the same format of a top level `mcpServers` object.)

        6. After you have edited the MCP settings configuration file, the system will automatically run all the servers and expose the available tools and resources in the 'Connected MCP Servers' section.

        7. Now that you have access to these new tools and resources, you may suggest ways the user can command you to invoke them - for example, with this new weather tool now available, you can invite the user to ask "what's the weather in San Francisco?"

        ## Editing MCP Servers

        The user may ask to add tools or resources that may make sense to add to an existing MCP server (listed under 'Connected MCP Servers' above: {{ server_names }}, e.g. if it would use the same API. This would be possible if you can locate the MCP server repository on the user's system by looking at the server arguments for a filepath. You might then use list_files and read_file to explore the files in the repository, and use replace_in_file to make changes to the files.

        However some MCP servers may be running from installed packages rather than a local repository, in which case it may make more sense to create a new MCP server.

        # MCP Servers Are Not Always Necessary

        The user may not always request the use or creation of MCP servers. Instead, they might provide tasks that can be completed with existing tools. While using the MCP SDK to extend your capabilities can be useful, it's important to understand that this is just one specialized type of task you can accomplish. You should only implement MCP servers when the user explicitly requests it (e.g., "add a tool that...").

        Remember: The MCP documentation and example provided above are to help you understand and work with existing MCP servers or create new ones when requested by the user. You already have access to tools and capabilities that can be used to accomplish a wide range of tasks.
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
        new_conversations = [{
            "role": "user",
            "content": self.mcp_prompt.prompt()
        }, {
            "role": "assistant",
            "content": "I have read the tools usage instructions."
        }] + conversations

        all_tool_results = []

        v = self.llm.chat_oai(conversations=new_conversations)
        content = v[0].output        
        tools = await self.extract_mcp_calls(content)
        # while tools:            
        #     results = await self.execute_mcp_tools(tools)
        #     all_tool_results += results
        #     str_results = "\n\n".join(self.format_mcp_result(result) for result in results)            
        #     new_conversations += [{
        #         "role": "assistant",
        #         "content": f"Tool results: {str_results}"
        #     },{
        #         "role": "user",
        #         "content": "continue"
        #     }]
        #     v = self.llm.chat_oai(conversations=new_conversations)
        #     content = v[0].output        
        #     tools = await self.extract_mcp_calls(content)
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
        # if isinstance(result, mcp_types.CallToolResult):
        #     for content in result.contents:
        #         if isinstance(content, mcp_types.TextContent):
        #             return content.text
        # if isinstance(result, mcp_types.ReadResourceResult):
        #     return result.contents                    
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
