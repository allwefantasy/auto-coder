
import sys
import os
import locale
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

def get_terminal_encoding() -> str:
    """
    获取当前终端编码(自动适配 Windows/Linux/Mac)
    返回标准编码名称如: utf-8, gbk, cp936 等
    """
    # 第一优先级:尝试标准库locale检测
    try:
        return locale.getencoding()  # Python 3.10+ 新增方法
    except AttributeError:
        pass
    
    # 第二优先级:各平台专用检测逻辑
    if sys.platform == 'win32':
        return _get_windows_terminal_encoding()
    else:
        return _get_unix_terminal_encoding()

def _get_windows_terminal_encoding() -> str:
    """Windows 系统编码检测"""
    try:
        # 通过 chcp 命令获取代码页
        result = subprocess.run(
            ['chcp'], 
            capture_output=True, 
            text=True,
            shell=True,
            timeout=1
        )
        code_page = result.stdout.split(':')[-1].strip()
        return _win_code_page_to_encoding(code_page)
    except Exception:
        return locale.getpreferredencoding(do_setlocale=False) or 'gbk'

def _get_unix_terminal_encoding() -> str:
    """Linux/Mac 系统编码检测"""
    # 尝试读取环境变量
    for var in ['LC_ALL', 'LC_CTYPE', 'LANG']:
        lang = os.environ.get(var)
        if lang and '.' in lang:
            return lang.split('.')[-1]
    
    # 通过 locale 命令检测
    try:
        result = subprocess.run(
            ['locale', '-c', 'LC_CTYPE'],
            capture_output=True,
            text=True,
            timeout=1
        )
        return result.stdout.strip().split('.')[-1] or 'utf-8'
    except Exception:
        return locale.getpreferredencoding(do_setlocale=False) or 'utf-8'

def _win_code_page_to_encoding(code_page: str) -> str:
    """Windows 代码页转编码名称"""
    cp_map = {
        '65001': 'utf-8',
        '936': 'gbk',
        '950': 'big5',
        '54936': 'gb18030',
        '437': 'cp437',
        '850': 'cp850'
    }
    return cp_map.get(code_page, f'cp{code_page}')

def execute_shell_command(command: str):
    """
    Execute a shell command with cross-platform encoding support.
    
    Args:
        command (str): The shell command to execute
        encoding (str, optional): Override default encoding. Defaults to None.
    """
    console = Console()
    try:
        # Get terminal encoding
        encoding = get_terminal_encoding()

        # Start subprocess
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True
        )

        # Safe decoding helper
        def safe_decode(byte_stream, encoding):
            try:
                return byte_stream.decode(encoding).strip()
            except UnicodeDecodeError:
                return byte_stream.decode(encoding, errors='replace').strip()

        output = []
        with Live(console=console, refresh_per_second=4) as live:
            while True:
                # Read output streams
                output_bytes = process.stdout.readline()
                error_bytes = process.stderr.readline()

                # Handle standard output
                if output_bytes:
                    output_line = safe_decode(output_bytes, encoding)
                    output.append(output_line)
                    live.update(
                        Panel(
                            Text("\n".join(output[-20:])),
                            title="Shell Output",
                            border_style="green",
                        )
                    )

                # Handle error output
                if error_bytes:
                    error_line = safe_decode(error_bytes, encoding)
                    output.append(f"ERROR: {error_line}")
                    live.update(
                        Panel(
                            Text("\n".join(output[-20:])),
                            title="Shell Output",
                            border_style="red",
                        )
                    )

                # Check if process has ended
                if process.poll() is not None:
                    break

        # Get remaining output
        remaining_out, remaining_err = process.communicate()
        if remaining_out:
            output.append(safe_decode(remaining_out, encoding))
        if remaining_err:
            output.append(f"ERROR: {safe_decode(remaining_err, encoding)}")

        # Show final output
        console.print(
            Panel(
                Text("\n".join(output)),
                title="Final Output",
                border_style="blue",
                subtitle=f"Encoding: {encoding} | OS: {sys.platform}"
            )
        )

        if process.returncode != 0:
            console.print(
                f"[bold red]Command failed with code {process.returncode}[/bold red]"
            )

    except FileNotFoundError:
        console.print(
            f"[bold red]Command not found:[/bold red] [yellow]{command}[/yellow]"
        )
    except Exception as e:
        console.print(
            f"[bold red]Unexpected error:[/bold red] [yellow]{str(e)}[/yellow]"
        )