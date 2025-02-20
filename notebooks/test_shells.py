import sys
import os
from rich.console import Console
from rich.table import Table
from autocoder.common.shells import (
    get_terminal_name,
    get_terminal_encoding,
    is_running_in_powershell,
    is_running_in_cmd,
    execute_shell_command
)

def print_terminal_info():
    """打印终端基本信息"""
    console = Console()
    
    # 创建表格
    table = Table(title="终端环境信息")
    table.add_column("检测项", style="cyan")
    table.add_column("结果", style="green")
    
    # 添加基本信息
    table.add_row("操作系统", sys.platform)
    table.add_row("终端名称", get_terminal_name())
    table.add_row("终端编码", get_terminal_encoding())
    table.add_row("是否 PowerShell", str(is_running_in_powershell()))
    table.add_row("是否 CMD", str(is_running_in_cmd()))
    
    # 打印环境变量
    env_vars = [
        "SHELL",
        "TERM",
        "PROMPT",
        "PSModulePath",
        "POWERSHELL_DISTRIBUTION_CHANNEL",
        "VSCODE_GIT_IPC_HANDLE",
        "WT_SESSION",
        "ComSpec"
    ]
    
    table.add_section()
    for var in env_vars:
        if var in os.environ:
            table.add_row(f"环境变量: {var}", os.environ[var])
    
    console.print(table)

def test_shell_commands():
    """测试不同类型的shell命令"""
    console = Console()
    console.print("\n[yellow]测试shell命令执行:[/yellow]")
    
    # 测试系统信息命令
    if sys.platform == 'win32':
        console.print("\n[cyan]1. 执行系统信息命令[/cyan]")
        # 使用 wmic 命令替代 systeminfo，输出更稳定
        execute_shell_command("wmic os get Caption,Version,OSArchitecture /format:list")
        
        console.print("\n[cyan]2. 执行目录列表命令[/cyan]")
        execute_shell_command("dir")
        
        console.print("\n[cyan]3. 执行PowerShell特定命令[/cyan]")
        execute_shell_command("Get-Host | Select-Object Version")
    else:
        console.print("\n[cyan]1. 执行系统信息命令[/cyan]")
        execute_shell_command("uname -a")
        
        console.print("\n[cyan]2. 执行目录列表命令[/cyan]")
        execute_shell_command("ls -la")
        
        console.print("\n[cyan]3. 执行环境变量查看命令[/cyan]")
        execute_shell_command("env")

if __name__ == "__main__":
    # 打印分隔线
    print("=" * 80)
    print("Shell环境测试脚本")
    print("=" * 80)
    
    # 打印终端信息
    print_terminal_info()
    
    # 测试shell命令
    test_shell_commands() 