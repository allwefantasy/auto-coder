import os
import json
import asyncio
import aiohttp
import importlib
import pkgutil
import re
import inspect
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Optional, Tuple
from pathlib import Path
from pydantic import BaseModel, Field
from loguru import logger
from contextlib import AsyncExitStack
from datetime import timedelta
from autocoder.common.mcp_server_types import MarketplaceMCPServerItem

try:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters
    from mcp.client.sse import sse_client
    import mcp.types as mcp_types
except ImportError:
    mcp_types = None
    stdio_client = None
    sse_client = None   
    ClientSession = None
    logger.error("mcp is not installed(which requires python>=3.11), please install it by `pip install mcp`")

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

    def __init__(self, server: McpServer, session: ClientSession):
        self.server = server
        self.session = session        


def _generate_server_configs() -> Tuple[Dict[str, Any], Dict[str, str]]:
    """
    Scan the autocoder.common.mcp_servers directory for mcp_server_*.py files
    and generate server configurations.
    
    Returns:
        Tuple of (built-in servers dict, JSON templates dict)
    """
    servers = {}
    templates = {}
    
    try:
        package_name = "autocoder.common.mcp_servers"
        package = importlib.import_module(package_name)
        
        # Find all modules in the package
        for _, name, _ in pkgutil.iter_modules(package.__path__, package.__name__ + "."):
            # Only process modules that start with "mcp_server_"
            base_name = name.split(".")[-1]
            if base_name.startswith("mcp_server_"):
                # Generate a friendly server name
                friendly_name = base_name[11:]
                                
                # Create env dictionary with placeholders
                env_dict = {}
                
                # Create server configuration
                config = {
                    "command": "python",
                    "args": ["-m", name],
                    "env": env_dict
                }                                
                
                # Store in dictionaries
                servers[friendly_name] = config
                templates[friendly_name] = json.dumps({friendly_name: config}, indent=4)                                
    
    except Exception as e:
        logger.error(f"Error generating server configs: {e}")
    
    return servers, templates


# Automatically generate server configurations
MCP_BUILD_IN_SERVERS, MCP_SERVER_TEMPLATES = _generate_server_configs()


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

    def __init__(self, settings_path: Optional[str] = None, marketplace_path: Optional[str] = None):
        if self._initialized:
            return
        """Initialize the MCP Hub with a path to settings file"""
        if settings_path is None:
            self.settings_path = Path.home() / ".auto-coder" / "mcp" / "settings.json"
        else:
            self.settings_path = Path(settings_path)

        if marketplace_path is None:
            self.marketplace_path = Path.home() / ".auto-coder" / "mcp" / "marketplace.json"
        else:
            self.marketplace_path = Path(marketplace_path)

        self.connections: Dict[str, McpConnection] = {}
        self.is_connecting = False
        self.exit_stacks: Dict[str, AsyncExitStack] = {}

        # Ensure settings directory exists
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.settings_path.exists():
            self._write_default_settings()
            
        # Ensure marketplace file exists
        self.marketplace_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.marketplace_path.exists():
            self._write_default_marketplace()

        self._initialized = True

    def _write_default_settings(self):
        """Write default MCP settings file"""
        default_settings = {"mcpServers": {}}
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(default_settings, f, indent=2)
            
    def _write_default_marketplace(self):
        """Write default marketplace file"""
        default_marketplace = {"mcpServers": []}
        with open(self.marketplace_path, "w", encoding="utf-8") as f:
            json.dump(default_marketplace, f, indent=2)
            
    def _read_marketplace(self) -> Dict[str, List[Dict[str, Any]]]:
        """Read marketplace file"""
        try:
            with open(self.marketplace_path,"r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read marketplace: {e}")
            return {"mcpServers": []}
            
    def get_marketplace_items(self) -> List[MarketplaceMCPServerItem]:
        """Get all marketplace items"""
        data = self._read_marketplace()
        return [MarketplaceMCPServerItem(**item) for item in data.get("mcpServers", [])]
        
    def get_marketplace_item(self, name: str) -> Optional[MarketplaceMCPServerItem]:
        """Get a marketplace item by name"""
        items = self.get_marketplace_items()
        for item in items:
            if item.name == name:
                return item
        return None
    
    async def add_marketplace_item(self, item: MarketplaceMCPServerItem) -> bool:
        """
        Add a new marketplace item
        
        Args:
            item: MarketplaceMCPServerItem to add
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Check if item with this name already exists
            existing = self.get_marketplace_item(item.name)
            if existing:
                logger.warning(f"Marketplace item with name {item.name} already exists")
                return False
                
            # Add the new item
            data = self._read_marketplace()
            data["mcpServers"].append(item.dict())
            
            # Write back to file
            with open(self.marketplace_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                
            logger.info(f"Added marketplace item: {item.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to add marketplace item: {e}")
            return False
    
    async def update_marketplace_item(self, name: str, updated_item: MarketplaceMCPServerItem) -> bool:
        """
        Update an existing marketplace item
        
        Args:
            name: Name of the item to update
            updated_item: Updated MarketplaceMCPServerItem
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = self._read_marketplace()
            items = data.get("mcpServers", [])
            
            # Find the item to update
            for i, item in enumerate(items):
                if item.get("name") == name:
                    # Update the item
                    items[i] = updated_item.model_dump()
                    
                    # Write back to file
                    with open(self.marketplace_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    logger.info(f"Updated marketplace item: {name}")
                    return True
            
            logger.warning(f"Marketplace item with name {name} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to update marketplace item: {e}")
            return False
    
    async def remove_marketplace_item(self, name: str) -> bool:
        """
        Remove a marketplace item
        
        Args:
            name: Name of the item to remove
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            data = self._read_marketplace()
            items = data.get("mcpServers", [])
            
            # Find and remove the item
            for i, item in enumerate(items):
                if item.get("name") == name:
                    del items[i]
                    
                    # Write back to file
                    with open(self.marketplace_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=2, ensure_ascii=False)
                    
                    logger.info(f"Removed marketplace item: {name}")
                    return True
            
            logger.warning(f"Marketplace item with name {name} not found")
            return False
        except Exception as e:
            logger.error(f"Failed to remove marketplace item: {e}")
            return False
            
    async def apply_marketplace_item(self, name: str) -> bool:
        """
        Apply a marketplace item to server config
        
        Args:
            name: Name of the item to apply
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            item = self.get_marketplace_item(name)
            if not item:
                logger.warning(f"Marketplace item with name {name} not found")
                return False
                
            # Convert marketplace item to server config
            config = {}
            
            if item.mcp_type == "command":
                config = {
                    "command": item.command,
                    "args": item.args,
                    "env": item.env,
                    "transport": {
                        "type": "stdio",
                        "endpoint": ""
                    }
                }
            elif item.mcp_type == "sse":
                config = {
                    "transport": {
                        "type": "sse",
                        "endpoint": item.url
                    }
                }
            else:
                logger.error(f"Unknown MCP type: {item.mcp_type}")
                return False
                
            # Add server config
            result = await self.add_server_config(name, config)
            return result
        except Exception as e:
            logger.error(f"Failed to apply marketplace item: {e}")
            return False

    async def add_server_config(self, name: str, config: Dict[str, Any]) -> None:
        """
        Add or update MCP server configuration in settings file.

        Args:
            server_name_or_config: Name of the server or server configuration dictionary
        """
        settings = self._read_settings()
        settings["mcpServers"][name] = config
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        await self.initialize()
        if name in self.connections:
            if self.connections[name].server.status == "connected":
                logger.info(f"Added/updated MCP server config: {name}")
                return True
            else:
                logger.error(f"Failed to add MCP server config: {name}")
                return False
        else:
            logger.error(f"Failed to add MCP server config: {name}")
            return False

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
                with open(self.settings_path, "w", encoding="utf-8") as f:
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
        config = self._read_settings()
        await self.update_server_connections(config.get("mcpServers", {}))

    def get_servers(self) -> List[McpServer]:
        """Get list of all configured servers"""
        return [conn.server for conn in self.connections.values()]

    async def connect_to_server(self, name: str, config: dict) -> McpServer:
        """
        Establish connection to an MCP server with proper resource management
        """
        # Remove existing connection if present
        if name in self.connections:
            await self.delete_connection(name)

        self.exit_stacks[name] = AsyncExitStack()
        exit_stack = self.exit_stacks[name]

        server = McpServer(
            name=name, config=json.dumps(config), status="connecting"
        )
        transport_config = config.get("transport", {
            "type": "stdio",
            "endpoint":""
        })

        if transport_config["type"] not in ["stdio", "sse"]:
            raise ValueError(f"Invalid transport type: {transport_config['type']}")
        
        if transport_config["type"] == "stdio":            
            # Setup transport parameters
            server_params = StdioServerParameters(
                command=config["command"],
                args=config.get("args", []),
                env={**config.get("env", {}),
                    "PATH": os.environ.get("PATH", "")},
            )

            # Create transport using context manager
            transport = await exit_stack.enter_async_context(stdio_client(server_params))
        
        if transport_config["type"] == "sse":
            url = transport_config["endpoint"]
            transport = await exit_stack.enter_async_context(sse_client(url))
        
        
        try:
            stdio, write = transport
            session = await exit_stack.enter_async_context(
                ClientSession(stdio, write, read_timeout_seconds=timedelta(seconds=60)))
            await session.initialize()
            connection = McpConnection(server, session)
            self.connections[name] = connection
            # Update server status and fetch capabilities
            server.status = "connected"
            server.tools = await self._fetch_tools(name)
            server.resources = await self._fetch_resources(name)
            server.resource_templates = await self._fetch_resource_templates(name)
            return server
        
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Failed to connect to server {name}: {error_msg}")
            if name in self.connections:
                self.connections[name].server.status = "disconnected"
                self.connections[name].server.error = error_msg
            return server

        




    async def delete_connection(self, name: str) -> None:
        """
        Close and remove a server connection with proper cleanup
        """
        if name in self.connections:
            
            try:                
                del self.connections[name]
            except Exception as e:
                logger.error(f"Error closing connection to {name}: {e}")

            try:
                exit_stack = self.exit_stacks[name]
                await exit_stack.aclose()
                del self.exit_stacks[name]
            except Exception as e:
                logger.error(f"Error cleaning up to {name}: {e}")
                        

    async def refresh_server_connection(self, name: str) -> None:
        """
        Refresh a server connection
        """
        config = self._read_settings()
        await self.delete_connection(name)
        await self.connect_to_server(name, config.get("mcpServers", {}).get(name, {}))

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
                    server = await self.connect_to_server(name, config)
                    if server.status == "connected":
                        logger.info(f"Connected to new MCP server: {name}")
                    else:
                        logger.error(
                            f"Failed to connect to new MCP server: {name}")

                elif current_conn.server.config != json.dumps(config):
                    # Updated configuration
                    server = await self.connect_to_server(name, config)
                    if server.status == "connected":
                        logger.info(
                            f"Reconnected MCP server with updated config: {name}")
                    else:
                        logger.error(
                            f"Failed to reconnected MCP server with updated config: {name}")

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

    @classmethod
    def get_server_templates(cls) -> Dict[str, str]:
        """
        Get all available server templates as JSON strings
        """
        return MCP_SERVER_TEMPLATES
