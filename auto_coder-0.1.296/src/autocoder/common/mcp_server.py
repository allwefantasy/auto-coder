import asyncio
from asyncio import Queue as AsyncQueue
import threading
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from autocoder.common.mcp_hub import McpHub
from autocoder.common.mcp_tools import McpExecutor
from autocoder.common.mcp_hub import MCP_BUILD_IN_SERVERS
import json
import os
import time
from pydantic import BaseModel
import sys
from loguru import logger
from autocoder.utils.llms import get_single_llm
from autocoder.chat_auto_coder_lang import get_message_with_format

@dataclass
class McpRequest:
    query: str
    model: Optional[str] = None
    product_mode: Optional[str] = None

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
class McpServerInfoRequest:
    """Request to get MCP server info"""
    model: Optional[str] = None
    product_mode: Optional[str] = None


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
            with open(cache_file, "r",encoding="utf-8") as f:
                raw_data = json.load(f)
                return [McpExternalServer(**item) for item in raw_data]

    # Fetch from GitHub
    url = "https://raw.githubusercontent.com/michaellatman/mcp-get/refs/heads/main/packages/package-list.json"
    try:
        import requests
        response = requests.get(url)
        if response.status_code == 200:
            raw_data = response.json()
            with open(cache_file, "w",encoding="utf-8") as f:
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

    def _deep_merge_dicts(self, dict1, dict2):
        """
        深度合并两个字典，包括嵌套的字典
        dict1是基础字典，dict2是优先字典（当有冲突时保留dict2的值）
        """
        result = dict1.copy()
        for key, value in dict2.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # 如果两个字典都包含相同的键，并且两个值都是字典，则递归合并
                result[key] = self._deep_merge_dicts(result[key], value)
            else:
                # 否则，使用dict2的值覆盖或添加到结果
                result[key] = value
        return result

    def _parse_command_line_args(self, server_name_or_config: str) -> tuple[str, dict]:
        """Parse command-line style arguments into name and config"""
        name = ""
        config = {}
        args = server_name_or_config.strip().split()
        i = 0
        while i < len(args):
            if args[i] == "--name" and i + 1 < len(args):
                name = args[i + 1]
                i += 2
            elif args[i] == "--command" and i + 1 < len(args):
                config["command"] = args[i + 1]
                i += 2
            elif args[i] == "--args":
                config["args"] = []
                i += 1
                while i < len(args) and not args[i].startswith("--"):
                    config["args"].append(args[i])
                    i += 1
            elif args[i] == "--env":
                config["env"] = {}
                i += 1
                while i < len(args) and not args[i].startswith("--"):
                    if "=" in args[i]:
                        key, value = args[i].split("=", 1)
                        config["env"][key] = value
                    i += 1
            else:
                i += 1                
        
        template_config = {}
        
        if name in MCP_BUILD_IN_SERVERS:
            template_config = MCP_BUILD_IN_SERVERS[name]
        else:
            # 查找外部server
            external_servers = get_mcp_external_servers()
            for s in external_servers:
                if s.name == name:
                    if s.runtime == "python":
                        self._install_python_package(name)
                        template_config = {
                            "command": "python",
                            "args": [
                                "-m", name.replace("-", "_")
                            ],
                        }
                    elif s.runtime == "node":
                        self._install_node_package(name)
                        template_config = {
                            "command": "npx",
                            "args": [
                                "-y",
                                "-g",
                                name
                            ]
                        }
                    break  

        # 深度合并两个配置，以用户配置为主
        config = self._deep_merge_dicts(template_config, config)

        if not config.get("args") and (name.startswith("@") or config.get("command") in ["npx", "npm"]):
            config["args"] = ["-y", "-g", name]            
        
        ## 如果有模板，则无需再次安装，处理模板的时候会自动安装
        if not template_config:    
            # Install package if needed
            if name.startswith("@") or config.get("command") in ["npx", "npm"]:            
                self._install_node_package(name)
            else:
                self._install_python_package(name)
            
        return name, config
        
    def _parse_json_config(self, server_name_or_config: str) -> tuple[str, dict]:
        """Parse JSON configuration into name and config"""
        raw_config = json.loads(server_name_or_config)
        # 用户给了一个完整的配置
        if "mcpServers" in raw_config:
            raw_config = raw_config["mcpServers"]

        # 取第一个server 配置
        config = list(raw_config.values())[0]
        name = list(raw_config.keys())[0]
        if name.startswith("@") or config["command"] in ["npx", "npm"]:
            for item in config["args"]:
                if name in item:
                    self._install_node_package(item)                    
        else:
            self._install_python_package(name)
            
        return name, config
            

    async def _install_server(self, request: McpInstallRequest, hub: McpHub) -> McpResponse:
        """Install an MCP server with module dependency check"""
        name = ""
        config = {}
        try:
            server_name_or_config = request.server_name_or_config
            
            # Try different parsing methods
            if server_name_or_config.strip().startswith("--"):
                # Command-line style arguments
                name, config = self._parse_command_line_args(server_name_or_config)
            else:
                try:
                    # Try parsing as JSON
                    name, config = self._parse_json_config(server_name_or_config)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse JSON config: {server_name_or_config}")
                    pass
            
            if not name:
                raise ValueError(
                    "MCP server name is not available in MCP_BUILD_IN_SERVERS or external servers")

            logger.info(f"Installing MCP server: {name} with config: {config}")
            if not config:
                raise ValueError(f"MCP server {name} config is not available")

            is_success = await hub.add_server_config(name, config)
            if is_success:
                return McpResponse(result=get_message_with_format("mcp_install_success", result=request.server_name_or_config))
            else:
                return McpResponse(result="", error=get_message_with_format("mcp_install_error", error="Failed to establish connection"))
        except Exception as e:
            return McpResponse(result="", error=get_message_with_format("mcp_install_error", error=str(e)))

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
                        await self._response_queue.put(McpResponse(
                            result=get_message_with_format("mcp_remove_success", result=request.server_name)))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(
                            result="", error=get_message_with_format("mcp_remove_error", error=str(e))))

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
                        result =  "\n".join(all_servers)

                        await self._response_queue.put(McpResponse(result=result))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(
                            result="", error=get_message_with_format("mcp_list_builtin_error", error=str(e))))

                elif isinstance(request, McpServerInfoRequest):
                    try:
                        llm = get_single_llm(request.model, product_mode=request.product_mode)
                        mcp_executor = McpExecutor(hub, llm)
                        result = mcp_executor.get_connected_servers_info()
                        await self._response_queue.put(McpResponse(result=result))
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        await self._response_queue.put(McpResponse(
                            result="", error=get_message_with_format("mcp_server_info_error", error=str(e))))

                elif isinstance(request, McpListRunningRequest):
                    try:
                        running_servers = "\n".join(
                            [f"- {server.name}" for server in hub.get_servers()])
                        result = running_servers if running_servers else ""
                        await self._response_queue.put(McpResponse(result=result))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(
                            result="", error=get_message_with_format("mcp_list_running_error", error=str(e))))

                elif isinstance(request, McpRefreshRequest):
                    try:
                        if request.name:
                            await hub.refresh_server_connection(request.name)
                        else:
                            await hub.initialize()
                        await self._response_queue.put(McpResponse(
                            result=get_message_with_format("mcp_refresh_success")))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(
                            result="", error=get_message_with_format("mcp_refresh_error", error=str(e))))

                else:
                    if not request.query.strip():
                        await self._response_queue.put(McpResponse(
                            result="", error=get_message_with_format("mcp_query_empty")))
                        continue
                        
                    llm = get_single_llm(request.model, product_mode=request.product_mode)
                    mcp_executor = McpExecutor(hub, llm)
                    conversations = [
                        {"role": "user", "content": request.query}]
                    _, results = await mcp_executor.run(conversations)
                    
                    if not results:
                        await self._response_queue.put(McpResponse(
                            result=get_message_with_format("mcp_error_title"), 
                            error="No results"))
                    else:
                        results_str = "\n\n".join(
                            mcp_executor.format_mcp_result(result) for result in results)
                        await self._response_queue.put(McpResponse(
                            result=get_message_with_format("mcp_response_title") + "\n" + results_str))
            except Exception as e:
                await self._response_queue.put(McpResponse(
                    result="", error=get_message_with_format("mcp_error_title") + ": " + str(e)))

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
