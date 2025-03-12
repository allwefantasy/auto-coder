import sys
import os
import locale
import subprocess
import platform
import tempfile
import uuid
import re
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.live import Live
import getpass
from rich.markup import escape
import threading
import queue

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

def is_running_in_powershell() -> bool:
    """
    检查当前 Python 进程是否在 PowerShell 环境中运行
    Returns:
        bool: True 表示在 PowerShell 环境中，False 表示不在
    """
    try:
        # 方法1: 检查特定的 PowerShell 环境变量
        if any(key for key in os.environ if 'POWERSHELL' in key.upper()):
            return True

        # 方法2: 尝试执行 PowerShell 特定命令
        try:
            result = subprocess.run(
                ['powershell', '-NoProfile', '-Command', '$PSVersionTable'],
                capture_output=True,
                timeout=1
            )
            if result.returncode == 0:
                return True
        except Exception:
            pass

        # 方法3: 检查父进程
        try:
            import psutil
            current_process = psutil.Process()
            parent = current_process.parent()
            if parent:
                parent_name = parent.name().lower()
                if 'powershell' in parent_name or 'pwsh' in parent_name:
                    return True
                
                # 递归检查父进程链
                while parent and parent.pid != 1:  # 1 是系统初始进程
                    if 'powershell' in parent.name().lower() or 'pwsh' in parent.name().lower():
                        return True
                    parent = parent.parent()
        except Exception:
            pass

        # 方法4: 检查命令行参数
        try:
            import sys
            if any('powershell' in arg.lower() for arg in sys.argv):
                return True
        except Exception:
            pass

        return False
    except Exception:
        return False

def is_running_in_cmd() -> bool:
    """
    检查当前 Python 进程是否在 CMD 环境中运行
    Returns:
        bool: True 表示在 CMD 环境中，False 表示不在
    """
    # 如果在 PowerShell 中，直接返回 False
    if is_running_in_powershell():
        return False
        
    try:
        # 方法1: 检查特定的 CMD 环境变量
        env = os.environ
        # CMD 特有的环境变量
        if 'PROMPT' in env and not any(key for key in env if 'POWERSHELL' in key.upper()):
            return True
        
        # 方法2: 检查 ComSpec 环境变量
        comspec = env.get('ComSpec', '').lower()
        if 'cmd.exe' in comspec:
            return True

        # 方法3: 检查父进程
        try:
            import psutil
            current_process = psutil.Process()
            parent = current_process.parent()
            if parent:
                parent_name = parent.name().lower()
                if 'cmd.exe' in parent_name:
                    return True
                
                # 递归检查父进程链
                while parent and parent.pid != 1:  # 1 是系统初始进程
                    if 'cmd.exe' in parent.name().lower():
                        return True
                    parent = parent.parent()
        except Exception:
            pass

        return False
    except Exception:
        return False

def _get_windows_terminal_name() -> str:
    """Windows 系统终端检测"""
    # 检查环境变量
    env = os.environ

    # 首先使用新方法检查是否在 PowerShell 环境中
    if is_running_in_powershell():
        # 进一步区分是否在 VSCode 的 PowerShell 终端
        if 'VSCODE_GIT_IPC_HANDLE' in env:
            return 'vscode-powershell'
        return 'powershell'
    
    # 检查是否在 CMD 环境中
    if is_running_in_cmd():
        # 区分是否在 VSCode 的 CMD 终端
        if 'VSCODE_GIT_IPC_HANDLE' in env:
            return 'vscode-cmd'
        return 'cmd'
    
    # 检查是否在 Git Bash
    if ('MINGW' in platform.system() or 
        'MSYSTEM' in env or 
        any('bash.exe' in path.lower() for path in env.get('PATH', '').split(os.pathsep))):
        # 区分是否在 VSCode 的 Git Bash 终端
        if 'VSCODE_GIT_IPC_HANDLE' in env:
            return 'vscode-git-bash'
        return 'git-bash'
    
    # 检查是否在 VSCode 的集成终端
    if 'VSCODE_GIT_IPC_HANDLE' in env:
        if 'WT_SESSION' in env:  # Windows Terminal
            return 'vscode-windows-terminal'
        return 'vscode-terminal'
    
    # 检查是否在 Windows Terminal
    if 'WT_SESSION' in env:
        return 'windows-terminal'
    
    # 检查是否在 Cygwin
    if 'CYGWIN' in platform.system():
        return 'cygwin'
    
    # 检查 TERM 环境变量
    term = env.get('TERM', '').lower()
    if term:
        if 'xterm' in term:
            return 'xterm'
        elif 'cygwin' in term:
            return 'cygwin'
    
    # 检查进程名
    try:
        import psutil
        parent = psutil.Process().parent()
        if parent:
            parent_name = parent.name().lower()
            if 'powershell' in parent_name:
                return 'powershell'
            elif 'windowsterminal' in parent_name:
                return 'windows-terminal'
            elif 'cmd.exe' in parent_name:
                return 'cmd'
    except (ImportError, Exception):
        pass
    
    # 默认返回 cmd.exe
    return 'cmd'

def get_os_distribution() -> str:
    """
    获取操作系统发行版名称
    
    Returns:
        str: 操作系统发行版名称，如 'Ubuntu 22.04', 'CentOS 7', 'Windows 10' 等
    """
    system = platform.system()
    
    if system == 'Windows':
        # Windows 系统版本
        version = sys.getwindowsversion()
        if version.major == 10 and version.build >= 22000:
            return 'Windows 11'
        elif version.major == 10:
            return 'Windows 10'
        elif version.major == 6:
            if version.minor == 3:
                return 'Windows 8.1'
            elif version.minor == 2:
                return 'Windows 8'
            elif version.minor == 1:
                return 'Windows 7'
            elif version.minor == 0:
                return 'Windows Vista'
        elif version.major == 5:
            if version.minor == 2:
                return 'Windows Server 2003'
            elif version.minor == 1:
                return 'Windows XP'
        return f'Windows {version.major}.{version.minor}'
    
    elif system == 'Linux':
        # Linux 发行版检测
        try:
            # 尝试读取 /etc/os-release
            with open('/etc/os-release', 'r') as f:
                os_release = f.read()
            
            # 解析 NAME 和 VERSION_ID
            name = re.search(r'NAME="([^"]+)"', os_release)
            version = re.search(r'VERSION_ID="([^"]+)"', os_release)
            
            if name and version:
                return f"{name.group(1)} {version.group(1)}"
            
            # 如果无法解析，尝试 lsb_release
            try:
                output = subprocess.check_output(['lsb_release', '-d'], stderr=subprocess.STDOUT)
                return output.decode('utf-8').split(':')[1].strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
            
            # 最后尝试 uname
            return platform.platform()
        except Exception:
            return platform.platform()
    
    elif system == 'Darwin':
        # macOS 版本
        version = platform.mac_ver()[0]
        return f'macOS {version}'
    
    return platform.platform()

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
    # 添加发行版信息到环境变量
    # os.environ['OS_DISTRIBUTION'] = get_os_distribution()
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
    Execute a shell command with cross-platform encoding support and streaming output.
    
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

        # Windows系统特殊处理
        if sys.platform == 'win32':
            # 设置控制台代码页为 UTF-8
            os.system('chcp 65001 > nul')
            # 强制使用 UTF-8 编码
            encoding = 'utf-8'
            # 设置环境变量
            os.environ['PYTHONIOENCODING'] = 'utf-8'

        # Create temp script file
        if sys.platform == 'win32':
            if is_running_in_powershell():
                # Create temp PowerShell script with UTF-8 BOM
                temp_file = tempfile.NamedTemporaryFile(
                    mode='wb',
                    suffix='.ps1',
                    delete=False
                )
                # 添加 UTF-8 BOM
                temp_file.write(b'\xef\xbb\xbf')
                # 设置输出编码
                ps_command = f'$OutputEncoding = [Console]::OutputEncoding = [Text.Encoding]::UTF8\n{command}'
                temp_file.write(ps_command.encode('utf-8'))
                temp_file.close()
                # Execute the temp script with PowerShell
                command = f'powershell.exe -NoProfile -NonInteractive -ExecutionPolicy Bypass -File "{temp_file.name}"'
            elif is_running_in_cmd():
                # Create temp batch script with UTF-8
                temp_file = tempfile.NamedTemporaryFile(
                    mode='wb',
                    suffix='.cmd',
                    delete=False
                )
                # 添加 UTF-8 BOM
                temp_file.write(b'\xef\xbb\xbf')
                # 写入命令内容，确保UTF-8输出
                content = f"""@echo off
chcp 65001 > nul
set PYTHONIOENCODING=utf-8
{command}
"""
                temp_file.write(content.encode('utf-8'))
                temp_file.close()
                # Execute the temp batch script
                command = f'cmd.exe /c "{temp_file.name}"'
        else:
            # Create temp shell script for Unix-like systems
            temp_file = tempfile.NamedTemporaryFile(
                mode='w',
                suffix='.sh',
                encoding='utf-8',
                delete=False
            )
            temp_file.write('#!/bin/bash\n' + command)
            temp_file.close()
            # Make the script executable
            os.chmod(temp_file.name, 0o755)
            command = temp_file.name

        # Start subprocess with UTF-8 encoding
        startupinfo = None
        if sys.platform == 'win32':
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
        # 创建子进程时设置环境变量
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            encoding='utf-8',  # 直接指定 UTF-8 编码
            errors='replace',  # 处理无法解码的字符
            env=env,          # 传递修改后的环境变量
            startupinfo=startupinfo,
            bufsize=1,        # Line buffering for immediate flushing
            universal_newlines=True  # Use text mode to handle platform line endings
        )

        # Safe decoding helper (for binary output)
        def safe_decode(text, encoding):
            if isinstance(text, str):
                return text.strip()
            try:
                # Try UTF-8 first
                return text.decode('utf-8').strip()
            except UnicodeDecodeError:
                try:
                    # If that fails, try GBK
                    return text.decode('gbk').strip()
                except UnicodeDecodeError:
                    # Finally use replacement mode
                    return text.decode(encoding, errors='replace').strip()

        output = []
        # Use direct printing for streaming output, not a Live object
        console.print(f"[bold blue]Running command:[/bold blue] {command}")
        console.print("[bold blue]Output streaming:[/bold blue]")                
                
        output_queue = queue.Queue()
        
        def read_stream(stream, stream_name):
            """Read data from stream and put in queue"""
            for line in stream:
                line = line.rstrip() if isinstance(line, str) else safe_decode(line, encoding)
                prefix = "[ERROR] " if stream_name == "stderr" else ""
                output_queue.put((stream_name, f"{prefix}{line}"))
            output_queue.put((stream_name, None))  # Mark stream end
            
        # Create threads to read stdout and stderr
        stdout_thread = threading.Thread(target=read_stream, args=(process.stdout, "stdout"))
        stderr_thread = threading.Thread(target=read_stream, args=(process.stderr, "stderr"))
        stdout_thread.daemon = True
        stderr_thread.daemon = True
        stdout_thread.start()
        stderr_thread.start()
        
        # Track number of active streams
        active_streams = 2
        
        # Process output from queue
        while active_streams > 0:
            try:
                stream_name, line = output_queue.get(timeout=0.1)
                if line is None:
                    active_streams -= 1
                    continue
                    
                output.append(line)
                # Print each line directly for true streaming output
                if stream_name == "stderr":
                    console.print(f"[red]{line}[/red]")
                else:
                    console.print(line)
                    
            except queue.Empty:
                # Check if process is still running
                if process.poll() is not None and active_streams == 2:
                    # If process ended but threads are still running, may have no output
                    break
                continue
                
        # Wait for threads to finish
        stdout_thread.join()
        stderr_thread.join()
        
        # Wait for process to end and get return code
        return_code = process.wait()
        
        # Compile results
        result_content = "\n".join(output)
        result_manager.add_result(content=result_content, meta={
            "action": "execute_shell_command",
            "input": {
                "command": command
            },
            "return_code": return_code
        })
        
        # Show command completion info
        completion_message = f"Command completed with return code: {return_code}"
        style = "green" if return_code == 0 else "red"
        console.print(f"[bold {style}]{escape(completion_message)}[/bold {style}]")

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

def get_current_username():
    """
    Get the current username across different operating systems.
    
    Returns:
        str: The current username.
    """
    try:
        # getpass.getuser() works on Windows, macOS, and Linux
        username = getpass.getuser()
        return username
    except Exception:
        # Fallback methods if getpass.getuser() fails
        try:
            if platform.system() == 'Windows':
                return os.environ.get('USERNAME', '')
            else:  # macOS/Linux
                return os.environ.get('USER', '')
        except Exception:
            return ''