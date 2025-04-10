import os
import platform
import subprocess
import sys
from io import BytesIO

import pexpect
import psutil


def run_cmd(command, verbose=False, error_print=None, cwd=None):
    """
    执行一条命令，根据不同系统和环境选择最合适的执行方式（交互式或非交互式）。

    适用场景：
    - 需要跨平台运行命令，自动判断是否使用pexpect（支持交互式）还是subprocess。
    - 希望获得命令的执行状态及输出内容。
    - 在CLI工具、自动化脚本、REPL中执行shell命令。

    参数：
    - command (str): 需要执行的命令字符串。
    - verbose (bool): 是否打印详细调试信息，默认为False。
    - error_print (callable|None): 自定义错误打印函数，默认为None，使用print。
    - cwd (str|None): 指定命令的工作目录，默认为None。

    返回：
    - tuple: (exit_code, output)，其中exit_code为整型退出码，output为命令输出内容。

    异常：
    - 捕获OSError异常，返回错误信息。
    """
    try:
        if sys.stdin.isatty() and hasattr(pexpect, "spawn") and platform.system() != "Windows":
            return run_cmd_pexpect(command, verbose, cwd)

        return run_cmd_subprocess(command, verbose, cwd)
    except OSError as e:
        error_message = f"Error occurred while running command '{command}': {str(e)}"
        if error_print is None:
            print(error_message)
        else:
            error_print(error_message)
        return 1, error_message


def get_windows_parent_process_name():
    """
    获取当前进程的父进程名（仅在Windows系统下有意义）。

    适用场景：
    - 判断命令是否由PowerShell或cmd.exe启动，以便调整命令格式。
    - 在Windows平台上进行父进程分析。

    参数：
    - 无

    返回：
    - str|None: 父进程名（小写字符串，如"powershell.exe"或"cmd.exe"），如果无法获取则为None。

    异常：
    - 捕获所有异常，返回None。
    """
    try:
        current_process = psutil.Process()
        while True:
            parent = current_process.parent()
            if parent is None:
                break
            parent_name = parent.name().lower()
            if parent_name in ["powershell.exe", "cmd.exe"]:
                return parent_name
            current_process = parent
        return None
    except Exception:
        return None


def run_cmd_subprocess(command, verbose=False, cwd=None, encoding=sys.stdout.encoding):
    if verbose:
        print("Using run_cmd_subprocess:", command)

    try:
        shell = os.environ.get("SHELL", "/bin/sh")
        parent_process = None

        # Determine the appropriate shell
        if platform.system() == "Windows":
            parent_process = get_windows_parent_process_name()
            if parent_process == "powershell.exe":
                command = f"powershell -Command {command}"

        if verbose:
            print("Running command:", command)
            print("SHELL:", shell)
            if platform.system() == "Windows":
                print("Parent process:", parent_process)

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            encoding=encoding,
            errors="replace",
            bufsize=0,  # Set bufsize to 0 for unbuffered output
            universal_newlines=True,
            cwd=cwd,
        )

        output = []
        while True:
            chunk = process.stdout.read(1)
            if not chunk:
                break
            print(chunk, end="", flush=True)  # Print the chunk in real-time
            output.append(chunk)  # Store the chunk for later use

        process.wait()
        return process.returncode, "".join(output)
    except Exception as e:
        return 1, str(e)

def run_cmd_subprocess_generator(command, verbose=False, cwd=None, encoding=sys.stdout.encoding):
    """
    使用subprocess运行命令，将命令输出逐步以生成器方式yield出来。

    适用场景：
    - 运行无需交互的命令。
    - 希望实时逐步处理命令输出（如日志打印、进度监控）。
    - 在Linux、macOS、Windows等多平台环境下安全运行命令。

    参数：
    - command (str): 需要执行的命令字符串。
    - verbose (bool): 是否打印详细调试信息，默认为False。
    - cwd (str|None): 指定命令的工作目录，默认为None。
    - encoding (str): 输出解码使用的字符编码，默认为当前stdout编码。

    返回：
    - 生成器: 逐块yield命令的输出字符串。

    异常：
    - 捕获所有异常，yield错误信息字符串。
    """
    if verbose:
        print("Using run_cmd_subprocess:", command)

    try:
        shell = os.environ.get("SHELL", "/bin/sh")
        parent_process = None

        # Windows下调整命令
        if platform.system() == "Windows":
            parent_process = get_windows_parent_process_name()
            if parent_process == "powershell.exe":
                command = f"powershell -Command {command}"

        if verbose:
            print("Running command:", command)
            print("SHELL:", shell)
            if platform.system() == "Windows":
                print("Parent process:", parent_process)

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=True,
            encoding=encoding,
            errors="replace",
            bufsize=0,
            universal_newlines=True,
            cwd=cwd,
        )

        while True:
            chunk = process.stdout.read(1)
            if not chunk:
                break            
            # 确保始终yield字符串，避免因字节或其他类型导致异常
            if not isinstance(chunk, str):
                chunk = str(chunk)
            yield chunk

        process.wait()
    except Exception as e:
        # 出错时yield异常信息，也可以raise
        yield f"[run_cmd_subprocess error]: {str(e)}"


def run_cmd_pexpect(command, verbose=False, cwd=None):
    """
    使用pexpect以交互方式运行命令，捕获完整输出。

    适用场景：
    - 执行需要用户交互的命令（如登录、密码输入等）。
    - 在Linux、macOS等Unix系统下模拟终端操作。
    - 希望完整捕获交互式命令的输出。

    参数：
    - command (str): 需要执行的命令字符串。
    - verbose (bool): 是否打印详细调试信息，默认为False。
    - cwd (str|None): 指定命令的工作目录，默认为None。

    返回：
    - tuple: (exit_code, output)，exit_code为退出状态码，output为命令完整输出内容。

    异常：
    - 捕获pexpect相关异常，返回错误信息。
    """
    if verbose:
        print("Using run_cmd_pexpect:", command)

    output = BytesIO()

    def output_callback(b):
        output.write(b)
        return b

    try:
        # Use the SHELL environment variable, falling back to /bin/sh if not set
        shell = os.environ.get("SHELL", "/bin/sh")
        if verbose:
            print("With shell:", shell)

        if os.path.exists(shell):
            # Use the shell from SHELL environment variable
            if verbose:
                print("Running pexpect.spawn with shell:", shell)
            child = pexpect.spawn(shell, args=["-i", "-c", command], encoding="utf-8", cwd=cwd)
        else:
            # Fall back to spawning the command directly
            if verbose:
                print("Running pexpect.spawn without shell.")
            child = pexpect.spawn(command, encoding="utf-8", cwd=cwd)

        # Transfer control to the user, capturing output
        child.interact(output_filter=output_callback)

        # Wait for the command to finish and get the exit status
        child.close()
        return child.exitstatus, output.getvalue().decode("utf-8", errors="replace")

    except (pexpect.ExceptionPexpect, TypeError, ValueError) as e:
        error_msg = f"Error running command {command}: {e}"
        return 1, error_msg
