import os
import json
import asyncio
import aiohttp
from datetime import datetime
from typing import Dict, List, Optional, Any, Set, Optional
from pathlib import Path
from pydantic import BaseModel, Field

from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
import mcp.types as mcp_types
from loguru import logger
import time


class McpTool(BaseModel):
    """Represents an MCP tool configuration"""

    name: str
    description: Optional[str] = None
    input_schema: dict = Field(default_factory=dict)


class McpResource(BaseModel):
    """Represents an MCP resource configuration"""

    uri: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


class McpResourceTemplate(BaseModel):
    """Represents an MCP resource template"""

    uri_template: str
    name: str
    description: Optional[str] = None
    mime_type: Optional[str] = None


class McpServer(BaseModel):
    """Represents an MCP server configuration and status"""

    name: str
    config: str  # JSON string of server config
    status: str = "disconnected"  # connected, disconnected, connecting
    error: Optional[str] = None
    tools: List[McpTool] = Field(default_factory=list)
    resources: List[McpResource] = Field(default_factory=list)
    resource_templates: List[McpResourceTemplate] = Field(default_factory=list)


class McpConnection:
    """Represents an active MCP server connection"""

    def __init__(self, server: McpServer, session: ClientSession, transport_manager):
        self.server = server
        self.session = session
        self.transport_manager = (
            transport_manager  # Will hold transport context manager
        )


MCP_PERPLEXITY_SERVER = '''
{
    "perplexity": {
        "command": "python",
        "args": [
            "-m", "autocoder.common.mcp_servers.mcp_server_perplexity"
        ],
        "env": {
            "PERPLEXITY_API_KEY": "{{PERPLEXITY_API_KEY}}"
        }
    }
}
'''

MCP_BUILD_IN_SERVERS = {
    "perplexity": json.loads(MCP_PERPLEXITY_SERVER)["perplexity"]
}

class McpHub:
    """
    Manages MCP server connections and interactions.
    Similar to the TypeScript McpHub but adapted for Python/asyncio.
    """

    _instance = None

    def __new__(cls, settings_path: Optional[str] = None):
        if cls._instance is None:
            cls._instance = super(McpHub, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, settings_path: Optional[str] = None):
        if self._initialized:
            return
        """Initialize the MCP Hub with a path to settings file"""
        if settings_path is None:
            self.settings_path = Path.home() / ".auto-coder" / "mcp" / "settings.json"
        else:
            self.settings_path = Path(settings_path)
        self.connections: Dict[str, McpConnection] = {}
        self.is_connecting = False

        # Ensure settings directory exists
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.settings_path.exists():
            self._write_default_settings()

        self._initialized = True

    def _write_default_settings(self):
        """Write default MCP settings file"""
        default_settings = {"mcpServers": {}}
        with open(self.settings_path, "w") as f:
            json.dump(default_settings, f, indent=2)

    async def add_server_config(self, name: str, config:Dict[str,Any]) -> None:
        """
        Add or update MCP server configuration in settings file.

        Args:
            server_name_or_config: Name of the server or server configuration dictionary
        """
        try:
            settings = self._read_settings()            
            settings["mcpServers"][name] = config
            with open(self.settings_path, "w") as f:
                json.dump(settings, f, indent=2, ensure_ascii=False)
            await self.initialize()
            logger.info(f"Added/updated MCP server config: {name}")
        except Exception as e:
            logger.error(f"Failed to add MCP server config: {e}")
            raise

    async def remove_server_config(self, name: str) -> None:
        """
        Remove MCP server configuration from settings file.

        Args:
            name: Name of the server to remove
        """
        try:
            settings = self._read_settings()
            if name in settings["mcpServers"]:
                del settings["mcpServers"][name]
                with open(self.settings_path, "w") as f:
                    json.dump(settings, f, indent=2, ensure_ascii=False)
                logger.info(f"Removed MCP server config: {name}")
                await self.initialize()
            else:
                logger.warning(f"MCP server {name} not found in settings")
        except Exception as e:
            logger.error(f"Failed to remove MCP server config: {e}")
            raise

    async def initialize(self):
        """Initialize MCP server connections from settings"""
        try:
            config = self._read_settings()
            await self.update_server_connections(config.get("mcpServers", {}))
        except Exception as e:
            logger.error(f"Failed to initialize MCP servers: {e}")
            raise

    def get_servers(self) -> List[McpServer]:
        """Get list of all configured servers"""
        return [conn.server for conn in self.connections.values()]

    async def connect_to_server(self, name: str, config: dict) -> None:
        """
        Establish connection to an MCP server with proper resource management
        """
        # Remove existing connection if present
        if name in self.connections:
            await self.delete_connection(name)

        try:
            server = McpServer(
                name=name, config=json.dumps(config), status="connecting"
            )

            # Setup transport parameters
            server_params = StdioServerParameters(
                command=config["command"],
                args=config.get("args", []),
                env={**config.get("env", {}),
                     "PATH": os.environ.get("PATH", "")},
            )

            # Create transport using context manager            
            transport_manager = stdio_client(server_params)
            transport = await transport_manager.__aenter__()
            try:
                session = await ClientSession(transport[0], transport[1]).__aenter__()
                await session.initialize()

                # Store connection with transport manager
                connection = McpConnection(server, session, transport_manager)
                self.connections[name] = connection

                # Update server status and fetch capabilities
                server.status = "connected"                
                server.tools = await self._fetch_tools(name)                
                server.resources = await self._fetch_resources(name)                
                server.resource_templates = await self._fetch_resource_templates(name)

            except Exception as e:
                # Clean up transport if session initialization fails

                await transport_manager.__aexit__(None, None, None)
                raise

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to connect to server {name}: {error_msg}")
            if name in self.connections:
                self.connections[name].server.status = "disconnected"
                self.connections[name].server.error = error_msg
            raise

    async def delete_connection(self, name: str) -> None:
        """
        Close and remove a server connection with proper cleanup
        """
        if name in self.connections:
            try:
                connection = self.connections[name]
                # Clean up in reverse order of creation
                await connection.session.__aexit__(None, None, None)
                await connection.transport_manager.__aexit__(None, None, None)
                del self.connections[name]
            except Exception as e:
                logger.error(f"Error closing connection to {name}: {e}")
                # Continue with deletion even if cleanup fails
                if name in self.connections:
                    del self.connections[name]

    async def refresh_server_connection(self, name: str) -> None:
        """
        Refresh a server connection
        """
        try:
            config = self._read_settings()
            await self.delete_connection(name)
            await self.connect_to_server(name, config.get("mcpServers", {}).get(name, {}))
        except Exception as e:
            logger.error(f"Failed to refresh MCP server {name}: {e}")
            raise
        

    async def update_server_connections(self, new_servers: Dict[str, Any]) -> None:
        """
        Update server connections based on new configuration
        """
        self.is_connecting = True
        try:
            current_names = set(self.connections.keys())
            new_names = set(new_servers.keys())

            # Remove deleted servers
            for name in current_names - new_names:
                await self.delete_connection(name)
                logger.info(f"Deleted MCP server: {name}")

            # Add or update servers
            for name, config in new_servers.items():
                current_conn = self.connections.get(name)

                if not current_conn:
                    # New server
                    await self.connect_to_server(name, config)
                    logger.info(f"Connected to new MCP server: {name}")
                elif current_conn.server.config != json.dumps(config):
                    # Updated configuration
                    await self.connect_to_server(name, config)
                    logger.info(
                        f"Reconnected MCP server with updated config: {name}")

        finally:
            self.is_connecting = False

    async def _fetch_tools(self, server_name: str) -> List[McpTool]:
        """Fetch available tools from server"""
        try:
            connection = self.connections.get(server_name)
            if not connection:
                return []

            response = await connection.session.list_tools()
            return [
                McpTool(
                    name=tool.name,
                    description=tool.description,
                    input_schema=tool.inputSchema,
                )
                for tool in response.tools
            ]
        except Exception as e:
            logger.error(f"Failed to fetch tools for {server_name}: {e}")
            return []

    async def _fetch_resources(self, server_name: str) -> List[McpResource]:
        """Fetch available resources from server"""
        try:
            connection = self.connections.get(server_name)
            if not connection:
                return []

            response = await connection.session.list_resources()
            return [
                McpResource(
                    uri=resource.uri,
                    name=resource.name,
                    description=resource.description,
                    mime_type=resource.mimeType,
                )
                for resource in response.resources
            ]
        except Exception as e:
            logger.warning(f"Failed to fetch resources for {server_name}: {e}")
            return []

    async def _fetch_resource_templates(
        self, server_name: str
    ) -> List[McpResourceTemplate]:
        """Fetch available resource templates from server"""
        try:
            connection = self.connections.get(server_name)
            if not connection:
                return []

            #       return await self.send_request(
            #     types.ClientRequest(
            #         types.PingRequest(
            #             method="ping",
            #         )
            #     ),
            #     types.EmptyResult,
            # )

            response = await connection.session.send_request(
                mcp_types.ClientRequest(mcp_types.ListResourceTemplatesRequest(
                    method="resources/templates/list",
                )),
                mcp_types.ListResourceTemplatesResult,
            )
            return [
                McpResourceTemplate(
                    uri_template=template.uriTemplate,
                    name=template.name,
                    description=template.description,
                    mime_type=template.mimeType,
                )
                for template in response.resourceTemplates
            ]
        except Exception as e:
            logger.warning(
                f"Failed to fetch resource templates for {server_name}: {e}")
            return []

    def _read_settings(self) -> dict:
        """Read MCP settings file"""
        try:
            with open(self.settings_path) as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read MCP settings: {e}")
            return {"mcpServers": {}}

    async def call_tool(
        self, server_name: str, tool_name: str, tool_arguments: Optional[Dict] = None
    ) -> mcp_types.CallToolResult:
        """
        Call an MCP tool with arguments
        """
        connection = self.connections.get(server_name)
        if not connection:
            raise ValueError(f"No connection found for server: {server_name}")

        return await connection.session.call_tool(tool_name, tool_arguments or {})

    async def read_resource(self, server_name: str, uri: str) -> mcp_types.ReadResourceResult:
        """
        Read an MCP resource
        """
        connection = self.connections.get(server_name)
        if not connection:
            raise ValueError(f"No connection found for server: {server_name}")

        return await connection.session.read_resource(uri)

    async def shutdown(self):
        """
        Clean shutdown of all connections
        """
        for name in list(self.connections.keys()):
            await self.delete_connection(name)
