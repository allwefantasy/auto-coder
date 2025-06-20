"""
Auto-Coder SDK 核心封装类

提供统一的查询接口，处理同步和异步调用。
"""

from typing import AsyncIterator, Optional, Dict, Any, Iterator
import asyncio
import os
import time
from concurrent.futures import ThreadPoolExecutor

# Rich 渲染相关导入
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn

from ..models.options import AutoCodeOptions
from ..models.messages import Message
from ..models.responses import StreamEvent, CodeModificationResult
from ..exceptions import BridgeError
from .bridge import AutoCoderBridge


class AutoCoderCore:
    """AutoCoder核心封装类"""
    
    def __init__(self, options: AutoCodeOptions):
        """
        初始化AutoCoderCore
        
        Args:
            options: 配置选项
        """
        self.options = options
        cwd_str = str(options.cwd) if options.cwd is not None else os.getcwd()
        self.bridge = AutoCoderBridge(cwd_str)
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._console = Console()
    
    def _render_stream_event(self, event: StreamEvent, show_terminal: bool = True) -> None:
        """
        渲染流式事件到终端
        
        Args:
            event: 流式事件
            show_terminal: 是否显示到终端
        """
        if not show_terminal:
            return
            
        try:
            if event.event_type == "start":
                project_name = os.path.basename(os.path.abspath(self.options.cwd or os.getcwd()))
                self._console.rule(f"[bold cyan]Starting Auto-Coder: {project_name}[/]")
                query = event.data.get("query", "")
                if query:
                    self._console.print(Panel(
                        f"[bold]Query:[/bold]\n{query}", 
                        title="🎯 Objective", 
                        border_style="blue"
                    ))
                    
            elif event.event_type == "llm_thinking":
                text = event.data.get("text", "")
                if text.strip():
                    self._console.print(f"[grey50]{text}[/grey50]", end="")
                    
            elif event.event_type == "llm_output":
                text = event.data.get("text", "")
                if text.strip():
                    self._console.print(text, end="")
                        
            elif event.event_type == "tool_call":
                tool_name = event.data.get("tool_name", "Unknown Tool")
                tool_args = event.data.get("args", {})
                display_content = self._format_tool_display(tool_name, tool_args)
                self._console.print(Panel(
                    display_content, 
                    title=f"🛠️ Action: {tool_name}", 
                    border_style="blue", 
                    title_align="left"
                ))
                
            elif event.event_type == "tool_result":
                tool_name = event.data.get("tool_name", "Unknown Tool")
                success = event.data.get("success", True)
                message = event.data.get("message", "")
                content = event.data.get("content")
                
                title = f"✅ Tool Result: {tool_name}" if success else f"❌ Tool Result: {tool_name}"
                border_style = "green" if success else "red"
                
                base_content = f"[bold]Status:[/bold] {'Success' if success else 'Failure'}\n"
                base_content += f"[bold]Message:[/bold] {message}\n"
                
                # 处理内容显示
                if content is not None:
                    formatted_content = self._format_tool_result_content(content, tool_name)
                    if isinstance(formatted_content, Syntax):
                        self._console.print(Panel(base_content, title=title, border_style=border_style, title_align="left"))
                        self._console.print(formatted_content)
                    else:
                        base_content += f"\n{formatted_content}"
                        self._console.print(Panel(base_content, title=title, border_style=border_style, title_align="left"))
                else:
                    self._console.print(Panel(base_content, title=title, border_style=border_style, title_align="left"))
                    
            elif event.event_type == "completion":
                result = event.data.get("result", "Task completed successfully")
                self._console.print(Panel(
                    Markdown(result), 
                    title="🏁 Task Completion", 
                    border_style="green", 
                    title_align="left"
                ))
                
            elif event.event_type == "plan_mode_respond":
                result = event.data.get("result", "Plan completed")
                self._console.print(Panel(
                    Markdown(result), 
                    title="🏁 Plan Completion", 
                    border_style="green", 
                    title_align="left"
                ))
                
            elif event.event_type == "token_usage":
                usage = event.data.get("usage", {})
                if usage:
                    self._console.print(f"[dim]Token usage: {usage}[/dim]")
                    
            elif event.event_type == "window_change":
                tokens_used = event.data.get("tokens_used", 0)
                if tokens_used > 0:
                    self._console.print(f"[dim]Window tokens: {tokens_used}[/dim]")
                    
            elif event.event_type == "conversation_id":
                conversation_id = event.data.get("conversation_id", "")
                if conversation_id:
                    self._console.print(f"[dim]Conversation ID: {conversation_id}[/dim]")
                    
            elif event.event_type == "content":
                content = event.data.get("content", "")
                if content.strip():
                    # 检查是否是思考过程（通常包含特定标记）
                    if any(marker in content.lower() for marker in ["thinking", "analyzing", "考虑", "分析"]):
                        self._console.print(f"[grey50]{content}[/grey50]", end="")
                    else:
                        self._console.print(content, end="")
                        
            elif event.event_type == "file_modified":
                files = event.data.get("files", [])
                if files:
                    files_str = "\n".join([f"  - {f}" for f in files])
                    self._console.print(Panel(
                        f"[bold]Modified Files:[/bold]\n{files_str}", 
                        title="📝 File Changes", 
                        border_style="yellow", 
                        title_align="left"
                    ))
                    
            elif event.event_type == "file_created":
                files = event.data.get("files", [])
                if files:
                    files_str = "\n".join([f"  - {f}" for f in files])
                    self._console.print(Panel(
                        f"[bold]Created Files:[/bold]\n{files_str}", 
                        title="📄 New Files", 
                        border_style="green", 
                        title_align="left"
                    ))
                    
            elif event.event_type == "file_deleted":
                files = event.data.get("files", [])
                if files:
                    files_str = "\n".join([f"  - {f}" for f in files])
                    self._console.print(Panel(
                        f"[bold]Deleted Files:[/bold]\n{files_str}", 
                        title="🗑️ Removed Files", 
                        border_style="red", 
                        title_align="left"
                    ))
                    
            elif event.event_type == "end":
                status = event.data.get("status", "completed")
                if status == "completed":
                    self._console.rule("[bold green]Auto-Coder Finished Successfully[/]")
                else:
                    self._console.rule(f"[bold yellow]Auto-Coder Finished: {status}[/]")
                    
            elif event.event_type == "error":
                error = event.data.get("error", "Unknown error")
                error_type = event.data.get("error_type", "Error")
                self._console.print(Panel(
                    f"[bold red]Error Type:[/bold red] {error_type}\n[bold red]Message:[/bold red] {error}", 
                    title="🔥 Error", 
                    border_style="red", 
                    title_align="left"
                ))
                
        except Exception as e:
            # 渲染错误不应该影响主流程
            self._console.print(f"[dim red]Render error: {str(e)}[/dim red]")
    
    def _format_tool_display(self, tool_name: str, tool_args: Dict[str, Any]) -> str:
        """
        格式化工具调用显示内容
        
        Args:
            tool_name: 工具名称
            tool_args: 工具参数
            
        Returns:
            str: 格式化后的显示内容
        """
        if not tool_args:
            return f"[bold]Tool:[/bold] {tool_name}"
        
        content_parts = [f"[bold]Tool:[/bold] {tool_name}"]
        
        for key, value in tool_args.items():
            if isinstance(value, str) and len(value) > 100:
                value = f"{value[:50]}...{value[-50:]}"
            content_parts.append(f"[bold]{key}:[/bold] {value}")
        
        return "\n".join(content_parts)
    
    def _format_tool_result_content(self, content: Any, tool_name: str = "") -> str | Syntax:
        """
        格式化工具结果内容
        
        Args:
            content: 结果内容
            tool_name: 工具名称（用于推断语法类型）
            
        Returns:
            str | Syntax: 格式化后的内容或语法高亮对象
        """
        def _truncate_content(content_str: str) -> str:
            if len(content_str) > 500:
                return f"{content_str[:200]}\n...\n{content_str[-200:]}"
            return content_str
        
        try:
            if isinstance(content, (dict, list)):
                import json
                content_str = json.dumps(content, indent=2, ensure_ascii=False)
                return Syntax(_truncate_content(content_str), "json", theme="default", line_numbers=False)
                
            elif isinstance(content, str):
                # 检查是否是多行内容或代码
                if '\n' in content or content.strip().startswith('<') or len(content) > 200:
                    # 推断语法类型
                    lexer = "text"
                    if "ReadFile" in tool_name:
                        if any(ext in content for ext in [".py", "python"]):
                            lexer = "python"
                        elif any(ext in content for ext in [".js", "javascript"]):
                            lexer = "javascript"
                        elif any(ext in content for ext in [".ts", "typescript"]):
                            lexer = "typescript"
                        elif any(ext in content for ext in [".html", "<!DOCTYPE", "<html"]):
                            lexer = "html"
                        elif any(ext in content for ext in [".css", "{"]):
                            lexer = "css"
                        elif any(ext in content for ext in [".json", "{"]):
                            lexer = "json"
                        elif any(ext in content for ext in [".xml", "<?xml"]):
                            lexer = "xml"
                        elif any(ext in content for ext in [".md", "#"]):
                            lexer = "markdown"
                    elif "ExecuteCommand" in tool_name or "Shell" in tool_name:
                        lexer = "shell"
                    elif content.strip().startswith('{') or content.strip().startswith('['):
                        lexer = "json"
                    
                    return Syntax(_truncate_content(content), lexer, theme="default", line_numbers=True)
                else:
                    return _truncate_content(content)
            else:
                return _truncate_content(str(content))
                
        except Exception:
            return _truncate_content(str(content))
    
    async def query_stream(self, prompt: str, show_terminal: bool = True) -> AsyncIterator[Message]:
        """
        异步流式查询 - 使用 run_auto_command
        
        Args:
            prompt: 查询提示
            show_terminal: 是否显示到终端
            
        Yields:
            Message: 响应消息流
            
        Raises:
            BridgeError: 桥接层错误
        """
        try:
            # 先返回用户消息
            user_message = Message(role="user", content=prompt)
            yield user_message
            
            # 在线程池中执行同步调用
            loop = asyncio.get_event_loop()
            
            # 使用 run_auto_command 进行代码修改
            event_stream = await loop.run_in_executor(
                self._executor,
                self._sync_run_auto_command,
                prompt
            )
            
            # 处理事件流并转换为消息
            assistant_content = ""
            for event in event_stream:
                # 渲染事件到终端
                self._render_stream_event(event, show_terminal)
                
                if event.event_type == "content":
                    content = event.data.get("content", "")
                    assistant_content += content
                    
                    # 返回增量消息
                    yield Message(
                        role="assistant",
                        content=content,
                        metadata={
                            "event_type": event.event_type,
                            "model": self.options.model,
                            "temperature": self.options.temperature,
                            "is_incremental": True
                        }
                    )
                elif event.event_type == "end":
                    # 返回最终完整消息
                    yield Message(
                        role="assistant",
                        content=assistant_content,
                        metadata={
                            "event_type": event.event_type,
                            "model": self.options.model,
                            "temperature": self.options.temperature,
                            "is_final": True,
                            "status": event.data.get("status", "completed")
                        }
                    )
                elif event.event_type == "error":
                    # 返回错误消息
                    yield Message(
                        role="assistant",
                        content=f"Error: {event.data.get('error', 'Unknown error')}",
                        metadata={
                            "event_type": event.event_type,
                            "error_type": event.data.get("error_type", "Unknown"),
                            "is_error": True
                        }
                    )
                    
                # 添加小延迟以改善视觉效果
                if show_terminal:
                    time.sleep(0.05)
            
        except Exception as e:
            raise BridgeError(f"Query stream failed: {str(e)}", original_error=e)
    
    def query_sync(self, prompt: str, show_terminal: bool = True) -> str:
        """
        同步查询 - 使用 run_auto_command
        
        Args:
            prompt: 查询提示
            show_terminal: 是否显示到终端
            
        Returns:
            str: 响应内容
            
        Raises:
            BridgeError: 桥接层错误
        """
        try:
            event_stream = self._sync_run_auto_command(prompt)
            
            # 收集所有内容
            content_parts = []
            for event in event_stream:
                # 渲染事件到终端
                self._render_stream_event(event, show_terminal)
                
                if event.event_type == "content":
                    content_parts.append(event.data.get("content", ""))
                elif event.event_type == "error":
                    raise BridgeError(f"Query failed: {event.data.get('error', 'Unknown error')}")
                
                # 添加小延迟以改善视觉效果
                if show_terminal:
                    time.sleep(0.05)
            
            return "".join(content_parts)
            
        except Exception as e:
            raise BridgeError(f"Sync query failed: {str(e)}", original_error=e)
    
    def modify_code(
        self, 
        prompt: str, 
        pre_commit: bool = False,
        extra_args: Optional[Dict[str, Any]] = None,
        show_terminal: bool = True
    ) -> CodeModificationResult:
        """
        代码修改接口 - 直接使用 run_auto_command
        
        Args:
            prompt: 修改提示
            pre_commit: 是否预提交
            extra_args: 额外参数
            show_terminal: 是否显示到终端
            
        Returns:
            CodeModificationResult: 修改结果
        """
        try:
            event_stream = self._sync_run_auto_command(
                prompt, 
                pre_commit=pre_commit, 
                extra_args=extra_args
            )
            
            # 分析事件流，提取修改结果
            modified_files = []
            created_files = []
            deleted_files = []
            messages = []
            success = True
            error_details = None
            
            for event in event_stream:
                # 渲染事件到终端
                self._render_stream_event(event, show_terminal)
                
                if event.event_type == "content":
                    messages.append(event.data.get("content", ""))
                elif event.event_type == "error":
                    success = False
                    error_details = event.data.get("error", "Unknown error")
                elif event.event_type == "file_modified":
                    modified_files.extend(event.data.get("files", []))
                elif event.event_type == "file_created":
                    created_files.extend(event.data.get("files", []))
                elif event.event_type == "file_deleted":
                    deleted_files.extend(event.data.get("files", []))
                
                # 添加小延迟以改善视觉效果
                if show_terminal:
                    time.sleep(0.05)
            
            return CodeModificationResult(
                success=success,
                message="".join(messages),
                modified_files=modified_files,
                created_files=created_files,
                deleted_files=deleted_files,
                error_details=error_details,
                metadata={
                    "pre_commit": pre_commit,
                    "extra_args": extra_args or {}
                }
            )
            
        except Exception as e:
            if show_terminal:
                self._console.print(Panel(
                    f"[bold red]FATAL ERROR:[/bold red]\n{str(e)}", 
                    title="🔥 System Error", 
                    border_style="red"
                ))
            return CodeModificationResult(
                success=False,
                message="",
                error_details=str(e),
                metadata={"exception_type": type(e).__name__}
            )
    
    async def modify_code_stream(
        self, 
        prompt: str, 
        pre_commit: bool = False,
        extra_args: Optional[Dict[str, Any]] = None,
        show_terminal: bool = True
    ) -> AsyncIterator[StreamEvent]:
        """
        异步流式代码修改接口
        
        Args:
            prompt: 修改提示
            pre_commit: 是否预提交
            extra_args: 额外参数
            show_terminal: 是否显示到终端
            
        Yields:
            StreamEvent: 修改事件流
        """
        try:
            loop = asyncio.get_event_loop()
            
            # 在线程池中执行同步调用
            event_stream = await loop.run_in_executor(
                self._executor,
                self._sync_run_auto_command,
                prompt,
                pre_commit,
                extra_args
            )
            
            # 处理并转发事件流
            for event in event_stream:
                # 渲染事件到终端
                self._render_stream_event(event, show_terminal)
                
                # 转发事件
                yield event
                
                # 添加小延迟以改善视觉效果
                if show_terminal:
                    time.sleep(0.05)
                
        except Exception as e:
            error_event = StreamEvent(
                event_type="error",
                data={"error": str(e), "error_type": type(e).__name__}
            )
            self._render_stream_event(error_event, show_terminal)
            yield error_event
    
    def _sync_run_auto_command(
        self, 
        prompt: str, 
        pre_commit: bool = False,
        extra_args: Optional[Dict[str, Any]] = None
    ) -> Iterator[StreamEvent]:
        """
        内部同步调用 run_auto_command
        
        Args:
            prompt: 查询提示
            pre_commit: 是否预提交
            extra_args: 额外参数
            
        Returns:
            Iterator[StreamEvent]: 事件流
        """
        return self.bridge.call_run_auto_command(
            query=prompt,
            pre_commit=pre_commit,
            extra_args=extra_args or {},
            stream=True
        )
    
    def get_session_manager(self):
        """
        获取会话管理器
        
        Returns:
            SessionManager: 会话管理器实例
        """
        from ..session.session_manager import SessionManager
        cwd_str = str(self.options.cwd) if self.options.cwd is not None else os.getcwd()
        return SessionManager(cwd_str)
    
    def get_project_memory(self) -> Dict[str, Any]:
        """
        获取项目内存状态
        
        Returns:
            Dict[str, Any]: 项目内存数据
        """
        return self.bridge.get_memory()
    
    def save_project_memory(self, memory_data: Dict[str, Any]) -> None:
        """
        保存项目内存状态
        
        Args:
            memory_data: 内存数据
        """
        self.bridge.save_memory(memory_data)
    
    def get_project_config(self) -> Dict[str, Any]:
        """
        获取项目配置
        
        Returns:
            Dict[str, Any]: 项目配置
        """
        return self.bridge.get_project_config()
    
    def __del__(self):
        """清理资源"""
        if hasattr(self, '_executor'):
            self._executor.shutdown(wait=False)





