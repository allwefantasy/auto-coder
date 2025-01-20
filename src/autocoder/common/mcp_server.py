import asyncio
from asyncio import Queue as AsyncQueue
import threading
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import byzerllm
from autocoder.common.mcp_hub import McpHub
from autocoder.common.mcp_tools import McpExecutor
from autocoder.common.mcp_hub import MCP_BUILD_IN_SERVERS
import json
import os
import time
from pydantic import BaseModel
import sys
from loguru import logger

@dataclass
class McpRequest:
    query: str
    model: Optional[str] = None


@dataclass
class McpInstallRequest:
    server_name_or_config: Optional[str] = None


@dataclass
class McpRemoveRequest:
    server_name: str


@dataclass
class McpListRequest:
    """Request to list all builtin MCP servers"""
    pass


@dataclass
class McpListRunningRequest:
    """Request to list all running MCP servers"""
    pass

@dataclass
class McpResponse:
    result: str
    error: Optional[str] = None


@dataclass
class McpRefreshRequest:
    """Request to refresh MCP server connections"""
    name: Optional[str] = None


@dataclass
class McpExternalServer(BaseModel):
    result: str
    error: Optional[str] = None


class McpExternalServer(BaseModel):
    """Represents an external MCP server configuration"""
    name: str
    description: str
    vendor: str
    sourceUrl: str
    homepage: str
    license: str
    runtime: str


def get_mcp_external_servers() -> List[McpExternalServer]:
    """Get external MCP servers list from GitHub"""
    cache_dir = os.path.join(".auto-coder", "tmp")
    os.makedirs(cache_dir, exist_ok=True)
    cache_file = os.path.join(cache_dir, "mcp_external_servers.json")

    # Check cache first
    if os.path.exists(cache_file):
        cache_time = os.path.getmtime(cache_file)
        if time.time() - cache_time < 3600:  # 1 hour cache
            with open(cache_file, "r") as f:
                raw_data = json.load(f)
                return [McpExternalServer(**item) for item in raw_data]

    # Fetch from GitHub
    url = "https://raw.githubusercontent.com/michaellatman/mcp-get/refs/heads/main/packages/package-list.json"
    try:
        import requests
        response = requests.get(url)
        if response.status_code == 200:
            raw_data = response.json()
            with open(cache_file, "w") as f:
                json.dump(raw_data, f)
            return [McpExternalServer(**item) for item in raw_data]
        return []
    except Exception as e:
        logger.error(f"Failed to fetch external MCP servers: {e}")
        return []


class McpServer:
    def __init__(self):
        self._request_queue = AsyncQueue()
        self._response_queue = AsyncQueue()
        self._running = False
        self._task = None
        self._loop = None

    def start(self):
        if self._running:
            return

        self._running = True
        self._loop = asyncio.new_event_loop()
        threading.Thread(target=self._run_event_loop, daemon=True).start()

    def stop(self):
        if self._running:
            self._running = False
            if self._loop:
                self._loop.stop()
                self._loop.close()

    def _run_event_loop(self):
        asyncio.set_event_loop(self._loop)
        self._task = self._loop.create_task(self._process_request())
        self._loop.run_forever()

    def _install_python_package(self, package_name: str) -> None:
        """Install a Python package using pip"""
        try:
            import importlib
            importlib.import_module(package_name.replace("-", "_"))
        except ImportError:
            import subprocess
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", package_name], check=True)
            except subprocess.CalledProcessError:
                print(f"\n\033[93mFailed to automatically install {package_name}. Please manually install it using:\n")
                print(f"    pip install {package_name}\n")
                print(f"We have already updated the server configuration in ~/.autocoder/mcp/settings.json.\n")
                print(f"After installation, you can restart the auto-coder.chat using the server.\033[0m\n")

    def _install_node_package(self, package_name: str) -> None:
        """Install a Node.js package using npm"""
        import subprocess
        try:
            subprocess.run(["npx", package_name, "--version"], check=True)
        except:
            try:
                subprocess.run(["npm", "install", "-y", "-g", package_name], check=True)
            except subprocess.CalledProcessError:
                print(f"\n\033[93mFailed to automatically install {package_name}. Please manually install it using:\n")
                print(f"    npm install -g {package_name}\n")
                print(f"We have already updated the server configuration in ~/.autocoder/mcp/settings.json.\n")
                print(f"After installation, you can restart the auto-coder.chat using the server.\033[0m\n")

    async def _install_server(self, request: McpInstallRequest, hub: McpHub) -> McpResponse:
        """Install an MCP server with module dependency check"""
        name = ""
        config = {}
        try:
            server_name_or_config = request.server_name_or_config
            try:
                raw_config = json.loads(server_name_or_config)
                # 用户给了一个完整的配置
                if "mcpServers" in raw_config:
                    raw_config = raw_config["mcpServers"]

                # 取第一个server 配置
                config = list(raw_config.values())[0]
                name = list(raw_config.keys())[0]
                if name.startswith("@") or config["command"] in ["npx","npm"]:
                    for item in config["args"]:
                        if name in item:
                            self._install_node_package(item)                    
                else:
                    self._install_python_package(name)
            except json.JSONDecodeError:
                name = server_name_or_config.strip()
                if name not in MCP_BUILD_IN_SERVERS:
                    # 查找外部server
                    external_servers = get_mcp_external_servers()
                    for s in external_servers:
                        if s.name == name:
                            if s.runtime == "python":
                                self._install_python_package(name)
                                config = {
                                    "command": "python",
                                    "args": [
                                        "-m", name.replace("-", "_")
                                    ],
                                }
                            elif s.runtime == "node":
                                self._install_node_package(name)
                                config = {
                                    "command": "npx",
                                    "args": [
                                        "-y",
                                        "-g",
                                        name
                                    ]
                                }
                            break
                else:
                    config = MCP_BUILD_IN_SERVERS[name]
            if not name:
                raise ValueError(
                    "MCP server name is not available in MCP_BUILD_IN_SERVERS or external servers")

            logger.info(f"Installing MCP server: {name} with config: {config}")
            if not config:
                raise ValueError(f"MCP server {name} config is not available")

            await hub.add_server_config(name, config)
            return McpResponse(result=f"Successfully installed MCP server: {request.server_name_or_config}")
        except Exception as e:
            return McpResponse(result="", error=f"Failed to install MCP server: {str(e)}")

    async def _process_request(self):
        hub = McpHub()
        await hub.initialize()

        while self._running:
            try:
                request = await self._request_queue.get()
                if request is None:
                    break

                if isinstance(request, McpInstallRequest):
                    response = await self._install_server(request, hub)
                    await self._response_queue.put(response)

                elif isinstance(request, McpRemoveRequest):
                    try:
                        await hub.remove_server_config(request.server_name)
                        await self._response_queue.put(McpResponse(result=f"Successfully removed MCP server: {request.server_name}"))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(result="", error=f"Failed to remove MCP server: {str(e)}"))

                elif isinstance(request, McpListRequest):
                    try:
                        # Get built-in servers
                        builtin_servers = [
                            f"- Built-in: {name}" for name in MCP_BUILD_IN_SERVERS.keys()]

                        # Get external servers
                        external_servers = get_mcp_external_servers()
                        external_list = [
                            f"- External: {s.name} ({s.description})" for s in external_servers]

                        # Combine results
                        all_servers = builtin_servers + external_list
                        result = "Available MCP servers:\n" + \
                            "\n".join(all_servers)

                        await self._response_queue.put(McpResponse(result=result))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(result="", error=f"Failed to list servers: {str(e)}"))

                elif isinstance(request, McpListRunningRequest):
                    try:
                        running_servers = "\n".join(
                            [f"- {server.name}" for server in hub.get_servers()])
                        await self._response_queue.put(McpResponse(result=running_servers))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(result="", error=f"Failed to list running servers: {str(e)}"))

                elif isinstance(request, McpRefreshRequest):
                    try:
                        if request.name:
                            await hub.refresh_server_connection(request.name)
                        else:
                            await hub.initialize()
                        await self._response_queue.put(McpResponse(result="Successfully refreshed MCP server connections"))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(result="", error=f"Failed to refresh MCP servers: {str(e)}"))

                else:
                    llm = byzerllm.ByzerLLM.from_default_model(
                        model=request.model)
                    mcp_executor = McpExecutor(hub, llm)
                    conversations = [
                        {"role": "user", "content": request.query}]
                    _, results = await mcp_executor.run(conversations)
                    if not results:
                        await self._response_queue.put(McpResponse(result="[No Result]", error="No results"))
                    results_str = "\n\n".join(
                        mcp_executor.format_mcp_result(result) for result in results)
                    await self._response_queue.put(McpResponse(result=results_str))
            except Exception as e:
                await self._response_queue.put(McpResponse(result="", error=str(e)))

    def send_request(self, request: McpRequest) -> McpResponse:
        async def _send():
            await self._request_queue.put(request)
            return await self._response_queue.get()

        future = asyncio.run_coroutine_threadsafe(_send(), self._loop)
        return future.result()


# Global MCP server instance
_mcp_server = None


def get_mcp_server():
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = McpServer()
        _mcp_server.start()
    return _mcp_server
