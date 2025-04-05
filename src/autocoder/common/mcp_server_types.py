from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field


class MarketplaceMCPServerItem(BaseModel):
    """Represents an MCP server item"""

    name: str
    description: Optional[str] = ""
    mcp_type: str = "command"  # command/sse
    command: str = ""  # npm/uvx/python/node/...
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)
    url: str = ""  # sse url
    
class McpRequest(BaseModel):
    query: str
    model: Optional[str] = None
    product_mode: Optional[str] = None


class McpInstallRequest(BaseModel):
    server_name_or_config: Optional[str] = None
    market_install_item:Optional[MarketplaceMCPServerItem] = None


class McpRemoveRequest(BaseModel):
    server_name: str


class McpListRequest(BaseModel):
    """Request to list all builtin MCP servers"""
    path:str="/list"


class McpListRunningRequest(BaseModel):
    """Request to list all running MCP servers"""
    path:str="/list/running"


# Pydantic models for raw_result
class ServerConfig(BaseModel):
    command: str
    args: List[str] = Field(default_factory=list)
    env: Dict[str, str] = Field(default_factory=dict)


class InstallResult(BaseModel):
    success: bool
    server_name: Optional[str] = None
    config: Optional[ServerConfig] = None
    error: Optional[str] = None


class RemoveResult(BaseModel):
    success: bool
    server_name: Optional[str] = None
    error: Optional[str] = None


class ExternalServerInfo(BaseModel):
    name: str
    description: str





class ListResult(BaseModel):
    builtin_servers: List[MarketplaceMCPServerItem] = Field(
        default_factory=list)
    external_servers: List[MarketplaceMCPServerItem] = Field(
        default_factory=list)
    marketplace_items: List[MarketplaceMCPServerItem] = Field(
        default_factory=list)
    error: Optional[str] = None


class ServerInfo(BaseModel):
    name: str


class ListRunningResult(BaseModel):
    servers: List[ServerInfo] = Field(default_factory=list)
    error: Optional[str] = None


class RefreshResult(BaseModel):
    success: bool
    name: Optional[str] = None
    error: Optional[str] = None


class QueryResult(BaseModel):
    success: bool
    results: Optional[List[Any]] = None
    error: Optional[str] = None


class ErrorResult(BaseModel):
    success: bool = False
    error: str

class StringResult(BaseModel):
    success: bool = True
    result: str

class McpRefreshRequest(BaseModel):
    """Request to refresh MCP server connections"""
    name: Optional[str] = None


class McpServerInfoRequest(BaseModel):
    """Request to get MCP server info"""
    model: Optional[str] = None
    product_mode: Optional[str] = None


class McpExternalServer(BaseModel):
    """Represents an external MCP server configuration"""
    name: str
    description: str
    vendor: str
    sourceUrl: str
    homepage: str
    license: str
    runtime: str


class MarketplaceAddRequest(BaseModel):
    """Request to add a new marketplace item"""
    name: str
    description: Optional[str] = ""
    mcp_type: str = "command"  # command/sse
    command: Optional[str] = ""  # npm/uvx/python/node/...
    args: Optional[List[str]] = Field(default_factory=list)
    env: Optional[Dict[str, str]] = Field(default_factory=dict)
    url: Optional[str] = ""  # sse url


class MarketplaceAddResult(BaseModel):
    """Result for marketplace add operation"""
    success: bool
    name: str
    error: Optional[str] = None


class MarketplaceUpdateRequest(BaseModel):
    """Request to update an existing marketplace item"""
    name: str
    description: Optional[str] = ""
    mcp_type: str = "command"  # command/sse
    command: Optional[str] = ""  # npm/uvx/python/node/...
    args: Optional[List[str]] = Field(default_factory=list)
    env: Optional[Dict[str, str]] = Field(default_factory=dict)
    url: Optional[str] = ""  # sse url


class MarketplaceUpdateResult(BaseModel):
    """Result for marketplace update operation"""
    success: bool
    name: str
    error: Optional[str] = None

class McpResponse(BaseModel):
    result: str
    error: Optional[str] = None
    raw_result: Optional[Union[InstallResult, MarketplaceAddResult, MarketplaceUpdateResult, RemoveResult,
                               ListResult, ListRunningResult, RefreshResult, QueryResult, ErrorResult,StringResult]] = None
