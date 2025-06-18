

















"""
Auto-Coder SDK 格式化工具

提供各种输出格式化功能。
"""

import json
from typing import Any, AsyncIterator, Dict

from ..models.messages import Message
from ..models.responses import StreamEvent


def format_output(content: Any, output_format: str = "text") -> str:
    """
    格式化输出内容
    
    Args:
        content: 要格式化的内容
        output_format: 输出格式 (text, json)
        
    Returns:
        str: 格式化后的内容
    """
    if output_format == "json":
        if isinstance(content, (dict, list)):
            return json.dumps(content, ensure_ascii=False, indent=2)
        elif hasattr(content, 'to_dict'):
            return json.dumps(content.to_dict(), ensure_ascii=False, indent=2)
        else:
            return json.dumps({"content": str(content)}, ensure_ascii=False, indent=2)
    else:
        # text format
        return str(content)


async def format_stream_output(stream: AsyncIterator[Any], output_format: str = "stream-json") -> AsyncIterator[str]:
    """
    格式化流式输出
    
    Args:
        stream: 输入流
        output_format: 输出格式
        
    Yields:
        str: 格式化后的内容
    """
    if output_format == "stream-json":
        # 发送开始事件
        start_event = StreamEvent.start_event()
        yield start_event.to_json()
        
        try:
            async for item in stream:
                if isinstance(item, Message):
                    # 转换Message为StreamEvent
                    if item.is_assistant_message():
                        content_event = StreamEvent.content_event(item.content)
                        yield content_event.to_json()
                elif hasattr(item, 'to_dict'):
                    # 直接输出有to_dict方法的对象
                    yield json.dumps(item.to_dict(), ensure_ascii=False)
                else:
                    # 包装普通内容为content事件
                    content_event = StreamEvent.content_event(str(item))
                    yield content_event.to_json()
            
            # 发送结束事件
            end_event = StreamEvent.end_event()
            yield end_event.to_json()
            
        except Exception as e:
            # 发送错误事件
            error_event = StreamEvent.error_event(str(e))
            yield error_event.to_json()
    else:
        # 其他格式，直接输出
        async for item in stream:
            yield format_output(item, "text")


def format_table_output(data: list, headers: list = None) -> str:
    """
    格式化表格输出
    
    Args:
        data: 表格数据
        headers: 表头
        
    Returns:
        str: 格式化的表格
    """
    if not data:
        return "No data to display"
    
    if headers is None:
        if isinstance(data[0], dict):
            headers = list(data[0].keys())
        else:
            headers = [f"Column {i+1}" for i in range(len(data[0]) if data[0] else 0)]
    
    # 计算列宽
    col_widths = []
    for i, header in enumerate(headers):
        max_width = len(header)
        for row in data:
            if isinstance(row, dict):
                cell_value = str(row.get(header, ""))
            elif isinstance(row, (list, tuple)) and i < len(row):
                cell_value = str(row[i])
            else:
                cell_value = ""
            max_width = max(max_width, len(cell_value))
        col_widths.append(max_width + 2)  # 添加padding
    
    # 构建表格
    lines = []
    
    # 表头
    header_line = "|".join(header.center(col_widths[i]) for i, header in enumerate(headers))
    lines.append(header_line)
    
    # 分隔线
    separator = "|".join("-" * width for width in col_widths)
    lines.append(separator)
    
    # 数据行
    for row in data:
        if isinstance(row, dict):
            row_values = [str(row.get(header, "")) for header in headers]
        elif isinstance(row, (list, tuple)):
            row_values = [str(row[i]) if i < len(row) else "" for i in range(len(headers))]
        else:
            row_values = [str(row)]
        
        row_line = "|".join(value.ljust(col_widths[i]) for i, value in enumerate(row_values))
        lines.append(row_line)
    
    return "\n".join(lines)


def format_error_output(error: Exception, verbose: bool = False) -> str:
    """
    格式化错误输出
    
    Args:
        error: 异常对象
        verbose: 是否显示详细信息
        
    Returns:
        str: 格式化的错误信息
    """
    if verbose:
        import traceback
        return f"Error: {str(error)}\n\nTraceback:\n{traceback.format_exc()}"
    else:
        return f"Error: {str(error)}"


def format_progress_output(current: int, total: int, description: str = "") -> str:
    """
    格式化进度输出
    
    Args:
        current: 当前进度
        total: 总数
        description: 描述
        
    Returns:
        str: 格式化的进度信息
    """
    if total == 0:
        percentage = 100
    else:
        percentage = min(100, int((current / total) * 100))
    
    bar_length = 30
    filled_length = int(bar_length * percentage // 100)
    bar = "█" * filled_length + "-" * (bar_length - filled_length)
    
    return f"{description} [{bar}] {percentage}% ({current}/{total})"

















