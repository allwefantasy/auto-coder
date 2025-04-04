import asyncio
from asyncio import Queue as AsyncQueue
import threading
from typing import List
import os
import time
from loguru import logger
import json

from autocoder.common.mcp_hub import McpHub, MCP_BUILD_IN_SERVERS
from autocoder.common.mcp_tools import McpExecutor
from autocoder.utils.llms import get_single_llm
from autocoder.chat_auto_coder_lang import get_message_with_format
from autocoder.common.mcp_server_types import (
    McpRequest, McpInstallRequest, McpRemoveRequest, McpListRequest, 
    McpListRunningRequest, McpRefreshRequest, McpServerInfoRequest, 
    McpResponse, ServerInfo, InstallResult, RemoveResult, ListResult, 
    ListRunningResult, RefreshResult, QueryResult, ErrorResult, ServerConfig,
    ExternalServerInfo, McpExternalServer
)
from autocoder.common.mcp_server_install import McpServerInstaller

class McpServer:
    def __init__(self):
        self._request_queue = AsyncQueue()
        self._response_queue = AsyncQueue()
        self._running = False
        self._task = None
        self._loop = None
        self._installer = McpServerInstaller()

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

    async def _process_request(self):
        hub = McpHub()
        await hub.initialize()

        while self._running:
            try:
                request = await self._request_queue.get()
                if request is None:
                    break

                if isinstance(request, McpInstallRequest):
                    response = await self._installer.install_server(request, hub)
                    await self._response_queue.put(response)

                elif isinstance(request, McpRemoveRequest):
                    try:
                        await hub.remove_server_config(request.server_name)
                        await self._response_queue.put(McpResponse(
                            result=get_message_with_format("mcp_remove_success", result=request.server_name),
                            raw_result=RemoveResult(
                                success=True,
                                server_name=request.server_name
                            )
                        ))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(
                            result="", 
                            error=get_message_with_format("mcp_remove_error", error=str(e)),
                            raw_result=RemoveResult(
                                success=False,
                                server_name=request.server_name,
                                error=str(e)
                            )
                        ))

                elif isinstance(request, McpListRequest):
                    try:
                        # Get built-in servers
                        builtin_servers = [
                            f"- Built-in: {name}" for name in MCP_BUILD_IN_SERVERS.keys()]

                        # Get external servers
                        external_servers = self._installer.get_mcp_external_servers()
                        external_list = [
                            f"- External: {s.name} ({s.description})" for s in external_servers]

                        # Combine results
                        all_servers = builtin_servers + external_list
                        result =  "\n".join(all_servers)
                        
                        raw_result = ListResult(
                            builtin_servers=list(MCP_BUILD_IN_SERVERS.keys()),
                            external_servers=[
                                ExternalServerInfo(name=s.name, description=s.description) 
                                for s in external_servers
                            ]
                        )

                        await self._response_queue.put(McpResponse(result=result, raw_result=raw_result))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(
                            result="", 
                            error=get_message_with_format("mcp_list_builtin_error", error=str(e)),
                            raw_result=ListResult(error=str(e))
                        ))

                elif isinstance(request, McpServerInfoRequest):
                    try:
                        llm = get_single_llm(request.model, product_mode=request.product_mode)
                        mcp_executor = McpExecutor(hub, llm)
                        result = mcp_executor.get_connected_servers_info()
                        await self._response_queue.put(McpResponse(result=result, raw_result=result))
                    except Exception as e:
                        import traceback
                        traceback.print_exc()
                        await self._response_queue.put(McpResponse(
                            result="", 
                            error=get_message_with_format("mcp_server_info_error", error=str(e)),
                            raw_result=ErrorResult(error=str(e))
                        ))

                elif isinstance(request, McpListRunningRequest):
                    try:
                        servers = hub.get_servers()
                        running_servers = "\n".join(
                            [f"- {server.name}" for server in servers])
                        result = running_servers if running_servers else ""
                        await self._response_queue.put(McpResponse(
                            result=result,
                            raw_result=ListRunningResult(
                                servers=[ServerInfo(name=server.name) for server in servers]
                            )
                        ))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(
                            result="", 
                            error=get_message_with_format("mcp_list_running_error", error=str(e)),
                            raw_result=ListRunningResult(error=str(e))
                        ))

                elif isinstance(request, McpRefreshRequest):
                    try:
                        if request.name:
                            await hub.refresh_server_connection(request.name)
                        else:
                            await hub.initialize()
                        await self._response_queue.put(McpResponse(
                            result=get_message_with_format("mcp_refresh_success"),
                            raw_result=RefreshResult(
                                success=True,
                                name=request.name
                            )
                        ))
                    except Exception as e:
                        await self._response_queue.put(McpResponse(
                            result="", 
                            error=get_message_with_format("mcp_refresh_error", error=str(e)),
                            raw_result=RefreshResult(
                                success=False,
                                name=request.name,
                                error=str(e)
                            )
                        ))

                else:
                    if not request.query.strip():
                        await self._response_queue.put(McpResponse(
                            result="", 
                            error=get_message_with_format("mcp_query_empty"),
                            raw_result=QueryResult(
                                success=False,
                                error="Empty query"
                            )
                        ))
                        continue

                    llm = get_single_llm(request.model, product_mode=request.product_mode)
                    mcp_executor = McpExecutor(hub, llm)
                    conversations = [
                        {"role": "user", "content": request.query}]
                    _, results = await mcp_executor.run(conversations)

                    if not results:
                        await self._response_queue.put(McpResponse(
                            result=get_message_with_format("mcp_error_title"),
                            error="No results",
                            raw_result=QueryResult(
                                success=False,
                                error="No results"
                            )
                        ))
                    else:
                        results_str = "\n\n".join(
                            mcp_executor.format_mcp_result(result) for result in results)
                        await self._response_queue.put(McpResponse(
                            result=get_message_with_format("mcp_response_title") + "\n" + results_str,
                            raw_result=QueryResult(
                                success=True,
                                results=results
                            )
                        ))
            except Exception as e:
                await self._response_queue.put(McpResponse(
                    result="", 
                    error=get_message_with_format("mcp_error_title") + ": " + str(e),
                    raw_result=ErrorResult(error=str(e))
                ))

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


