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
LAYOUT_TYPES = Literal["vertical", "horizontal"]

class StreamController:
    def __init__(self, layout_type: LAYOUT_TYPES = "vertical", console: Optional[Console] = None):
        self.console = console or Console(force_terminal=True, color_system="auto", height=24)  # 设置默认高度
        self.layout = Layout()
        self.queue = Queue()
        self.lock = Lock()
        self.running = True
        self.workers = []
        self.layout_type = layout_type
        self.stream_count = 0

    def _create_stream_panel(self, idx: int) -> Layout:
        """创建流面板布局"""
        panel = Layout(name=f"stream-{idx}", size="auto")
        # 设置默认高度和有效性校验
        current_height = self.console.height or 24  # 默认24行防止获取失败
        safe_height = max(min(50, current_height // 2 - 4), 5)  # 限制最小高度为5行
        panel.update(
            Panel(
                "", 
                title=f"Stream {idx+1}", 
                border_style="green",
                height=safe_height  # 确保数值有效
            )
        )
        return panel

    def prepare_layout(self, count: int):
        """准备动态布局结构"""        
        self.stream_count = count
        
        if self.layout_type == "vertical":
            split_panels = Layout()
            for i in range(count):
                split_panels.split_column(self._create_stream_panel(i))
        else:
            split_panels = Layout()
            for i in range(count):
                split_panels.split_row(self._create_stream_panel(i))
        
        self.layout.split(
            Layout(name="header", size=1),
            split_panels
        )

    def update_panel(self, idx: int, content: str, final: bool = False):
        """线程安全的面板更新方法"""
        with self.lock:
            if final:
                new_panel = Panel(
                    Markdown(content),
                    title=f"Final Stream {idx+1}",
                    border_style="blue"
                )
            else:
                new_panel = Panel(
                    Markdown(content),
                    title=f"Stream {idx+1}",
                    border_style="green",
                    height=min(50, self.console.height // 2 - 4)
                )

            panel_name = f"stream-{idx}"
            if panel_name in self.layout:
                layout = self.layout[panel_name]
                layout.update(new_panel)

def stream_worker(
    idx: int,
    generator: Generator[Tuple[str, Dict[str, Any]], None, None],
    controller: StreamController,
    request_id: Optional[str] = None
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """单个流处理工作线程"""
    lines_buffer = []
    current_line = ""
    assistant_response = ""
    last_meta = None
    
    try:
        for res in generator:
            content, meta = res
            last_meta = meta
            
            assistant_response += content
            display_delta = meta.get("reasoning_content", "") or content

            parts = (current_line + display_delta).split("\n")
            if len(parts) > 1:
                lines_buffer.extend(parts[:-1])
                if len(lines_buffer) > MAX_HISTORY_LINES:
                    del lines_buffer[0:len(lines_buffer) - MAX_HISTORY_LINES]
            
            current_line = parts[-1]
            display_content = "\n".join(lines_buffer[-MAX_HISTORY_LINES:] + [current_line])
            
            controller.queue.put((idx, display_content, False))
            
            if request_id and request_queue:
                request_queue.add_request(
                    request_id,
                    RequestValue(
                        value=StreamValue(value=[content]),
                        status=RequestOption.RUNNING,
                    ),
                )

        if current_line:
            lines_buffer.append(current_line)
        controller.queue.put((idx, assistant_response, True))
        return assistant_response, last_meta
    
    except Exception as e:
        error_content = f"Error: {str(e)}"
        controller.queue.put((idx, error_content, True))
        if request_id and request_queue:
            request_queue.add_request(
                request_id,
                RequestValue(
                    value=StreamValue(value=[str(e)]), 
                    status=RequestOption.FAILED
                ),
            )
        return assistant_response, last_meta
    finally:
        if request_id and request_queue:
            request_queue.add_request(
                request_id,
                RequestValue(
                    value=StreamValue(value=[""]), 
                    status=RequestOption.COMPLETED
                ),
            )

def multi_stream_out(
    stream_generators: List[Generator[Tuple[str, Dict[str, Any]], None, None]],
    request_ids: Optional[List[str]] = None,
    console: Optional[Console] = None,
    layout_type: LAYOUT_TYPES = "vertical"
) -> List[Tuple[str, Optional[Dict[str, Any]]]]:
    """
    多流并行输出处理器
    
    Args:
        stream_generators: 流处理器列表
        request_ids: 对应请求ID列表
        console: Rich Console对象
        layout_type: 布局类型 vertical/horizontal
        
    Returns:
        List[Tuple[str, Dict]]: 各流的处理结果
    """
    # 确保使用统一的console实例
    if console is None:
        console = Console(force_terminal=True, color_system="auto", height=24)
    controller = StreamController(layout_type, console=console)
    controller.prepare_layout(len(stream_generators))
    
    # 启动工作线程
    results = [None] * len(stream_generators)
    threads = []
    for idx, gen in enumerate(stream_generators):
        req_id = request_ids[idx] if request_ids and idx < len(request_ids) else None
        t = Thread(
            target=lambda i, g: results.__setitem__(i, stream_worker(i, g, controller, req_id)),
            args=(idx, gen)
        )
        t.start()
        threads.append(t)
    
    # 主渲染线程
    try:
        with Live(
            controller.layout, 
            console=console or controller.console,
            refresh_per_second=10,
            screen=True
        ) as live:
            while controller.running:
                updated = False
                try:
                    while True:  # 处理队列中的所有更新
                        idx, content, final = controller.queue.get_nowait()
                        controller.update_panel(idx, content, final)
                        updated = True
                except Empty:
                    pass
                
                if updated:
                    live.refresh()
                
                # 检查线程是否全部完成
                if all(not t.is_alive() for t in threads):
                    break
                
                time.sleep(0.1)
                
    finally:
        controller.running = False
        for t in threads:
            t.join()
            
    return results

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
