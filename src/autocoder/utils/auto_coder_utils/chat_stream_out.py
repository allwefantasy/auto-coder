from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.markdown import Markdown
from rich.layout import Layout
from threading import Thread, Lock
from queue import Queue, Empty
from typing import Generator, List, Dict, Any, Optional, Tuple, Literal
from autocoder.utils.request_queue import RequestValue, RequestOption, StreamValue
from autocoder.utils.request_queue import request_queue
import time

MAX_HISTORY_LINES = 40  # 最大保留历史行数

class StreamRenderer:
    def __init__(self, title: str):
        self.title = title
        self.content = ""
        self.lock = Lock()
        self.is_complete = False
        
    def update(self, content: str):
        with self.lock:
            self.content += content
            
    def get_content(self) -> str:
        with self.lock:
            return self.content
            
    def complete(self):
        with self.lock:
            self.is_complete = True

class MultiStreamRenderer:
    def __init__(self, stream_titles: List[str], layout: str = "horizontal", console: Optional[Console] = None):
        """
        Initialize multi-stream renderer
        
        Args:
            stream_titles: List of titles for each stream
            layout: "horizontal" or "vertical"
            console: Rich console instance
        """
        if console is None:
            console = Console(force_terminal=True, color_system="auto")
            
        self.console = console
        self.layout_type = layout
        self.streams = [StreamRenderer(title) for title in stream_titles]
        self.layout = Layout()
        
        # Create named layouts for each stream
        self.stream_layouts = [Layout(name=f"stream{i}") for i in range(len(stream_titles))]
        
        # Configure layout
        if layout == "horizontal":
            self.layout.split_row(*self.stream_layouts)
        else:
            self.layout.split_column(*self.stream_layouts)
            
    def _process_stream(self, 
                       stream_idx: int, 
                       stream_generator: Generator[Tuple[str, Dict[str, Any]], None, None]):
        """Process a single stream in a separate thread"""
        stream = self.streams[stream_idx]
        try:
            for content, meta in stream_generator:
                if content:
                    stream.update(content)
        finally:
            stream.complete()

    def render_streams(self, 
                      stream_generators: List[Generator[Tuple[str, Dict[str, Any]], None, None]]) -> List[str]:
        """
        Render multiple streams simultaneously
        
        Args:
            stream_generators: List of stream generators to render
            
        Returns:
            List of final content from each stream
        """
        assert len(stream_generators) == len(self.streams), "Number of generators must match number of streams"
        
        # Start processing threads
        threads = []
        for i, generator in enumerate(stream_generators):
            thread = Thread(target=self._process_stream, args=(i, generator))
            thread.daemon = True
            thread.start()
            threads.append(thread)
            
        try:
            with Live(self.layout, console=self.console, refresh_per_second=10) as live:
                while any(not stream.is_complete for stream in self.streams):
                    # Update all panels
                    for i, stream in enumerate(self.streams):
                        panel = Panel(
                            Markdown(stream.get_content() or "Waiting..."),
                            title=stream.title,
                            border_style="green" if not stream.is_complete else "blue"
                        )
                        
                        # Update appropriate layout section
                        self.stream_layouts[i].update(panel)
                        
                    time.sleep(0.1)  # Prevent excessive CPU usage
                    
        except KeyboardInterrupt:
            print("\nStopping streams...")
            
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
            
        return [stream.get_content() for stream in self.streams]

def multi_stream_out(
    stream_generators: List[Generator[Tuple[str, Dict[str, Any]], None, None]],
    titles: List[str],
    layout: str = "horizontal",
    console: Optional[Console] = None
) -> List[str]:
    """
    Render multiple streams with Rich
    
    Args:
        stream_generators: List of stream generators
        titles: List of titles for each stream
        layout: "horizontal" or "vertical"
        console: Optional Rich console instance
        
    Returns:
        List of final content from each stream
    """
    renderer = MultiStreamRenderer(titles, layout, console)
    return renderer.render_streams(stream_generators)


def stream_out(
    stream_generator: Generator[Tuple[str, Dict[str, Any]], None, None],
    request_id: Optional[str] = None,    
    console: Optional[Console] = None
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    处理流式输出事件并在终端中展示
    
    Args:
        stream_generator: 生成流式输出的生成器
        request_id: 请求ID,用于更新请求队列        
        console: Rich Console对象
        
    Returns:
        Tuple[str, Dict[str, Any]]: 返回完整的响应内容和最后的元数据
    """
    if console is None:
        console = Console(force_terminal=True, color_system="auto", height=None)
        
    lines_buffer = []  # 存储历史行
    current_line = ""  # 当前行
    assistant_response = ""
    last_meta = None
    
    try:
        with Live(
            Panel("", title="Response", border_style="green"),
            refresh_per_second=4,
            console=console
        ) as live:
            for res in stream_generator:
                last_meta = res[1]                
                content = res[0]
                reasoning_content = last_meta.reasoning_content

                if reasoning_content == "" and content == "":
                    continue
            
                assistant_response += content

                display_delta = reasoning_content if reasoning_content else content
                
                # 处理所有行
                parts = (current_line + display_delta).split("\n")
                
                # 最后一部分是未完成的新行
                if len(parts) > 1:
                    # 将完整行加入缓冲区
                    lines_buffer.extend(parts[:-1])
                    # 保留最大行数限制
                    if len(lines_buffer) > MAX_HISTORY_LINES:
                        del lines_buffer[0:len(lines_buffer) - MAX_HISTORY_LINES]
                
                # 更新当前行
                current_line = parts[-1]
                
                # 构建显示内容 = 历史行 + 当前行
                display_content = "\n".join(lines_buffer[-MAX_HISTORY_LINES:] + [current_line])
                
                if request_id and request_queue:
                    request_queue.add_request(
                        request_id,
                        RequestValue(
                            value=StreamValue(value=[content]),
                            status=RequestOption.RUNNING,
                        ),
                    )
                    
                live.update(
                    Panel(
                        Markdown(display_content),
                        title="Response",
                        border_style="green",
                        height=min(50, live.console.height - 4)
                    )
                )
            
            # 处理最后一行的内容
            if current_line:
                lines_buffer.append(current_line)
            
            # 最终显示结果
            live.update(
                Panel(
                    Markdown(assistant_response),
                    title="Final Response",
                    border_style="blue"
                )
            )
            
    except Exception as e:
        console.print(Panel(
            f"Error: {str(e)}",  
            title="Error",
            border_style="red"
        ))
        
        if request_id and request_queue:
            request_queue.add_request(
                request_id,
                RequestValue(
                    value=StreamValue(value=[str(e)]), 
                    status=RequestOption.FAILED
                ),
            )
            
    finally:
        if request_id and request_queue:
            request_queue.add_request(
                request_id,
                RequestValue(
                    value=StreamValue(value=[""]), 
                    status=RequestOption.COMPLETED
                ),
            )
            
    return assistant_response, last_meta
