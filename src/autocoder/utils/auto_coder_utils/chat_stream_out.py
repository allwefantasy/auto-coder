from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.markdown import Markdown
from typing import Generator, List, Dict, Any, Optional, Tuple
from autocoder.utils.request_queue import RequestValue, RequestOption, StreamValue
from autocoder.utils.request_queue import request_queue

MAX_HISTORY_LINES = 40  # 最大保留历史行数

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
                assistant_response += content
                
                # 处理所有行
                parts = (current_line + content).split("\n")
                
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
