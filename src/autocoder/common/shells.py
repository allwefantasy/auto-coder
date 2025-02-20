import sys
import os
import locale
import subprocess
import platform
import tempfile
import uuid
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live

from autocoder.common.result_manager import ResultManager

def get_terminal_name() -> str:
    """
    获取当前终端名称(自动适配 Windows/Linux/Mac)
    返回终端名称如: cmd.exe, bash, zsh 等
    """
    if sys.platform == 'win32':
        return _get_windows_terminal_name()
    else:
        return _get_unix_terminal_name()

def _get_windows_terminal_name() -> str:
    """Windows 系统终端检测"""
    # 检查是否在 PowerShell
    if 'POWERSHELL_DISTRIBUTION_CHANNEL' in os.environ:
        return 'powershell'
    
    # 检查是否在 Git Bash
    if 'MINGW' in platform.system():
        return 'git-bash'
    
    # 默认返回 cmd.exe
    return 'cmd.exe'

def _get_unix_terminal_name() -> str:
    """Linux/Mac 系统终端检测"""
    # 从环境变量获取终端名称
    term = os.environ.get('TERM')
    shell = os.environ.get('SHELL', '')
    
    # 检查是否在 VS Code 终端
    if 'VSCODE_GIT_IPC_HANDLE' in os.environ:
        return 'vscode-terminal'
    
    # 如果是 Mac 的 Terminal.app
    if sys.platform == 'darwin' and 'Apple_Terminal' in os.environ.get('TERM_PROGRAM', ''):
        return 'terminal.app'
    
    # 从 shell 路径获取终端名称
    if shell:
        shell_name = os.path.basename(shell)
        if shell_name in ['bash', 'zsh', 'fish']:
            return shell_name
    
    # 从 TERM 环境变量判断
    if term:
        if 'xterm' in term:
            return 'xterm'
        elif 'rxvt' in term:
            return 'rxvt'
        elif 'screen' in term:
            return 'screen'
        elif 'tmux' in term:
            return 'tmux'
    
    return 'unknown'

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
    """
    console = Console()
    result_manager = ResultManager()
    temp_file = None
    try:
        # Get terminal encoding and name
        encoding = get_terminal_encoding()
        terminal_name = get_terminal_name()

        # Create temp script file
        if sys.platform == 'win32':
            if terminal_name == 'powershell':
                # Create temp PowerShell script
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.ps1',
                    encoding=encoding,
                    delete=False
                )
                temp_file.write(command)
                temp_file.close()
                # Execute the temp script with PowerShell
                command = f'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{temp_file.name}"'
            elif terminal_name == 'cmd.exe':
                # Create temp batch script
                temp_file = tempfile.NamedTemporaryFile(
                    mode='w',
                    suffix='.cmd',
                    encoding=encoding,
                    delete=False
                )
                temp_file.write(f"@echo off\n{command}")
                temp_file.close()
                # Execute the temp batch script
                command = f'cmd.exe /c "{temp_file.name}"'
        else:
            # Create temp shell script for Unix-like systems
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.sh',
                encoding=encoding,
                delete=False
            )
            temp_file.write('#!/bin/bash\n' + command)
            temp_file.close()
            # Make the script executable
            os.chmod(temp_file.name, 0o755)
            command = temp_file.name

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
        
        result_manager.add_result(content="\n".join(output),meta={
            "action": "execute_shell_command",
            "input": {
                "command": command
            }
        })
        # Show final output
        console.print(
            Panel(
                Text("\n".join(output)),
                title="Final Output",
                border_style="blue",
                subtitle=f"Encoding: {encoding} | OS: {sys.platform}"
            )
        )

    except FileNotFoundError:
        result_manager.add_result(content=f"[bold red]Command not found:[/bold red] [yellow]{command}[/yellow]",meta={
            "action": "execute_shell_command",
            "input": {
                "command": command
            }
        })
        console.print(
            f"[bold red]Command not found:[/bold red] [yellow]{command}[/yellow]"
        )
    except Exception as e:
        result_manager.add_result(content=f"[bold red]Unexpected error:[/bold red] [yellow]{str(e)}[/yellow]",meta={
            "action": "execute_shell_command",
            "input": {
                "command": command
            }
        })
        console.print(
            f"[bold red]Unexpected error:[/bold red] [yellow]{str(e)}[/yellow]"
        )
    finally:
        # Clean up temp file
        if temp_file and os.path.exists(temp_file.name):
            try:
                os.unlink(temp_file.name)
            except Exception:
                pass