import asyncio
from asyncio import Queue as AsyncQueue
import threading
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import byzerllm
from autocoder.common.mcp_hub import McpHub
from autocoder.common.mcp_tools import McpExecutor

@dataclass 
class McpRequest:
    query: str
    model: Optional[str] = None
    
@dataclass
class McpResponse:
    result: str
    error: Optional[str] = None

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
                
    async def _process_request(self):
        hub = McpHub()
        await hub.initialize()
        
        while self._running:
            try:
                request = await self._request_queue.get()
                if request is None:
                    break
                    
                llm = byzerllm.ByzerLLM.from_default_model(model=request.model)
                mcp_executor = McpExecutor(hub, llm)
                conversations = [{"role": "user", "content": request.query}]
                _, results = await mcp_executor.run(conversations)
                results_str = "\n\n".join(mcp_executor.format_mcp_result(result) for result in results)
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
