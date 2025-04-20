import os
import io
import fnmatch
import json
from typing import Dict, Any, List, Callable, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.markdown import Markdown
from autocoder.auto_coder_runner import get_memory, save_memory
from autocoder.common.rulefiles.autocoderrules_utils import AutocoderRulesManager
from autocoder.agent.auto_learn import AutoLearn
from autocoder.common import SourceCode, SourceCodeList
from autocoder.auto_coder_runner import get_final_config, get_single_llm
from autocoder.chat_auto_coder_lang import get_message, get_message_with_format

# Helper function to print the rules files table (internal implementation)
def _print_rules_table(rules: Dict[str, str], pattern: str = "*"):
    """Display rules files in a Rich table format."""
    console = Console(file=io.StringIO(), force_terminal=True, color_system="truecolor") # Capture output

    # Create a styled table with rounded borders
    table = Table(
        show_header=True,
        header_style="bold magenta",
        title=get_message_with_format("rules_file_list_title", pattern=pattern),
        title_style="bold blue",
        border_style="blue",
        show_lines=True
    )

    # Add columns with explicit width and alignment
    table.add_column(get_message("rules_file_path"), style="cyan", justify="left", width=80, no_wrap=False)
    table.add_column(get_message("rules_content_length"), style="green", justify="right", width=15, no_wrap=False)

    # Sort keys for consistent display
    for file_path in sorted(rules.keys()):
        if not fnmatch.fnmatch(os.path.basename(file_path), pattern):
            continue
            
        content = rules[file_path]
        content_length = len(content)
        
        # Format display values
        formatted_path = Text(file_path, style="cyan")
        formatted_length = Text(str(content_length), style="bright_cyan")

        table.add_row(formatted_path, formatted_length)

    # Add padding and print with a panel
    console.print(Panel(
        table,
        padding=(1, 2),
        subtitle=f"[italic]{get_message('rules_help_subtitle')}[/italic]",
        border_style="blue"
    ))
    return console.file.getvalue() # Return captured string

# --- Command Handlers ---

def _handle_list_rules(memory: Dict[str, Any], args: List[str]) -> str:
    """Handles listing rules files, supports wildcard filtering."""
    from autocoder.common.rulefiles.autocoderrules_utils import get_rules
    
    # 获取项目根目录（当前工作目录）
    project_root = os.getcwd()
    
    # 获取所有规则文件
    rules = get_rules(project_root)
    
    if not rules:
        return get_message("rules_no_files_found")
    
    # 如果提供了参数，使用它作为过滤模式
    pattern = args[0] if args else "*"
    
    # 使用通配符匹配规则文件
    if pattern != "*":
        filtered_rules = {k: v for k, v in rules.items() if fnmatch.fnmatch(os.path.basename(k), pattern)}
        if not filtered_rules:
            return get_message_with_format("rules_no_matching_files", pattern=pattern)
        return _print_rules_table(filtered_rules, pattern)
    else:
        return _print_rules_table(rules)

def _handle_remove_rules(memory: Dict[str, Any], args: List[str]) -> str:
    """Handles removing rules files based on glob pattern."""
    if not args:
        return get_message("rules_remove_param_required")
    
    pattern = args[0]
    
    # 获取规则管理器
    rules_manager = AutocoderRulesManager()
    rules = rules_manager.get_rules()
    
    if not rules:
        return get_message("rules_no_files_found")
    
    # 匹配要删除的文件
    files_to_remove = []
    for file_path in rules.keys():
        if fnmatch.fnmatch(os.path.basename(file_path), pattern):
            files_to_remove.append(file_path)
    
    if not files_to_remove:
        return get_message_with_format("rules_no_files_to_remove", pattern=pattern)
    
    # 删除匹配的文件
    removed_count = 0
    for file_path in files_to_remove:
        try:
            os.remove(file_path)
            removed_count += 1
        except Exception as e:
            return get_message_with_format("rules_delete_error", file_path=file_path, error=str(e))
    
    # 重新加载规则
    rules_manager._load_rules()
    
    return get_message_with_format("rules_delete_success", count=removed_count)

def _handle_analyze_rules(memory: Dict[str, Any], args: List[str], coding_func=None) -> str:
    """Handles analyzing current files with rules."""
    query = " ".join(args) if args else ""
    
    args = get_final_config()    
    llm = get_single_llm(args.model, product_mode=args.product_mode)    
    auto_learn = AutoLearn(llm=llm, args=args)
    
    files = memory.get("current_files", {}).get("files", [])
    if not files:
        return get_message("rules_no_active_files")
    
    sources = SourceCodeList([])
    for file in files:        
        try:
            with open(file, "r", encoding="utf-8") as f:
                source_code = f.read()  
                sources.sources.append(SourceCode(module_name=file, source_code=source_code))
        except Exception as e:
            return get_message_with_format("rules_file_read_error", file_path=file, error=str(e))
    
    try:
        result = auto_learn.analyze_modules.prompt(sources=sources, query=query)
        # 如果传入了 coding_func，则执行
        if coding_func is not None:
            coding_func(query=result)
        return result
    except Exception as e:
        return get_message_with_format("rules_analysis_error", error=str(e))

def _handle_get_rules(memory: Dict[str, Any], args: List[str]) -> str:
    """Handles displaying the content of rules files based on glob pattern."""
    if not args:
        return get_message("rules_get_param_required")
    
    pattern = args[0]
    
    # 获取规则管理器
    from autocoder.common.rulefiles.autocoderrules_utils import get_rules
    project_root = os.getcwd()
    rules = get_rules(project_root)
    
    if not rules:
        return get_message("rules_no_files_found")
    
    # 匹配文件
    matched_files = []
    for file_path in rules.keys():
        if fnmatch.fnmatch(os.path.basename(file_path), pattern):
            matched_files.append(file_path)
    
    if not matched_files:
        return get_message_with_format("rules_get_no_matching_files", pattern=pattern)
    
    # 创建一个真实的控制台，而不是捕获输出
    console = Console()
    
    # 打印每个匹配文件的内容
    for file_path in sorted(matched_files):
        try:
            # 获取文件内容
            content = rules[file_path]
            
            # 打印文件标题
            console.print("\n")
            console.print(Panel(
                get_message_with_format("rules_get_file_title", file_path=file_path),
                style="bold blue"
            ))
            
            # 以Markdown格式打印内容
            md = Markdown(content)
            console.print(md)
            
        except Exception as e:
            console.print(
                get_message_with_format("rules_get_read_error", file_path=file_path, error=str(e)),
                style="bold red"
            )
    
    # 由于控制台直接打印，返回空字符串
    return ""

def _handle_help(memory: Dict[str, Any], args: List[str]) -> str:
    """Provides help text for the /rules command."""
    return get_message("rules_help_text")

# Command dispatch table
COMMAND_HANDLERS: Dict[str, Callable[[Dict[str, Any], List[str]], str]] = {
    "list": _handle_list_rules,
    "remove": _handle_remove_rules,
    "get": _handle_get_rules,
    "analyze": _handle_analyze_rules,  # 默认行为
    "help": _handle_help,
}

def handle_rules_command(command_args: str, memory: Dict[str, Any], coding_func=None) -> str:
    """
    Handles the /rules command and its subcommands.

    Args:
        command_args: The arguments string following the /rules command.
                      Example: "analyze code quality", "/list", "/remove *.md"
        memory: The current session memory dictionary.

    Returns:
        A string response to be displayed to the user.
    """
    rules_str = command_args.strip()
    
    # 处理空命令
    if not rules_str:
        # 没有参数，默认执行分析操作
        return _handle_analyze_rules(memory, [], coding_func=coding_func)
    
    # 处理子命令
    if rules_str.startswith("/"):
        # 解析子命令
        parts = rules_str[1:].strip().split(maxsplit=1)
        subcommand = parts[0].lower() if parts else ""
        args = parts[1].split() if len(parts) > 1 else []
        
        handler = COMMAND_HANDLERS.get(subcommand)
        if handler:
            try:
                # 仅 analyze 需要 coding_func
                if subcommand == "analyze":
                    return handler(memory, args, coding_func=coding_func)
                else:
                    return handler(memory, args)
            except Exception as e:
                return get_message_with_format("rules_command_error", subcommand=subcommand, error=str(e))
        else:
            return get_message_with_format("rules_unknown_command", subcommand=subcommand)
    elif rules_str.lower() == "help":
        # 处理无斜杠的 help 命令
        return _handle_help(memory, [])
    else:
        # 将整个字符串作为查询参数传递给 analyze
        return _handle_analyze_rules(memory, [rules_str], coding_func=coding_func) 