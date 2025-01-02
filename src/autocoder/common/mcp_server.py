import asyncio
import queue
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
        self._request_queue = queue.Queue()
        self._response_queue = queue.Queue()
        self._running = False
        self._thread = None
        
    def start(self):
        if self._running:
            return
            
        self._running = True
        self._thread = threading.Thread(target=self._run_server)
        self._thread.daemon = True
        self._thread.start()
        
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join()
            
    def _run_server(self):
        while self._running:
            try:
                request = self._request_queue.get(timeout=1)
                if request is None:
                    continue
                    
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    result = loop.run_until_complete(self._process_request(request))
                    self._response_queue.put(McpResponse(result=result))
                except Exception as e:
                    self._response_queue.put(McpResponse(result="", error=str(e)))
                finally:
                    loop.close()
                    
            except queue.Empty:
                continue
            except Exception as e:
                print(f"Error in MCP server: {e}")
                
    async def _process_request(self, request: McpRequest) -> str:
        hub = McpHub()
        await hub.initialize()
        
        llm = byzerllm.ByzerLLM.from_default_model(request.model) if request.model else byzerllm.ByzerLLM()
        
        mcp_executor = McpExecutor(hub, llm)
        conversations = [{"role": "user", "content": request.query}]
        _, results = await mcp_executor.run(conversations)
        results_str = "\n\n".join(mcp_executor.format_mcp_result(result) for result in results)
        return results_str
        
    def send_request(self, request: McpRequest) -> McpResponse:
        self._request_queue.put(request)
        return self._response_queue.get()

# Global MCP server instance
_mcp_server = None

def get_mcp_server():
    global _mcp_server
    if _mcp_server is None:
        _mcp_server = McpServer()
        _mcp_server.start()
    return _mcp_server