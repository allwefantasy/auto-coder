from itertools import product
from rich.console import Console
from rich.panel import Panel
from prompt_toolkit.formatted_text import HTML
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit import prompt
import os
import yaml
import json
import sys
import io
import uuid
import glob
import time
import hashlib
from contextlib import contextmanager
from typing import List, Dict, Any, Optional
from autocoder.common import AutoCoderArgs
from pydantic import BaseModel
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
from autocoder.common.result_manager import ResultManager
from autocoder.version import __version__
from autocoder.auto_coder import main as auto_coder_main
from autocoder.utils import get_last_yaml_file
from autocoder.commands.auto_command import CommandAutoTuner, AutoCommandRequest, CommandConfig, MemoryConfig
from autocoder.common.v2.agent.agentic_edit import AgenticEdit,AgenticEditRequest
from autocoder.index.symbols_utils import (
    extract_symbols,
    SymbolType,
)
import platform
import subprocess
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.live import Live
# Removed Text import as it's only used in the deleted print_conf
from rich.live import Live
from rich.markdown import Markdown
from byzerllm.utils.nontext import Image
import git
from autocoder.common import git_utils
from autocoder.chat_auto_coder_lang import get_message,get_message_with_format
from autocoder.agent.auto_guess_query import AutoGuessQuery
from autocoder.common.mcp_server import get_mcp_server
from autocoder.common.mcp_server_types import (
    McpRequest, McpInstallRequest, McpRemoveRequest, McpListRequest, 
    McpListRunningRequest, McpRefreshRequest, McpServerInfoRequest
)
import byzerllm
from byzerllm.utils import format_str_jinja2
from autocoder.common.memory_manager import get_global_memory_file_paths 
from autocoder import models as models_module
import shlex
from autocoder.utils.llms import get_single_llm
import fnmatch
import pkg_resources
from autocoder.common.printer import Printer
from autocoder.utils.thread_utils import run_in_raw_thread
from autocoder.memory.active_context_manager import ActiveContextManager
from autocoder.common.command_completer import CommandCompleter,FileSystemModel as CCFileSystemModel,MemoryConfig as CCMemoryModel
from autocoder.common.conf_validator import ConfigValidator
from autocoder import command_parser as CommandParser
from loguru import logger as global_logger
from autocoder.utils.project_structure import EnhancedFileAnalyzer
from autocoder.common import SourceCodeList,SourceCode
from autocoder.common.file_monitor import FileMonitor
from filelock import FileLock


## 对外API，用于第三方集成 auto-coder 使用。
class SymbolItem(BaseModel):
    symbol_name: str
    symbol_type: SymbolType
    file_name: str

class InitializeSystemRequest(BaseModel):
    product_mode: str
    skip_provider_selection: bool
    debug: bool
    quick: bool
    lite: bool
    pro: bool


if platform.system() == "Windows":
    from colorama import init

    init()


memory = {
    "conversation": [],
    "current_files": {"files": [], "groups": {}},
    "conf": {},
    "exclude_dirs": [],
    "mode": "auto_detect",  # 新增mode字段,默认为 auto_detect 模式
}

project_root = os.getcwd()


base_persist_dir = os.path.join(project_root,".auto-coder", "plugins", "chat-auto-coder")

defaut_exclude_dirs = [".git", "node_modules", "dist", "build", "__pycache__",".auto-coder"]

commands = [
    "/add_files",
    "/remove_files",
    "/list_files",
    "/conf",
    "/coding",
    "/chat",
    "/ask",
    "/commit",
    "/rules",
    "/revert",
    "/index/query",
    "/index/build",
    "/index/export",
    "/index/import",
    "/exclude_files",        
    "/help",
    "/shell",
    "/voice_input",
    "/exit",
    "/summon",
    "/mode",
    "/lib",
    "/design",
    "/mcp",
    "/models",
    "/auto",
    "/conf/export",
    "/conf/import",
    "/exclude_dirs",
]

def load_tokenizer():
    from autocoder.rag.variable_holder import VariableHolder
    from tokenizers import Tokenizer    
    try:
        tokenizer_path = pkg_resources.resource_filename(
            "autocoder", "data/tokenizer.json"
        )
        VariableHolder.TOKENIZER_PATH = tokenizer_path
        VariableHolder.TOKENIZER_MODEL = Tokenizer.from_file(tokenizer_path)
    except FileNotFoundError:
        tokenizer_path = None


def configure_project_type():
    from prompt_toolkit.lexers import PygmentsLexer
    from pygments.lexers.markup import MarkdownLexer
    from prompt_toolkit.formatted_text import HTML
    from prompt_toolkit.shortcuts import print_formatted_text
    from prompt_toolkit.styles import Style
    from html import escape

    style = Style.from_dict(
        {
            "info": "#ansicyan",
            "warning": "#ansiyellow",
            "input-area": "#ansigreen",
            "header": "#ansibrightyellow bold",
        }
    )

    def print_info(text):
        print_formatted_text(HTML(f"<info>{escape(text)}</info>"), style=style)

    def print_warning(text):
        print_formatted_text(
            HTML(f"<warning>{escape(text)}</warning>"), style=style)

    def print_header(text):
        print_formatted_text(
            HTML(f"<header>{escape(text)}</header>"), style=style)

    print_header(f"\n=== {get_message('project_type_config')} ===\n")
    print_info(get_message("project_type_supports"))
    print_info(get_message("language_suffixes"))
    print_info(get_message("predefined_types"))
    print_info(get_message("mixed_projects"))
    print_info(get_message("examples"))

    print_warning(f"{get_message('default_type')}\n")
    
    extensions = get_all_extensions(project_root) or "py"
    project_type = prompt(
        get_message("enter_project_type"), default=extensions, style=style
    ).strip()

    if project_type:
        configure(f"project_type:{project_type}", skip_print=True)
        configure("skip_build_index:false", skip_print=True)
        print_info(f"\n{get_message('project_type_set')} {project_type}")
    else:
        print_info(f"\n{get_message('using_default_type')}")

    print_warning(f"\n{get_message('change_setting_later')}:")
    print_warning("/conf project_type:<new_type>\n")

    return project_type


def get_all_extensions(directory: str = ".") -> str:
    """获取指定目录下所有文件的后缀名,多个按逗号分隔，并且带."""
    args = AutoCoderArgs(
        source_dir=directory,
        # 其他必要参数设置为默认值
        target_file="",
        git_url="",
        project_type="",
        conversation_prune_safe_zone_tokens=0
    )
    
    analyzer = EnhancedFileAnalyzer(
        args=args,
        llm=None,  # 如果只是获取后缀名，可以不需要LLM
        config=None  # 使用默认配置
    )
    
    # 获取分析结果
    analysis_result = analyzer.analyze_extensions()
    
    # 合并 code 和 config 的后缀名
    all_extensions = set(analysis_result["code"] + analysis_result["config"])
    
    # 转换为逗号分隔的字符串
    return ",".join(sorted(all_extensions))

def configure_logger():
    # 设置日志目录和文件    
    log_dir = os.path.join(project_root, ".auto-coder", "logs")
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, "auto-coder.log")

    # 配置全局日志
    # 默认情况下，所有日志都写入文件
    # 控制台上默认不输出任何日志，除非显式配置
    global_logger.configure(
        handlers=[
            {
                "sink": log_file,
                "level": "INFO",
                "rotation": "10 MB",
                "retention": "1 week",
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name} | {message}",
            },
            {
                "sink": sys.stdout,
                "level": "INFO",
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {name} | {message}",
                # 默认不打印任何日志到控制台
                "filter": lambda record: False
            }
        ]
    )


def init_singleton_instances():
    # 初始化文件监控系统
    try:
        FileMonitor(project_root).start()
    except Exception as e:
        global_logger.error(f"Failed to start file monitor: {e}")
        global_logger.exception(e)
    
    # 初始化规则文件管理器
    from autocoder.common.rulefiles.autocoderrules_utils import get_rules
    get_rules(project_root=project_root)

    # 初始化忽略文件管理器
    from autocoder.common.ignorefiles.ignore_file_utils import IgnoreFileManager
    _ = IgnoreFileManager(project_root=project_root)


def start():    
    if os.environ.get('autocoder_auto_init',"true") in ["true","True","True",True]:
        configure_logger()
        init_singleton_instances()

def stop():
    try:
        FileMonitor(project_root).stop()
    except Exception as e:
        global_logger.error(f"Failed to stop file monitor: {e}")
        global_logger.exception(e)

def initialize_system(args:InitializeSystemRequest):
    from autocoder.utils.model_provider_selector import ModelProviderSelector
    from autocoder import models as models_module
    print(f"\n\033[1;34m{get_message('initializing')}\033[0m")

    first_time = [False]
    configure_success = [False]

    def print_status(message, status):
        if status == "success":
            print(f"\033[32m✓ {message}\033[0m")
        elif status == "warning":
            print(f"\033[33m! {message}\033[0m")
        elif status == "error":
            print(f"\033[31m✗ {message}\033[0m")
        else:
            print(f"  {message}")

    def init_project():           
        if not os.path.exists(".auto-coder") or not os.path.exists("actions"):
            first_time[0] = True
            print_status(get_message("not_initialized"), "warning")
            init_choice = input(
                f"  {get_message('init_prompt')}").strip().lower()
            if init_choice == "y":
                try:
                    subprocess.run(
                        ["auto-coder", "init", "--source_dir", "."], check=True
                    )
                    print_status(get_message("init_success"), "success")
                except subprocess.CalledProcessError:
                    print_status(get_message("init_fail"), "error")
                    print_status(get_message("init_manual"), "warning")
                    exit(1)
            else:
                print_status(get_message("exit_no_init"), "warning")
                exit(1)

        if not os.path.exists(base_persist_dir):
            os.makedirs(base_persist_dir, exist_ok=True)
            print_status(get_message_with_format("created_dir",path=base_persist_dir), "success")

        if first_time[0]:
            configure_project_type()
            configure_success[0] = True

        print_status(get_message("init_complete"), "success")

    init_project()

    if not args.skip_provider_selection and first_time[0]:
        if args.product_mode == "lite":                    
            ## 如果已经是配置过的项目，就无需再选择
            if first_time[0]:
                if not models_module.check_model_exists("v3_chat") or not models_module.check_model_exists("r1_chat"):
                    model_provider_selector = ModelProviderSelector()
                    model_provider_info = model_provider_selector.select_provider()
                    if model_provider_info is not None:
                        models_json_list = model_provider_selector.to_models_json(model_provider_info)
                        models_module.add_and_activate_models(models_json_list)              

        if args.product_mode == "pro":
            # Check if Ray is running
            print_status(get_message("checking_ray"), "")
            ray_status = subprocess.run(
                ["ray", "status"], capture_output=True, text=True)
            if ray_status.returncode != 0:
                print_status(get_message("ray_not_running"), "warning")
                try:
                    subprocess.run(["ray", "start", "--head"], check=True)
                    print_status(get_message("ray_start_success"), "success")
                except subprocess.CalledProcessError:
                    print_status(get_message("ray_start_fail"), "error")
                    return
            else:
                print_status(get_message("ray_running"), "success")

            # Check if deepseek_chat model is available
            print_status(get_message("checking_model"), "")
            try:
                result = subprocess.run(
                    ["easy-byzerllm", "chat", "v3_chat", "你好"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if result.returncode == 0:
                    print_status(get_message("model_available"), "success")
                    init_project()
                    print_status(get_message("init_complete_final"), "success")
                    return
            except subprocess.TimeoutExpired:
                print_status(get_message("model_timeout"), "error")
            except subprocess.CalledProcessError:
                print_status(get_message("model_error"), "error")

            # If deepseek_chat is not available
            print_status(get_message("model_not_available"), "warning")
            api_key = prompt(HTML(f"<b>{get_message('enter_api_key')} </b>"))

            print_status(get_message("deploying_model").format("Deepseek官方"), "")
            deploy_cmd = [
                "byzerllm",
                "deploy",
                "--pretrained_model_type",
                "saas/openai",
                "--cpus_per_worker",
                "0.001",
                "--gpus_per_worker",
                "0",
                "--worker_concurrency",
                "1000",
                "--num_workers",
                "1",
                "--infer_params",
                f"saas.base_url=https://api.deepseek.com/v1 saas.api_key={api_key} saas.model=deepseek-chat",
                "--model",
                "v3_chat",
            ]

            try:
                subprocess.run(deploy_cmd, check=True)
                print_status(get_message("deploy_complete"), "success")
            except subprocess.CalledProcessError:
                print_status(get_message("deploy_fail"), "error")
                return


            deploy_cmd = [
                "byzerllm",
                "deploy",
                "--pretrained_model_type",
                "saas/reasoning_openai",
                "--cpus_per_worker",
                "0.001",
                "--gpus_per_worker",
                "0",
                "--worker_concurrency",
                "1000",
                "--num_workers",
                "1",
                "--infer_params",
                f"saas.base_url=https://api.deepseek.com/v1 saas.api_key={api_key} saas.model=deepseek-reasoner",
                "--model",
                "r1_chat",
            ]

            try:
                subprocess.run(deploy_cmd, check=True)
                print_status(get_message("deploy_complete"), "success")
            except subprocess.CalledProcessError:
                print_status(get_message("deploy_fail"), "error")
                return

            # Validate the deployment
            print_status(get_message("validating_deploy"), "")
            try:
                validation_result = subprocess.run(
                    ["easy-byzerllm", "chat", "v3_chat", "你好"],
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=True,
                )
                print_status(get_message("validation_success"), "success")
            except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
                print_status(get_message("validation_fail"), "error")
                print_status(get_message("manual_start"), "warning")
                print_status("easy-byzerllm chat v3_chat 你好", "")

            print_status(get_message("init_complete_final"), "success")  
            configure_success[0] = True

    if first_time[0] and args.product_mode == "pro" and configure_success[0]:
        configure(f"model:v3_chat", skip_print=True)        

    if first_time[0] and args.product_mode == "lite" and models_module.check_model_exists("v3_chat"):
        configure(f"model:v3_chat", skip_print=True)        


def convert_yaml_config_to_str(yaml_config):
    yaml_content = yaml.safe_dump(
        yaml_config,
        allow_unicode=True,
        default_flow_style=False,
        default_style=None,
    )
    return yaml_content


def get_all_file_names_in_project() -> List[str]:

    file_names = []
    final_exclude_dirs = defaut_exclude_dirs + memory.get("exclude_dirs", [])
    for root, dirs, files in os.walk(project_root, followlinks=True):
        dirs[:] = [d for d in dirs if d not in final_exclude_dirs]
        file_names.extend(files)
    return file_names


def get_all_file_in_project() -> List[str]:

    file_names = []
    final_exclude_dirs = defaut_exclude_dirs + memory.get("exclude_dirs", [])
    for root, dirs, files in os.walk(project_root, followlinks=True):
        dirs[:] = [d for d in dirs if d not in final_exclude_dirs]
        for file in files:
            file_names.append(os.path.join(root, file))
    return file_names


def get_all_file_in_project_with_dot() -> List[str]:
    file_names = []
    final_exclude_dirs = defaut_exclude_dirs + memory.get("exclude_dirs", [])
    for root, dirs, files in os.walk(project_root, followlinks=True):
        dirs[:] = [d for d in dirs if d not in final_exclude_dirs]
        for file in files:
            file_names.append(os.path.join(
                root, file).replace(project_root, "."))
    return file_names


def get_all_dir_names_in_project() -> List[str]:
    dir_names = []
    final_exclude_dirs = defaut_exclude_dirs + memory.get("exclude_dirs", [])
    for root, dirs, files in os.walk(project_root, followlinks=True):
        dirs[:] = [d for d in dirs if d not in final_exclude_dirs]
        for dir in dirs:
            dir_names.append(dir)
    return dir_names


def find_files_in_project(patterns: List[str]) -> List[str]:
    matched_files = []
    final_exclude_dirs = defaut_exclude_dirs + memory.get("exclude_dirs", [])

    for pattern in patterns:
        if "*" in pattern or "?" in pattern:
            for file_path in glob.glob(pattern, recursive=True):
                if os.path.isfile(file_path):
                    abs_path = os.path.abspath(file_path)
                    if not any(
                        exclude_dir in abs_path.split(os.sep)
                        for exclude_dir in final_exclude_dirs
                    ):
                        matched_files.append(abs_path)
        else:
            is_added = False
            # add files belongs to project
            for root, dirs, files in os.walk(project_root, followlinks=True):
                dirs[:] = [d for d in dirs if d not in final_exclude_dirs]
                if pattern in files:
                    matched_files.append(os.path.join(root, pattern))
                    is_added = True
                else:
                    for file in files:
                        _pattern = os.path.abspath(pattern)
                        if _pattern in os.path.join(root, file):
                            matched_files.append(os.path.join(root, file))
                            is_added = True
            # add files not belongs to project
            if not is_added:
                matched_files.append(pattern)

    return list(set(matched_files))


def convert_config_value(key, value):
    field_info = AutoCoderArgs.model_fields.get(key)
    if field_info:
        if isinstance(value, str) and value.lower() in ["true", "false"]:
            return value.lower() == "true"
        elif "int" in str(field_info.annotation):
            return int(value)
        elif "float" in str(field_info.annotation):
            return float(value)
        else:
            return value
    else:
        print(f"Invalid configuration key: {key}")
        return None


@contextmanager
def redirect_stdout():
    original_stdout = sys.stdout
    sys.stdout = f = io.StringIO()
    try:
        yield f
    finally:
        sys.stdout = original_stdout


def configure(conf: str, skip_print=False):
    printer = Printer()
    parts = conf.split(None, 1)
    if len(parts) == 2 and parts[0] in ["/drop", "/unset", "/remove"]:
        key = parts[1].strip()
        if key in memory["conf"]:
            del memory["conf"][key]
            save_memory()
            printer.print_in_terminal("config_delete_success", style="green", key=key)
        else:
            printer.print_in_terminal("config_not_found", style="yellow", key=key)
    else:
        parts = conf.split(":", 1)
        if len(parts) != 2:
            printer.print_in_terminal("config_invalid_format", style="red")
            return
        key, value = parts
        key = key.strip()
        value = value.strip()
        if not value:
            printer.print_in_terminal("config_value_empty", style="red")
            return
        product_mode = memory["conf"].get("product_mode",None)  
        if product_mode:
            ConfigValidator.validate(key, value, product_mode)    
        memory["conf"][key] = value
        save_memory()
        if not skip_print:
            printer.print_in_terminal("config_set_success", style="green", key=key, value=value)

# word_completer = WordCompleter(commands)


def get_symbol_list() -> List[SymbolItem]:
    list_of_symbols = []
    index_file = os.path.join(".auto-coder", "index.json")

    if os.path.exists(index_file):
        with open(index_file, "r",encoding="utf-8") as file:
            index_data = json.load(file)
    else:
        index_data = {}

    for item in index_data.values():
        symbols_str = item["symbols"]
        module_name = item["module_name"]
        info1 = extract_symbols(symbols_str)
        for name in info1.classes:
            list_of_symbols.append(
                SymbolItem(
                    symbol_name=name,
                    symbol_type=SymbolType.CLASSES,
                    file_name=module_name,
                )
            )
        for name in info1.functions:
            list_of_symbols.append(
                SymbolItem(
                    symbol_name=name,
                    symbol_type=SymbolType.FUNCTIONS,
                    file_name=module_name,
                )
            )
        for name in info1.variables:
            list_of_symbols.append(
                SymbolItem(
                    symbol_name=name,
                    symbol_type=SymbolType.VARIABLES,
                    file_name=module_name,
                )
            )
    return list_of_symbols


def save_memory():
    memory_path = os.path.join(base_persist_dir, "memory.json")
    lock_path = memory_path + ".lock"
    
    with FileLock(lock_path, timeout=30):
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(memory, f, indent=2, ensure_ascii=False)
    
    load_memory()


def save_memory_with_new_memory(new_memory):
    memory_path = os.path.join(base_persist_dir, "memory.json")
    lock_path = memory_path + ".lock"
    
    with FileLock(lock_path, timeout=30):
        with open(memory_path, "w", encoding="utf-8") as f:
            json.dump(new_memory, f, indent=2, ensure_ascii=False)
    load_memory()        


def load_memory():    
    global memory
    memory_path = os.path.join(base_persist_dir, "memory.json")
    lock_path = memory_path + ".lock"
    
    if os.path.exists(memory_path):
        with FileLock(lock_path, timeout=30):
            with open(memory_path, "r", encoding="utf-8") as f:
                _memory = json.load(f)
            # clear memory
            memory.clear()
            memory.update(_memory)    
    return memory

def get_memory():    
    return load_memory()    


from autocoder.common.command_completer_v2 import CommandCompleterV2
completer = CommandCompleterV2(commands,
                             file_system_model=CCFileSystemModel(project_root=project_root,
                                                                defaut_exclude_dirs=defaut_exclude_dirs,
                                                                get_all_file_names_in_project=get_all_file_names_in_project,
                                                                get_all_file_in_project=get_all_file_in_project,
                                                                get_all_dir_names_in_project=get_all_dir_names_in_project,
                                                                get_all_file_in_project_with_dot=get_all_file_in_project_with_dot,
                                                                get_symbol_list=get_symbol_list
                                                                ),
                             memory_model=CCMemoryModel(get_memory_func=get_memory,
                                                         save_memory_func=save_memory))
def revert():
    result_manager = ResultManager()
    last_yaml_file = get_last_yaml_file("actions")
    if last_yaml_file:
        file_path = os.path.join("actions", last_yaml_file)

        with redirect_stdout() as output:
            auto_coder_main(["revert", "--file", file_path])
        s = output.getvalue()
        
        console = Console()
        panel = Panel(
            Markdown(s),
            title="Revert Result",
            border_style="green" if "Successfully reverted changes" in s else "red",
            padding=(1, 2),
            expand=False
        )
        console.print(panel)
        
        if "Successfully reverted changes" in s:
            result_manager.append(content=s, meta={"action": "revert","success":False, "input":{                
            }})                                    
        else:
            result_manager.append(content=s, meta={"action": "revert","success":False, "input":{                
            }})
    else:
        result_manager.append(content="No previous chat action found to revert.", meta={"action": "revert","success":False, "input":{                
            }})        


def add_files(args: List[str]):

    result_manager = ResultManager()
    if "groups" not in memory["current_files"]:
        memory["current_files"]["groups"] = {}
    if "groups_info" not in memory["current_files"]:
        memory["current_files"]["groups_info"] = {}
    if "current_groups" not in memory["current_files"]:
        memory["current_files"]["current_groups"] = []
    groups = memory["current_files"]["groups"]
    groups_info = memory["current_files"]["groups_info"]

    console = Console()
    printer = Printer()

    if not args:
        printer.print_in_terminal("add_files_no_args", style="red")
        result_manager.append(content=printer.get_message_from_key("add_files_no_args"), 
                              meta={"action": "add_files","success":False, "input":{ "args": args}})
        return

    if args[0] == "/refresh":
        completer.refresh_files()
        load_memory()
        console.print(
            Panel("Refreshed file list.",
                  title="Files Refreshed", border_style="green")
        )
        result_manager.append(content="Files refreshed.", 
                              meta={"action": "add_files","success":True, "input":{ "args": args}})
        return

    if args[0] == "/group":
        if len(args) == 1 or (len(args) == 2 and args[1] == "list"):
            if not groups:
                console.print(
                    Panel("No groups defined.", title="Groups",
                          border_style="yellow")
                )
                result_manager.append(content="No groups defined.", 
                              meta={"action": "add_files","success":False, "input":{ "args": args}})
            else:
                table = Table(
                    title="Defined Groups",
                    show_header=True,
                    header_style="bold magenta",
                    show_lines=True,
                )
                table.add_column("Group Name", style="cyan", no_wrap=True)
                table.add_column("Files", style="green")
                table.add_column("Query Prefix", style="yellow")
                table.add_column("Active", style="magenta")

                for i, (group_name, files) in enumerate(groups.items()):
                    query_prefix = groups_info.get(group_name, {}).get(
                        "query_prefix", ""
                    )
                    is_active = (
                        "✓"
                        if group_name in memory["current_files"]["current_groups"]
                        else ""
                    )
                    table.add_row(
                        group_name,
                        "\n".join([os.path.relpath(f, project_root)
                                  for f in files]),
                        query_prefix,
                        is_active,
                        end_section=(i == len(groups) - 1),
                    )
                console.print(Panel(table, border_style="blue"))
                result_manager.append(content="Defined groups.", 
                              meta={"action": "add_files","success":True, "input":{ "args": args}})
        elif len(args) >= 2 and args[1] == "/reset":
            memory["current_files"]["current_groups"] = []
            console.print(
                Panel(
                    "Active group names have been reset. If you want to clear the active files, you should use the command /remove_files /all.",
                    title="Groups Reset",
                    border_style="green",
                )
            )
            result_manager.append(content="Active group names have been reset. If you want to clear the active files, you should use the command /remove_files /all.", 
                              meta={"action": "add_files","success":True, "input":{ "args": args}})
        elif len(args) >= 3 and args[1] == "/add":
            group_name = args[2]
            groups[group_name] = memory["current_files"]["files"].copy()
            console.print(
                Panel(
                    f"Added group '{group_name}' with current files.",
                    title="Group Added",
                    border_style="green",
                )
            )
            result_manager.append(content=f"Added group '{group_name}' with current files.", 
                              meta={"action": "add_files","success":True, "input":{ "args": args}})

        elif len(args) >= 3 and args[1] == "/drop":
            group_name = args[2]
            if group_name in groups:
                del memory["current_files"]["groups"][group_name]
                if group_name in groups_info:
                    del memory["current_files"]["groups_info"][group_name]
                if group_name in memory["current_files"]["current_groups"]:
                    memory["current_files"]["current_groups"].remove(
                        group_name)
                console.print(
                    Panel(
                        f"Dropped group '{group_name}'.",
                        title="Group Dropped",
                        border_style="green",
                    )
                )
                result_manager.append(content=f"Dropped group '{group_name}'.", 
                              meta={"action": "add_files","success":True, "input":{ "args": args}})
            else:
                console.print(
                    Panel(
                        f"Group '{group_name}' not found.",
                        title="Error",
                        border_style="red",
                    )
                )
                result_manager.append(content=f"Group '{group_name}' not found.", 
                              meta={"action": "add_files","success":False, "input":{ "args": args}})
        elif len(args) == 3 and args[1] == "/set":
            group_name = args[2]

            def multiline_edit():
                from prompt_toolkit.lexers import PygmentsLexer
                from pygments.lexers.markup import MarkdownLexer
                from prompt_toolkit.formatted_text import HTML
                from prompt_toolkit.shortcuts import print_formatted_text

                style = Style.from_dict(
                    {
                        "dialog": "bg:#88ff88",
                        "dialog frame.label": "bg:#ffffff #000000",
                        "dialog.body": "bg:#000000 #00ff00",
                        "dialog shadow": "bg:#00aa00",
                    }
                )

                print_formatted_text(
                    HTML(
                        "<b>Type Atom Group Desc (Prese [Esc] + [Enter]  to finish.)</b><br/>"
                    )
                )
                text = prompt(
                    HTML("<ansicyan>║</ansicyan> "),
                    multiline=True,
                    lexer=PygmentsLexer(MarkdownLexer),
                    style=style,
                    wrap_lines=True,
                    prompt_continuation=HTML("<ansicyan>║</ansicyan> "),
                    rprompt=HTML("<ansicyan>║</ansicyan>"),
                )
                return text

            query_prefix = multiline_edit()
            if group_name in groups:
                groups_info[group_name] = {"query_prefix": query_prefix}
                console.print(
                    Panel(
                        f"Set Atom Group Desc for group '{group_name}'.",
                        title="Group Info Updated",
                        border_style="green",
                    )
                )
            else:
                console.print(
                    Panel(
                        f"Group '{group_name}' not found.",
                        title="Error",
                        border_style="red",
                    )
                )
        elif len(args) >= 2:
            # 支持多个组的合并，允许组名之间使用逗号或空格分隔
            group_names = " ".join(args[1:]).replace(",", " ").split()
            merged_files = set()
            missing_groups = []
            for group_name in group_names:
                if group_name in groups:
                    merged_files.update(groups[group_name])
                else:
                    missing_groups.append(group_name)

            if missing_groups:
                console.print(
                    Panel(
                        f"Group(s) not found: {', '.join(missing_groups)}",
                        title="Error",
                        border_style="red",
                    )
                )
                result_manager.append(content=f"Group(s) not found: {', '.join(missing_groups)}", 
                              meta={"action": "add_files","success":False, "input":{ "args": args}})

            if merged_files:
                memory["current_files"]["files"] = list(merged_files)
                memory["current_files"]["current_groups"] = [
                    name for name in group_names if name in groups
                ]
                console.print(
                    Panel(
                        f"Merged files from groups: {', '.join(group_names)}",
                        title="Files Merged",
                        border_style="green",
                    )
                )
                table = Table(
                    title="Current Files",
                    show_header=True,
                    header_style="bold magenta",
                    show_lines=True,  # 这会在每行之间添加分割线
                )
                table.add_column("File", style="green")
                for i, f in enumerate(memory["current_files"]["files"]):
                    table.add_row(
                        os.path.relpath(f, project_root),
                        end_section=(
                            i == len(memory["current_files"]["files"]) - 1
                        ),  # 在最后一行之后不添加分割线
                    )
                console.print(Panel(table, border_style="blue"))
                console.print(
                    Panel(
                        f"Active groups: {', '.join(memory['current_files']['current_groups'])}",
                        title="Active Groups",
                        border_style="green",
                    )
                )
                result_manager.append(content=f"Active groups: {', '.join(memory['current_files']['current_groups'])}", 
                              meta={"action": "add_files","success":True, "input":{ "args": args}})
            elif not missing_groups:
                console.print(
                    Panel(
                        "No files in the specified groups.",
                        title="No Files Added",
                        border_style="yellow",
                    )
                    )
                result_manager.append(content="No files in the specified groups.", 
                              meta={"action": "add_files","success":False, "input":{ "args": args}})
    else:
        existing_files = memory["current_files"]["files"]
        matched_files = find_files_in_project(args)

        files_to_add = [f for f in matched_files if f not in existing_files]
        if files_to_add:
            memory["current_files"]["files"].extend(files_to_add)
            table = Table(
                title=get_message("add_files_added_files"),
                show_header=True,
                header_style="bold magenta",
                show_lines=True,  # 这会在每行之间添加分割线
            )
            table.add_column("File", style="green")
            for i, f in enumerate(files_to_add):
                table.add_row(
                    os.path.relpath(f, project_root),
                    end_section=(
                        i == len(files_to_add) - 1
                    ),  # 在最后一行之后不添加分割线
                )
            console.print(Panel(table, border_style="green"))   
            result_manager.append(content=f"Added files: {', '.join(files_to_add)}", 
                              meta={"action": "add_files","success":True, "input":{ "args": args}})
        else:
            printer.print_in_terminal("add_files_matched", style="yellow")
            result_manager.append(content=f"No files matched.", 
                              meta={"action": "add_files","success":False, "input":{ "args": args}})

    save_memory()


def remove_files(file_names: List[str]):
    project_root = os.getcwd()
    printer = Printer()
    result_manager = ResultManager()

    if "/all" in file_names:
        memory["current_files"]["files"] = []
        memory["current_files"]["current_groups"] = []
        printer.print_in_terminal("remove_files_all", style="green")
        result_manager.append(content="All files removed.",
                              meta={"action": "remove_files","success":True, "input":{ "file_names": file_names}})
    else:
        files_to_remove = set()
        current_files_abs = memory["current_files"]["files"]

        for pattern in file_names:
            pattern = pattern.strip() # Remove leading/trailing whitespace
            if not pattern:
                continue

            is_wildcard = "*" in pattern or "?" in pattern

            for file_path_abs in current_files_abs:
                relative_path = os.path.relpath(file_path_abs, project_root)
                basename = os.path.basename(file_path_abs)

                matched = False
                if is_wildcard:
                    # Match pattern against relative path or basename
                    if fnmatch.fnmatch(relative_path, pattern) or fnmatch.fnmatch(basename, pattern):
                        matched = True
                else:
                    # Exact match against relative path, absolute path, or basename
                    if relative_path == pattern or file_path_abs == pattern or basename == pattern:
                        matched = True

                if matched:
                    files_to_remove.add(file_path_abs)

        removed_files_list = list(files_to_remove)
        if removed_files_list:
            # Update memory by filtering out the files to remove
            memory["current_files"]["files"] = [
                f for f in current_files_abs if f not in files_to_remove
            ]

            table = Table(
                show_header=True,
                header_style="bold magenta"
            )
            table.add_column(printer.get_message_from_key("file_column_title"), style="green")
            for f in removed_files_list:
                table.add_row(os.path.relpath(f, project_root))

            console = Console()
            console.print(
                Panel(table, border_style="green",
                      title=printer.get_message_from_key("files_removed")))
            result_manager.append(content=f"Removed files: {', '.join(removed_files_list)}",
                              meta={"action": "remove_files","success":True, "input":{ "file_names": file_names}})
        else:
            printer.print_in_terminal("remove_files_none", style="yellow")
            result_manager.append(content=printer.get_message_from_key("remove_files_none"), 
                              meta={"action": "remove_files","success":False, "input":{ "file_names": file_names}})    
    save_memory()

@run_in_raw_thread()
def ask(query: str):
    conf = memory.get("conf", {})
    yaml_config = {
        "include_file": ["./base/base.yml"],
    }
    yaml_config["query"] = query

    if "project_type" in conf:
        yaml_config["project_type"] = conf["project_type"]

    if "model" in conf:
        yaml_config["model"] = conf["model"]

    if "index_model" in conf:
        yaml_config["index_model"] = conf["index_model"]

    if "vl_model" in conf:
        yaml_config["vl_model"] = conf["vl_model"]

    if "code_model" in conf:
        yaml_config["code_model"] = conf["code_model"]

    if "product_mode" in conf:
        yaml_config["product_mode"] = conf["product_mode"]

    yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)

    execute_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(os.path.join(execute_file), "w",encoding="utf-8") as f:
        f.write(yaml_content)

    def execute_ask():
        auto_coder_main(["agent", "project_reader", "--file", execute_file])

    try:
        execute_ask()
    finally:
        os.remove(execute_file)


def get_llm_friendly_package_docs(
    package_name: Optional[str] = None, return_paths: bool = False
) -> List[str]:
    lib_dir = os.path.join(".auto-coder", "libs")
    llm_friendly_packages_dir = os.path.join(lib_dir, "llm_friendly_packages")
    docs = []

    if not os.path.exists(llm_friendly_packages_dir):
        return docs

    libs = list(memory.get("libs", {}).keys())

    for domain in os.listdir(llm_friendly_packages_dir):
        domain_path = os.path.join(llm_friendly_packages_dir, domain)
        if os.path.isdir(domain_path):
            for username in os.listdir(domain_path):
                username_path = os.path.join(domain_path, username)
                if os.path.isdir(username_path):
                    for lib_name in os.listdir(username_path):
                        lib_path = os.path.join(username_path, lib_name)
                        if (
                            os.path.isdir(lib_path)
                            and (
                                package_name is None
                                or lib_name == package_name
                                or package_name == os.path.join(username, lib_name)
                            )
                            and lib_name in libs
                        ):
                            for root, _, files in os.walk(lib_path):
                                for file in files:
                                    if file.endswith(".md"):
                                        file_path = os.path.join(root, file)
                                        if return_paths:
                                            docs.append(file_path)
                                        else:
                                            with open(file_path, "r",encoding="utf-8") as f:
                                                docs.append(f.read())

    return docs


def convert_yaml_to_config(yaml_file: str):
    from autocoder.auto_coder import AutoCoderArgs, load_include_files, Template

    args = AutoCoderArgs()
    with open(yaml_file, "r",encoding="utf-8") as f:
        config = yaml.safe_load(f)
        config = load_include_files(config, yaml_file)
        for key, value in config.items():
            if key != "file":  # 排除 --file 参数本身
                # key: ENV {{VARIABLE_NAME}}
                if isinstance(value, str) and value.startswith("ENV"):
                    template = Template(value.removeprefix("ENV").strip())
                    value = template.render(os.environ)
                setattr(args, key, value)
    return args

@run_in_raw_thread()
def mcp(query: str):
    query = query.strip()
    mcp_server = get_mcp_server()
    printer = Printer()

    # Handle remove command
    if query.startswith("/remove"):
        server_name = query.replace("/remove", "", 1).strip()
        response = mcp_server.send_request(
            McpRemoveRequest(server_name=server_name))
        if response.error:
            printer.print_in_terminal("mcp_remove_error", style="red", error=response.error)
        else:
            printer.print_in_terminal("mcp_remove_success", style="green", result=response.result)
        return

    # Handle list command
    if query.startswith("/list_running"):
        response = mcp_server.send_request(McpListRunningRequest())
        if response.error:
            printer.print_in_terminal("mcp_list_running_error", style="red", error=response.error)
        else:
            printer.print_in_terminal("mcp_list_running_title")
            printer.print_str_in_terminal(response.result)
        return

    # Handle list command
    if query.startswith("/list"):
        response = mcp_server.send_request(McpListRequest())
        if response.error:
            printer.print_in_terminal("mcp_list_builtin_error", style="red", error=response.error)
        else:
            printer.print_in_terminal("mcp_list_builtin_title")
            printer.print_str_in_terminal(response.result)
        return
        
    # Handle refresh command
    if query.startswith("/refresh"):
        server_name = query.replace("/refresh", "", 1).strip()    
        response = mcp_server.send_request(McpRefreshRequest(name=server_name or None))
        if response.error:
            printer.print_in_terminal("mcp_refresh_error", style="red", error=response.error)
        else:
            printer.print_in_terminal("mcp_refresh_success", style="green")
        return

    # Handle add command
    if query.startswith("/add"):
        query = query.replace("/add", "", 1).strip()
        request = McpInstallRequest(server_name_or_config=query)
        response = mcp_server.send_request(request)

        if response.error:
            printer.print_in_terminal("mcp_install_error", style="red", error=response.error)
        else:
            printer.print_in_terminal("mcp_install_success", style="green", result=response.result)
        return

    # Handle default query
    conf = memory.get("conf", {})
    yaml_config = {
        "include_file": ["./base/base.yml"],
        "auto_merge": conf.get("auto_merge", "editblock"),
        "human_as_model": conf.get("human_as_model", "false") == "true",
        "skip_build_index": conf.get("skip_build_index", "true") == "true",
        "skip_confirm": conf.get("skip_confirm", "true") == "true",
        "silence": conf.get("silence", "true") == "true",
        "include_project_structure": conf.get("include_project_structure", "true")
        == "true",
        "exclude_files": memory.get("exclude_files", []),
    }
    for key, value in conf.items():
        converted_value = convert_config_value(key, value)
        if converted_value is not None:
            yaml_config[key] = converted_value

    temp_yaml = os.path.join("actions", f"{uuid.uuid4()}.yml")
    try:
        with open(temp_yaml, "w",encoding="utf-8") as f:
            f.write(convert_yaml_config_to_str(yaml_config=yaml_config))
        args = convert_yaml_to_config(temp_yaml)
    finally:
        if os.path.exists(temp_yaml):
            os.remove(temp_yaml)

    mcp_server = get_mcp_server()   


    if query.startswith("/info"):
        response = mcp_server.send_request(McpServerInfoRequest(
            model=args.inference_model or args.model,
            product_mode=args.product_mode
        ))
        if response.error:
            printer.print_in_terminal("mcp_server_info_error", style="red", error=response.error)
        else:
            printer.print_in_terminal("mcp_server_info_title")
            printer.print_str_in_terminal(response.result)
        return

    response = mcp_server.send_request(
        McpRequest(
            query=query,
            model=args.inference_model or args.model,
            product_mode=args.product_mode
        )
    )

    if response.error:
        printer.print_panel(
            f"Error from MCP server: {response.error}",
            text_options={"justify": "left"},
            panel_options={
                "title": printer.get_message_from_key("mcp_error_title"),
                "border_style": "red"
            }
        )
    else:
        # Save conversation
        mcp_dir = os.path.join(".auto-coder", "mcp", "conversations")
        os.makedirs(mcp_dir, exist_ok=True)
        timestamp = str(int(time.time()))
        file_path = os.path.join(mcp_dir, f"{timestamp}.md")

        # Format response as markdown
        markdown_content = response.result

        # Save to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        console = Console()
        console.print(
            Panel(
                Markdown(markdown_content, justify="left"),
                title=printer.get_message_from_key('mcp_response_title'),
                border_style="green"
            )
        )


@run_in_raw_thread()
def code_next(query: str):
    conf = memory.get("conf", {})
    yaml_config = {
        "include_file": ["./base/base.yml"],
        "auto_merge": conf.get("auto_merge", "editblock"),
        "human_as_model": conf.get("human_as_model", "false") == "true",
        "skip_build_index": conf.get("skip_build_index", "true") == "true",
        "skip_confirm": conf.get("skip_confirm", "true") == "true",
        "silence": conf.get("silence", "true") == "true",
        "include_project_structure": conf.get("include_project_structure", "true")
        == "true",
        "exclude_files": memory.get("exclude_files", []),
    }
    for key, value in conf.items():
        converted_value = convert_config_value(key, value)
        if converted_value is not None:
            yaml_config[key] = converted_value

    temp_yaml = os.path.join("actions", f"{uuid.uuid4()}.yml")
    try:
        with open(temp_yaml, "w",encoding="utf-8") as f:
            f.write(convert_yaml_config_to_str(yaml_config=yaml_config))
        args = convert_yaml_to_config(temp_yaml)
    finally:
        if os.path.exists(temp_yaml):
            os.remove(temp_yaml)

    product_mode = conf.get("product_mode", "lite")
    llm = get_single_llm(args.chat_model or args.model, product_mode=product_mode)

    auto_guesser = AutoGuessQuery(
        llm=llm, project_dir=os.getcwd(), skip_diff=True)

    predicted_tasks = auto_guesser.predict_next_tasks(
        5, is_human_as_model=args.human_as_model
    )

    if not predicted_tasks:
        console = Console()
        console.print(Panel("No task predictions available", style="yellow"))
        return

    console = Console()

    # Create main panel for all predicted tasks
    table = Table(show_header=True,
                  header_style="bold magenta", show_lines=True)
    table.add_column("Priority", style="cyan", width=8)
    table.add_column("Task Description", style="green",
                     width=40, overflow="fold")
    table.add_column("Files", style="yellow", width=30, overflow="fold")
    table.add_column("Reason", style="blue", width=30, overflow="fold")
    table.add_column("Dependencies", style="magenta",
                     width=30, overflow="fold")

    for task in predicted_tasks:
        # Format file paths to be more readable
        file_list = "\n".join([os.path.relpath(f, os.getcwd())
                              for f in task.urls])

        # Format dependencies to be more readable
        dependencies = (
            "\n".join(
                task.dependency_queries) if task.dependency_queries else "None"
        )

        table.add_row(
            str(task.priority), task.query, file_list, task.reason, dependencies
        )

    console.print(
        Panel(
            table,
            title="[bold]Predicted Next Tasks[/bold]",
            border_style="blue",
            padding=(1, 2),  # Add more horizontal padding
        )
    )


@run_in_raw_thread()
def commit(query: str):
    conf = memory.get("conf", {})
    product_mode = conf.get("product_mode", "lite")
    def prepare_commit_yaml():
        auto_coder_main(["next", "chat_action"])

    prepare_commit_yaml()

    # no_diff = query.strip().startswith("/no_diff")
    # if no_diff:
    #     query = query.replace("/no_diff", "", 1).strip()

    latest_yaml_file = get_last_yaml_file("actions")

    conf = memory.get("conf", {})
    current_files = memory["current_files"]["files"]
    execute_file = None

    if latest_yaml_file:
        try:
            execute_file = os.path.join("actions", latest_yaml_file)
            yaml_config = {
                "include_file": ["./base/base.yml"],
                "auto_merge": conf.get("auto_merge", "editblock"),
                "human_as_model": conf.get("human_as_model", "false") == "true",
                "skip_build_index": conf.get("skip_build_index", "true") == "true",
                "skip_confirm": conf.get("skip_confirm", "true") == "true",
                "silence": conf.get("silence", "true") == "true",
                "include_project_structure": conf.get("include_project_structure", "true")
                == "true",
            }
            for key, value in conf.items():
                converted_value = convert_config_value(key, value)
                if converted_value is not None:
                    yaml_config[key] = converted_value

            yaml_config["urls"] = current_files + get_llm_friendly_package_docs(
                return_paths=True
            )

            if conf.get("enable_global_memory", "false") in ["true", "True",True]:
                yaml_config["urls"] += get_global_memory_file_paths()

            # 临时保存yaml文件，然后读取yaml文件，转换为args
            temp_yaml = os.path.join("actions", f"{uuid.uuid4()}.yml")
            try:
                with open(temp_yaml, "w",encoding="utf-8") as f:
                    f.write(convert_yaml_config_to_str(
                        yaml_config=yaml_config))
                args = convert_yaml_to_config(temp_yaml)
            finally:
                if os.path.exists(temp_yaml):
                    os.remove(temp_yaml)

            target_model = args.commit_model or args.model
            llm = get_single_llm(target_model, product_mode)
            printer = Printer()
            printer.print_in_terminal("commit_generating", style="yellow", model_name=target_model)
            commit_message = ""

            try:
                uncommitted_changes = git_utils.get_uncommitted_changes(".")
                commit_message = git_utils.generate_commit_message.with_llm(llm).run(
                    uncommitted_changes
                )                
                # memory["conversation"].append(
                #     {"role": "user", "content": commit_message})
            except Exception as e:
                printer.print_in_terminal("commit_failed", style="red", error=str(e), model_name=target_model)
                return

            yaml_config["query"] = commit_message
            yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)
            with open(os.path.join(execute_file), "w",encoding="utf-8") as f:
                f.write(yaml_content)

            args.file = execute_file             
            
            file_name = os.path.basename(execute_file)
            commit_result = git_utils.commit_changes(
                ".", f"{commit_message}\nauto_coder_{file_name}"
            )

            printer = Printer()

            action_yml_file_manager = ActionYmlFileManager(args.source_dir)
            action_file_name = os.path.basename(args.file)
            add_updated_urls = []            
            for file in commit_result.changed_files:
                add_updated_urls.append(os.path.join(args.source_dir, file))

            args.add_updated_urls = add_updated_urls
            update_yaml_success = action_yml_file_manager.update_yaml_field(action_file_name, "add_updated_urls", add_updated_urls)
            if not update_yaml_success:                        
                printer.print_in_terminal("yaml_save_error", style="red", yaml_file=action_file_name)  
                        
            if args.enable_active_context:                
                active_context_manager = ActiveContextManager(llm, args.source_dir)
                task_id = active_context_manager.process_changes(args)
                printer.print_in_terminal("active_context_background_task", 
                                             style="blue",
                                             task_id=task_id)
            git_utils.print_commit_info(commit_result=commit_result)
            if commit_message:
                printer.print_in_terminal("commit_message", style="green", model_name=target_model, message=commit_message)                
        except Exception as e:
            import traceback
            traceback.print_exc()            
            print(f"Failed to commit: {e}")
            if execute_file:
                os.remove(execute_file)


@run_in_raw_thread()
def coding(query: str):    
    console = Console()
    is_apply = query.strip().startswith("/apply")
    if is_apply:
        query = query.replace("/apply", "", 1).strip()

    is_next = query.strip().startswith("/next")
    if is_next:
        query = query.replace("/next", "", 1).strip()

    if is_next:
        code_next(query)
        return

    # memory["conversation"].append({"role": "user", "content": query})
    conf = memory.get("conf", {})

    current_files = memory["current_files"]["files"]
    current_groups = memory["current_files"].get("current_groups", [])
    groups = memory["current_files"].get("groups", {})
    groups_info = memory["current_files"].get("groups_info", {})

    def prepare_chat_yaml():
        auto_coder_main(["next", "chat_action"])

    prepare_chat_yaml()

    latest_yaml_file = get_last_yaml_file("actions")

    if latest_yaml_file:
        yaml_config = {
            "include_file": ["./base/base.yml"],
            "auto_merge": conf.get("auto_merge", "editblock"),
            "human_as_model": conf.get("human_as_model", "false") == "true",
            "skip_build_index": conf.get("skip_build_index", "true") == "true",
            "skip_confirm": conf.get("skip_confirm", "true") == "true",
            "silence": conf.get("silence", "true") == "true",
            "include_project_structure": conf.get("include_project_structure", "true")
            == "true",
            "exclude_files": memory.get("exclude_files", []),
        }

        yaml_config["context"] = ""        
        yaml_config["in_code_apply"] = is_apply

        for key, value in conf.items():
            converted_value = convert_config_value(key, value)
            if converted_value is not None:
                yaml_config[key] = converted_value

        yaml_config["urls"] = current_files + get_llm_friendly_package_docs(
            return_paths=True
        )

        if conf.get("enable_global_memory", "false") in ["true", "True",True]:
            yaml_config["urls"] += get_global_memory_file_paths()

        # handle image
        v = Image.convert_image_paths_from(query)
        yaml_config["query"] = v

        # Add context for active groups and their query prefixes
        if current_groups:
            active_groups_context = "下面是对上面文件按分组给到的一些描述，当用户的需求正好匹配描述的时候，参考描述来做修改：\n"
            for group in current_groups:
                group_files = groups.get(group, [])
                query_prefix = groups_info.get(
                    group, {}).get("query_prefix", "")
                active_groups_context += f"组名: {group}\n"
                active_groups_context += f"文件列表:\n"
                for file in group_files:
                    active_groups_context += f"- {file}\n"
                active_groups_context += f"组描述: {query_prefix}\n\n"

            yaml_config["context"] = active_groups_context + "\n"

        if is_apply:
            memory_dir = os.path.join(".auto-coder", "memory")
            os.makedirs(memory_dir, exist_ok=True)
            memory_file = os.path.join(memory_dir, "chat_history.json")

            def error_message():
                console.print(
                    Panel(
                        "No chat history found to apply.",
                        title="Chat History",
                        expand=False,
                        border_style="yellow",
                    )
                )

            conversations = []
            if os.path.exists(memory_file):            
                with open(memory_file, "r",encoding="utf-8") as f:
                    chat_history = json.load(f)

                if not chat_history["ask_conversation"]:
                    error_message()                    
                else: 
                    conversations = chat_history["ask_conversation"]
            
            if conversations:
                yaml_config[
                    "context"
                ] += f"下面是我们的历史对话，参考我们的历史对话从而更好的理解需求和修改代码: \n\n<history>\n"
                for conv in conversations:
                    if conv["role"] == "user":
                        yaml_config["context"] += f"用户: {conv['content']}\n"
                    elif conv["role"] == "assistant":
                        yaml_config["context"] += f"你: {conv['content']}\n"
                yaml_config["context"] += "</history>\n"

        yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)        

        execute_file = os.path.join("actions", latest_yaml_file)
        with open(os.path.join(execute_file), "w",encoding="utf-8") as f:
            f.write(yaml_content)

        def execute_chat():
            cmd = ["--file", execute_file]
            auto_coder_main(cmd)
            result_manager = ResultManager()
            result_manager.append(content="", meta={"commit_message": f"auto_coder_{latest_yaml_file}","action": "coding", "input":{
                "query": query
            }})

        execute_chat()
    else:
        print("Failed to create new YAML file.")

    save_memory()
    completer.refresh_files()

@run_in_raw_thread()
def rules(query: str):
    from autocoder.chat.rules_command import handle_rules_command
    memory = get_memory()
    handle_rules_command(query, memory,coding_func=coding) 
    completer.refresh_files()   

@byzerllm.prompt()
def code_review(query: str) -> str:
    """
    掐面提供了上下文，对代码进行review，参考如下检查点。
    1. 有没有调用不符合方法，类的签名的调用，包括对第三方类，模块，方法的检查（如果上下文提供了这些信息）
    2. 有没有未声明直接使用的变量，方法，类
    3. 有没有明显的语法错误
    4. 如果是python代码，检查有没有缩进方面的错误
    5. 如果是python代码，检查是否 try 后面缺少 except 或者 finally
    {% if query %}
    6. 用户的额外的检查需求：{{ query }}
    {% endif %}

    如果用户的需求包含了@一个文件名 或者 @@符号， 那么重点关注这些文件或者符号（函数，类）进行上述的review。
    review 过程中严格遵循上述的检查点，不要遗漏，没有发现异常的点直接跳过，只对发现的异常点，给出具体的修改后的代码。
    """


@run_in_raw_thread()
def chat(query: str):
    conf = memory.get("conf", {})

    yaml_config = {
        "include_file": ["./base/base.yml"],
        "include_project_structure": conf.get("include_project_structure", "true")
        in ["true", "True"],
        "human_as_model": conf.get("human_as_model", "false") == "true",
        "skip_build_index": conf.get("skip_build_index", "true") == "true",
        "skip_confirm": conf.get("skip_confirm", "true") == "true",
        "silence": conf.get("silence", "true") == "true",
        "exclude_files": memory.get("exclude_files", []),
    }

    current_files = memory["current_files"]["files"] + get_llm_friendly_package_docs(
        return_paths=True
    )

    if conf.get("enable_global_memory", "false") in ["true", "True",True]:
        current_files += get_global_memory_file_paths()

    yaml_config["urls"] = current_files

    if "emb_model" in conf:
        yaml_config["emb_model"] = conf["emb_model"]

    # 解析命令        
    commands_infos = CommandParser.parse_query(query)    
    if len(commands_infos) > 0:
        if "query" in commands_infos:
            query = " ".join(commands_infos["query"]["args"])
        else:            
            temp_query = ""
            for (command,command_info) in commands_infos.items():
                if command_info["args"]:
                    temp_query = " ".join(command_info["args"])                    
            query = temp_query

    is_new = "new" in commands_infos

    if "learn" in commands_infos:
        commands_infos["no_context"] = {}

    if "review" in commands_infos:
        commands_infos["no_context"] = {}

    yaml_config["action"] = commands_infos            
    
    for key, value in conf.items():
        converted_value = convert_config_value(key, value)
        if converted_value is not None:
            yaml_config[key] = converted_value

    query = Image.convert_image_paths_from(query)

    yaml_config["query"] = query

    yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)

    execute_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(os.path.join(execute_file), "w",encoding="utf-8") as f:
        f.write(yaml_content)

    def execute_ask():
        cmd = ["agent", "chat", "--file", execute_file]
        if is_new:
            cmd.append("--new_session")
        auto_coder_main(cmd)

    try:
        execute_ask()
    finally:
        os.remove(execute_file)


@run_in_raw_thread()
def summon(query: str):
    conf = memory.get("conf", {})
    current_files = memory["current_files"]["files"]

    file_contents = []
    for file in current_files:
        if os.path.exists(file):
            try:
                with open(file, "r",encoding="utf-8") as f:
                    content = f.read()
                    s = f"##File: {file}\n{content}\n\n"
                    file_contents.append(s)
            except Exception as e:
                print(f"Failed to read file: {file}. Error: {str(e)}")

    all_file_content = "".join(file_contents)

    yaml_config = {
        "include_file": ["./base/base.yml"],
    }
    yaml_config["query"] = query
    yaml_config["context"] = json.dumps(
        {"file_content": all_file_content}, ensure_ascii=False
    )

    if "emb_model" in conf:
        yaml_config["emb_model"] = conf["emb_model"]

    if "vl_model" in conf:
        yaml_config["vl_model"] = conf["vl_model"]

    if "code_model" in conf:
        yaml_config["code_model"] = conf["code_model"]

    if "model" in conf:
        yaml_config["model"] = conf["model"]

    if "product_mode" in conf:
        yaml_config["product_mode"] = conf["product_mode"]

    yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)

    execute_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(os.path.join(execute_file), "w",encoding="utf-8") as f:
        f.write(yaml_content)

    def execute_summon():
        auto_coder_main(["agent", "auto_tool", "--file", execute_file])

    try:
        execute_summon()
    finally:
        os.remove(execute_file)


@run_in_raw_thread()
def design(query: str):

    conf = memory.get("conf", {})
    yaml_config = {
        "include_file": ["./base/base.yml"],
    }

    if query.strip().startswith("/svg"):
        query = query.replace("/svg", "", 1).strip()
        yaml_config["agent_designer_mode"] = "svg"
    elif query.strip().startswith("/sd"):
        query = query.replace("/svg", "", 1).strip()
        yaml_config["agent_designer_mode"] = "sd"
    elif query.strip().startswith("/logo"):
        query = query.replace("/logo", "", 1).strip()
        yaml_config["agent_designer_mode"] = "logo"
    else:
        yaml_config["agent_designer_mode"] = "svg"

    yaml_config["query"] = query

    if "model" in conf:
        yaml_config["model"] = conf["model"]

    if "designer_model" in conf:
        yaml_config["designer_model"] = conf["designer_model"]

    if "sd_model" in conf:
        yaml_config["sd_model"] = conf["sd_model"]

    yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)

    execute_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(os.path.join(execute_file), "w",encoding="utf-8") as f:
        f.write(yaml_content)

    def execute_design():
        auto_coder_main(["agent", "designer", "--file", execute_file])

    try:
        execute_design()
    finally:
        os.remove(execute_file)


@run_in_raw_thread()
def active_context(query: str):
    """
    管理活动上下文任务，支持列表、查询等操作
    
    Args:
        query: 命令参数，例如 "list" 列出所有任务
    """    
    # 解析命令
    commands_infos = CommandParser.parse_query(query)
    command = "list"  # 默认命令是列出所有任务
    
    if len(commands_infos) > 0:
        if "list" in commands_infos:
            command = "list"
        if "run" in commands_infos:
            command = "run"
    
    args = get_final_config()
    printer = Printer()
    # 获取LLM实例    
    llm = get_single_llm(args.model,product_mode=args.product_mode)
    action_file_manager = ActionYmlFileManager(args.source_dir)
    
    # 获取配置和参数
    
    
    active_context_manager = ActiveContextManager(llm, args.source_dir)
    if command == "run":
        file_name = commands_infos["run"]["args"][-1]
        args.file = action_file_manager.get_full_path_by_file_name(file_name)        
        ## 因为更新了args.file
        active_context_manager = ActiveContextManager(llm, args.source_dir)
        task_id = active_context_manager.process_changes(args)
        printer.print_in_terminal("active_context_background_task", 
                                        style="blue",
                                        task_id=task_id)

    # 处理不同的命令
    if command == "list":
        # 获取所有任务
        all_tasks = active_context_manager.get_all_tasks()
        
        if not all_tasks:
            console = Console()
            console.print("[yellow]没有找到任何活动上下文任务[/yellow]")
            return
        
        # 创建表格
        table = Table(title="活动上下文任务列表", show_lines=True, expand=True)
        table.add_column("任务ID", style="cyan", no_wrap=False)
        table.add_column("状态", style="green", no_wrap=False)
        table.add_column("开始时间", style="yellow", no_wrap=False)
        table.add_column("完成时间", style="yellow", no_wrap=False)
        table.add_column("文件", style="blue", no_wrap=False)
        table.add_column("Token统计", style="magenta", no_wrap=False)
        table.add_column("费用", style="red", no_wrap=False)
        
        # 添加任务数据
        for task in all_tasks:
            status = task.get("status", "未知")
            status_display = status
            
            # 根据状态设置不同的显示样式
            if status == "completed":
                status_display = "[green]已完成[/green]"
            elif status == "running":
                status_display = "[blue]运行中[/blue]"
            elif status == "queued":
                position = task.get("queue_position", 0)
                status_display = f"[yellow]排队中 (位置: {position})[/yellow]"
            elif status == "failed":
                status_display = "[red]失败[/red]"
            
            # 格式化时间
            start_time = task.get("start_time", "") 
            start_time_str = start_time.strftime("%Y-%m-%d %H:%M:%S") if start_time else "未知"
            
            completion_time = task.get("completion_time", "")
            completion_time_str = completion_time.strftime("%Y-%m-%d %H:%M:%S") if completion_time else "-"
            
            # 获取文件名
            file_name = task.get("file_name", "未知")
            
            # 获取token信息
            total_tokens = task.get("total_tokens", 0)
            input_tokens = task.get("input_tokens", 0)
            output_tokens = task.get("output_tokens", 0)
            token_info = f"总计: {total_tokens:,}\n输入: {input_tokens:,}\n输出: {output_tokens:,}"
            
            # 获取费用信息
            cost = task.get("cost", 0.0)
            cost_info = f"${cost:.6f}"
            
            # 添加到表格
            table.add_row(
                task.get("task_id", "未知"),
                status_display,
                start_time_str,
                completion_time_str,
                file_name,
                token_info,
                cost_info
            )
        
        # 显示表格
        console = Console(width=120)  # 设置更宽的显示宽度
        console.print(table)


def voice_input():
    conf = memory.get("conf", {})
    yaml_config = {
        "include_file": ["./base/base.yml"],
    }

    if "voice2text_model" not in conf:
        print(
            "Please set voice2text_model in configuration. /conf voice2text_model:<model>"
        )
        return

    yaml_config["voice2text_model"] = conf["voice2text_model"]
    yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)

    execute_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(os.path.join(execute_file), "w",encoding="utf-8") as f:
        f.write(yaml_content)

    def execute_voice2text_command():
        auto_coder_main(["agent", "voice2text", "--file", execute_file])

    try:
        execute_voice2text_command()
        with open(os.path.join(".auto-coder", "exchange.txt"), "r",encoding="utf-8") as f:
            return f.read()
    finally:
        os.remove(execute_file)


@run_in_raw_thread()
def generate_shell_command(input_text):
    conf = memory.get("conf", {})
    yaml_config = {
        "include_file": ["./base/base.yml"],
    }

    if "model" in conf:
        yaml_config["model"] = conf["model"]

    yaml_config["query"] = input_text

    yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)

    execute_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(os.path.join(execute_file), "w",encoding="utf-8") as f:
        f.write(yaml_content)

    try:
        auto_coder_main(["agent", "generate_command", "--file", execute_file])
        with open(os.path.join(".auto-coder", "exchange.txt"), "r",encoding="utf-8") as f:
            shell_script = f.read()
        result_manager = ResultManager()
        result_manager.add_result(content=shell_script,meta={
            "action": "generate_shell_command",
            "input": {
                "query": input_text
            }
        })
        return shell_script
    finally:
        os.remove(execute_file)

def manage_models(query: str):
    """    
    Handle /models subcommands:
      /models /list - List all models (default + custom)
      /models /add <name> <api_key> - Add model with simplified params
      /models /add_model name=xxx base_url=xxx ... - Add model with custom params
      /models /remove <name> - Remove model by name
    """
    console = Console()
    printer = Printer(console=console)    
    
    product_mode = memory.get("product_mode", "lite")
    if product_mode != "lite":
        printer.print_in_terminal("models_lite_only", style="red")
        return

    models_data = models_module.load_models()
    subcmd = ""
    if "/list" in query:
        subcmd = "/list"
        query = query.replace("/list", "", 1).strip()

    if "/add_model" in query:
        subcmd = "/add_model"
        query = query.replace("/add_model", "", 1).strip()

    if "/add" in query:
        subcmd = "/add"
        query = query.replace("/add", "", 1).strip()

    # alias to /add
    if "/activate" in query:
        subcmd = "/add"
        query = query.replace("/activate", "", 1).strip()    

    if "/remove" in query:
        subcmd = "/remove"
        query = query.replace("/remove", "", 1).strip()

    if "/speed-test" in query:
        subcmd = "/speed-test"
        query = query.replace("/speed-test", "", 1).strip()

    if "/speed_test" in query:
        subcmd = "/speed-test"
        query = query.replace("/speed_test", "", 1).strip() 

    if "input_price" in query:
        subcmd = "/input_price"
        query = query.replace("/input_price", "", 1).strip()

    if "output_price" in query:
        subcmd = "/output_price"
        query = query.replace("/output_price", "", 1).strip()        

    if "/speed" in query:
        subcmd = "/speed"
        query = query.replace("/speed", "", 1).strip()



    if not subcmd:
        printer.print_in_terminal("models_usage")        

    result_manager = ResultManager()
    if subcmd == "/list":                    
        if models_data:
            # Sort models by speed (average_speed)
            sorted_models = sorted(models_data, key=lambda x: float(x.get('average_speed', 0)))
            sorted_models.reverse()

            table = Table(
                title=printer.get_message_from_key("models_title"),
                expand=True,
                show_lines=True
            )
            table.add_column("Name", style="cyan", width=30, overflow="fold", no_wrap=False)
            table.add_column("Model Name", style="magenta", width=30, overflow="fold", no_wrap=False)
            table.add_column("Base URL", style="white", width=40, overflow="fold", no_wrap=False)
            table.add_column("Input Price (M)", style="magenta", width=15, overflow="fold", no_wrap=False)
            table.add_column("Output Price (M)", style="magenta", width=15, overflow="fold", no_wrap=False)
            table.add_column("Speed (s/req)", style="blue", width=15, overflow="fold", no_wrap=False)
            for m in sorted_models:
                # Check if api_key_path exists and file exists
                is_api_key_set = "api_key" in m  
                name = m.get("name", "")              
                if is_api_key_set:
                    api_key = m.get("api_key", "").strip()                    
                    if not api_key:                                                
                        printer.print_in_terminal("models_api_key_empty", style="yellow", name=name)                                           
                    name = f"{name} *"

                table.add_row(
                    name,                    
                    m.get("model_name", ""),                    
                    m.get("base_url", ""),
                    f"{m.get('input_price', 0.0):.2f}",
                    f"{m.get('output_price', 0.0):.2f}",
                    f"{m.get('average_speed', 0.0):.3f}"
                )
            console.print(table)
            result_manager.add_result(content=json.dumps(sorted_models,ensure_ascii=False),meta={
                "action": "models",
                "input": {
                    "query": query
                }
            })

        else:
            printer.print_in_terminal("models_no_models", style="yellow")
            result_manager.add_result(content="No models found",meta={
                "action": "models",
                "input": {
                    "query": query
                }
            })

    elif subcmd == "/input_price":
        args = query.strip().split()
        if len(args) >= 2:
            name = args[0]
            try:
                price = float(args[1])
                if models_module.update_model_input_price(name, price):
                    printer.print_in_terminal("models_input_price_updated", style="green", name=name, price=price)
                    result_manager.add_result(content=f"models_input_price_updated: {name} {price}",meta={
                        "action": "models",
                        "input": {
                            "query": query
                        }
                    })
                else:
                    printer.print_in_terminal("models_not_found", style="red", name=name)
                    result_manager.add_result(content=f"models_not_found: {name}",meta={
                        "action": "models",
                        "input": {
                            "query": query
                        }
                    })
            except ValueError as e:
                result_manager.add_result(content=f"models_invalid_price: {str(e)}",meta={
                    "action": "models",
                    "input": {
                        "query": query
                    }
                })
                printer.print_in_terminal("models_invalid_price", style="red", error=str(e))
        else:
            result_manager.add_result(content=printer.get_message_from_key("models_input_price_usage"),meta={
                "action": "models",
                "input": {
                    "query": query
                }
            })
            printer.print_in_terminal("models_input_price_usage", style="red")

    elif subcmd == "/output_price":
        args = query.strip().split()
        if len(args) >= 2:
            name = args[0]
            try:
                price = float(args[1])
                if models_module.update_model_output_price(name, price):
                    printer.print_in_terminal("models_output_price_updated", style="green", name=name, price=price)
                    result_manager.add_result(content=f"models_output_price_updated: {name} {price}",meta={
                        "action": "models",
                        "input": {
                            "query": query
                        }
                    })
                else:
                    printer.print_in_terminal("models_not_found", style="red", name=name)
                    result_manager.add_result(content=f"models_not_found: {name}",meta={
                        "action": "models",
                        "input": {
                            "query": query
                        }
                    })
            except ValueError as e:
                printer.print_in_terminal("models_invalid_price", style="red", error=str(e))
                result_manager.add_result(content=f"models_invalid_price: {str(e)}",meta={
                    "action": "models",
                    "input": {
                        "query": query
                    }
                })
        else:
            result_manager.add_result(content=printer.get_message_from_key("models_output_price_usage"),meta={
                "action": "models",
                "input": {
                    "query": query
                }
            })
            printer.print_in_terminal("models_output_price_usage", style="red")

    elif subcmd == "/speed":
        args = query.strip().split()
        if len(args) >= 2:
            name = args[0]
            try:
                speed = float(args[1])
                if models_module.update_model_speed(name, speed):
                    printer.print_in_terminal("models_speed_updated", style="green", name=name, speed=speed)
                    result_manager.add_result(content=f"models_speed_updated: {name} {speed}",meta={
                        "action": "models",
                        "input": {
                            "query": query
                        }
                    })
                else:
                    printer.print_in_terminal("models_not_found", style="red", name=name)
                    result_manager.add_result(content=f"models_not_found: {name}",meta={
                        "action": "models",
                        "input": {
                            "query": query
                        }
                    })
            except ValueError as e:
                printer.print_in_terminal("models_invalid_speed", style="red", error=str(e))
                result_manager.add_result(content=f"models_invalid_speed: {str(e)}",meta={
                    "action": "models",
                    "input": {
                        "query": query
                    }
                })
        else:
            result_manager.add_result(content=printer.get_message_from_key("models_speed_usage"),meta={
                "action": "models",
                "input": {
                    "query": query
                }
            })
            printer.print_in_terminal("models_speed_usage", style="red")

    elif subcmd == "/speed-test":
        from autocoder.common.model_speed_tester import render_speed_test_in_terminal
        test_rounds = 1  # 默认测试轮数

        enable_long_context = False
        if "/long_context" in query:
            enable_long_context = True
            query = query.replace("/long_context", "", 1).strip()

        if "/long-context" in query:
            enable_long_context = True
            query = query.replace("/long-context", "", 1).strip()

        # 解析可选的测试轮数参数
        args = query.strip().split()
        if args and args[0].isdigit():
            test_rounds = int(args[0])

        render_speed_test_in_terminal(product_mode, test_rounds,enable_long_context=enable_long_context)
        ## 等待优化，获取明细数据
        result_manager.add_result(content="models test success",meta={
            "action": "models",
            "input": {
                "query": query
            }
        })

    elif subcmd == "/add":
        # Support both simplified and legacy formats
        args = query.strip().split(" ")               
        if len(args) == 2:
            # Simplified: /models /add <name> <api_key>
            name, api_key = args[0], args[1]            
            result = models_module.update_model_with_api_key(name, api_key)
            if result:
                result_manager.add_result(content=f"models_added: {name}",meta={
                    "action": "models",
                    "input": {
                        "query": query
                    }
                })
                printer.print_in_terminal("models_added", style="green", name=name)
            else:
                result_manager.add_result(content=f"models_add_failed: {name}",meta={
                    "action": "models",
                    "input": {
                        "query": query
                    }
                })
                printer.print_in_terminal("models_add_failed", style="red", name=name)
        else:            
            models_list = "\n".join([m["name"] for m in models_module.default_models_list])                     
            printer.print_in_terminal("models_add_usage", style="red", models=models_list)
            result_manager.add_result(content=printer.get_message_from_key_with_format("models_add_usage",models=models_list),meta={
                "action": "models",
                "input": {
                    "query": query
                }
            })

    elif subcmd == "/add_model":
        # Parse key=value pairs: /models /add_model name=abc base_url=http://xx ...       
        # Collect key=value pairs
        kv_pairs = shlex.split(query)
        data_dict = {}
        for pair in kv_pairs:
            if '=' not in pair:
                printer.print_in_terminal("models_add_model_params", style="red")
                continue
            k, v = pair.split('=', 1)
            data_dict[k.strip()] = v.strip()

        # Name is required
        if "name" not in data_dict:
            printer.print_in_terminal("models_add_model_name_required", style="red")
            return

        # Check duplication
        if any(m["name"] == data_dict["name"] for m in models_data):
            printer.print_in_terminal("models_add_model_exists", style="yellow", name=data_dict["name"])
            result_manager.add_result(content=printer.get_message_from_key_with_format("models_add_model_exists",name=data_dict["name"]),meta={
                "action": "models",
                "input": {
                    "query": query
                }
            })
            return

        # Create model with defaults
        final_model = {
            "name": data_dict["name"],
            "model_type": data_dict.get("model_type", "saas/openai"),
            "model_name": data_dict.get("model_name", data_dict["name"]),
            "base_url": data_dict.get("base_url", "https://api.openai.com/v1"),
            "api_key_path": data_dict.get("api_key_path", "api.openai.com"),
            "description": data_dict.get("description", ""),
            "is_reasoning": data_dict.get("is_reasoning", "false") in ["true", "True", "TRUE", "1"]
        }

        models_data.append(final_model)
        models_module.save_models(models_data)
        printer.print_in_terminal("models_add_model_success", style="green", name=data_dict["name"])
        result_manager.add_result(content=f"models_add_model_success: {data_dict['name']}",meta={
            "action": "models",
            "input": {
                "query": query
            }
        })

    elif subcmd == "/remove":
        args = query.strip().split(" ")
        if len(args) < 1:
            printer.print_in_terminal("models_add_usage", style="red")
            result_manager.add_result(content=printer.get_message_from_key("models_add_usage"),meta={
                "action": "models",
                "input": {
                    "query": query
                }
            })
            return
        name = args[0]
        filtered_models = [m for m in models_data if m["name"] != name]
        if len(filtered_models) == len(models_data):
            printer.print_in_terminal("models_add_model_remove", style="yellow", name=name)
            result_manager.add_result(content=printer.get_message_from_key_with_format("models_add_model_remove",name=name),meta={
                "action": "models",
                "input": {
                    "query": query
                }
            })
            return
        models_module.save_models(filtered_models)
        printer.print_in_terminal("models_add_model_removed", style="green", name=name)
        result_manager.add_result(content=printer.get_message_from_key_with_format("models_add_model_removed",name=name),meta={ 
            "action": "models",
            "input": {
                "query": query
            }
        })
    else:
        printer.print_in_terminal("models_unknown_subcmd", style="yellow", subcmd=subcmd)
        result_manager.add_result(content=printer.get_message_from_key_with_format("models_unknown_subcmd",subcmd=subcmd),meta={ 
            "action": "models",
            "input": {
                "query": query
            }
        })

def exclude_dirs(dir_names: List[str]):
    new_dirs = dir_names
    existing_dirs = memory.get("exclude_dirs", [])    
    dirs_to_add = [d for d in new_dirs if d not in existing_dirs]
    
    if dirs_to_add:
        existing_dirs.extend(dirs_to_add)
        if "exclude_dirs" not in memory:
            memory["exclude_dirs"] = existing_dirs
        print(f"Added exclude dirs: {dirs_to_add}")
        exclude_files([f"regex://.*/{d}/*." for d in dirs_to_add])            
    else:
        print("All specified dirs are already in the exclude list.")
    save_memory()
    completer.refresh_files()

def exclude_files(query: str):
    result_manager = ResultManager()
    printer = Printer()
    if "/list" in query:
        query = query.replace("/list", "", 1).strip()
        existing_file_patterns = memory.get("exclude_files", []) 
        console = Console()
        # 打印表格
        table = Table(title="Exclude Files")
        table.add_column("File Pattern")
        for file_pattern in existing_file_patterns:
            table.add_row(file_pattern)
        console.print(table)
        result_manager.add_result(content=f"Exclude files: {existing_file_patterns}",meta={
            "action": "exclude_files",
            "input": {
                "query": query
            }
        })
        return

    if "/drop" in query:
        query = query.replace("/drop", "", 1).strip()
        existing_file_patterns = memory.get("exclude_files", [])    
        existing_file_patterns.remove(query.strip())
        memory["exclude_files"] = existing_file_patterns
        save_memory()
        completer.refresh_files()
        result_manager.add_result(content=f"Dropped exclude files: {query}",meta={
            "action": "exclude_files",
            "input": {
                "query": query
            }
        })
        return
    
    new_file_patterns = query.strip().split(",")
    
    existing_file_patterns = memory.get("exclude_files", [])    
    file_patterns_to_add = [f for f in new_file_patterns if f not in existing_file_patterns]

    for file_pattern in file_patterns_to_add:
        if not file_pattern.startswith("regex://"): 
            result_manager.add_result(content=printer.get_message_from_key_with_format("invalid_file_pattern", file_pattern=file_pattern),meta={
                "action": "exclude_files",
                "input": {
                    "query": file_pattern
                }
            })
            raise ValueError(printer.get_message_from_key_with_format("invalid_file_pattern", file_pattern=file_pattern))

    if file_patterns_to_add:
        existing_file_patterns.extend(file_patterns_to_add)
        if "exclude_files" not in memory:
            memory["exclude_files"] = existing_file_patterns
        
        result_manager.add_result(content=f"Added exclude files: {file_patterns_to_add}",meta={
            "action": "exclude_files",
            "input": {
                "query": file_patterns_to_add
            }
        })
        save_memory()
        print(f"Added exclude files: {file_patterns_to_add}")
    else:
        result_manager.add_result(content=f"All specified files are already in the exclude list.",meta={
            "action": "exclude_files",
            "input": {
                "query": file_patterns_to_add
            }
        })
        print("All specified files are already in the exclude list.")
    
    

@run_in_raw_thread()
def index_build():
    conf = memory.get("conf", {})
    yaml_config = {
        "include_file": ["./base/base.yml"],
        "exclude_files": memory.get("exclude_files", []),
    }

    for key, value in conf.items():
        converted_value = convert_config_value(key, value)
        if converted_value is not None:
            yaml_config[key] = converted_value

    yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)
    yaml_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(yaml_file, "w",encoding="utf-8") as f:
        f.write(yaml_content)
    try:        
        auto_coder_main(["index", "--file", yaml_file])        
        completer.refresh_files()
    finally:
        os.remove(yaml_file)


def get_final_config()->AutoCoderArgs:
    conf = memory.get("conf", {})
    yaml_config = {
        "include_file": ["./base/base.yml"],
        "auto_merge": conf.get("auto_merge", "editblock"),
        "human_as_model": conf.get("human_as_model", "false") == "true",
        "skip_build_index": conf.get("skip_build_index", "true") == "true",
        "skip_confirm": conf.get("skip_confirm", "true") == "true",
        "silence": conf.get("silence", "true") == "true",
        "include_project_structure": conf.get("include_project_structure", "true")
        == "true",
        "exclude_files": memory.get("exclude_files", []),
    }
    for key, value in conf.items():
        converted_value = convert_config_value(key, value)
        if converted_value is not None:
            yaml_config[key] = converted_value

    temp_yaml = os.path.join("actions", f"{uuid.uuid4()}.yml")
    try:
        with open(temp_yaml, "w",encoding="utf-8") as f:
            f.write(convert_yaml_config_to_str(yaml_config=yaml_config))
        args = convert_yaml_to_config(temp_yaml)
    finally:
        if os.path.exists(temp_yaml):
            os.remove(temp_yaml)
    return args

def help(query: str):
    from autocoder.common.auto_configure import ConfigAutoTuner,MemoryConfig,AutoConfigRequest        
    args = get_final_config()
    product_mode = memory.get("product_mode", "lite")
    llm = get_single_llm(args.chat_model or args.model, product_mode=product_mode)
    auto_config_tuner = ConfigAutoTuner(args=args, llm=llm, memory_config=MemoryConfig(memory=memory, save_memory_func=save_memory))
    auto_config_tuner.tune(AutoConfigRequest(query=query))    

@run_in_raw_thread()
def index_export(path: str):
    from autocoder.common.index_import_export import export_index
    from autocoder.common.printer import Printer
    printer = Printer()
    project_root = os.getcwd()
    if export_index(project_root, path):
        printer.print_in_terminal("index_export_success", path=path)
    else:
        printer.print_in_terminal("index_export_fail", path=path)

@run_in_raw_thread()
def index_import(path: str):
    from autocoder.common.index_import_export import import_index
    from autocoder.common.printer import Printer
    printer = Printer()
    project_root = os.getcwd()
    if import_index(project_root, path):
        printer.print_in_terminal("index_import_success", path=path)
    else:
        printer.print_in_terminal("index_import_fail", path=path)

@run_in_raw_thread()
def index_query(query: str):
    from autocoder.index.entry import build_index_and_filter_files
    from autocoder.pyproject import PyProject
    from autocoder.tsproject import TSProject
    from autocoder.suffixproject import SuffixProject

    config = get_final_config()
    config.query = query
    config.skip_filter_index = False
    llm = get_single_llm(config.chat_model or config.model, product_mode=config.product_mode)

    if config.project_type == "ts":
        pp = TSProject(args=config, llm=llm)
    elif config.project_type == "py":
        pp = PyProject(args=config, llm=llm)
    else:
        pp = SuffixProject(args=config, llm=llm, file_filter=None)
    pp.run()
    sources = pp.sources    
    source_code_list = build_index_and_filter_files(llm=llm, args=config, sources=sources)
    return source_code_list    

def list_files():
    console = Console()
    project_root = os.getcwd()
    current_files = memory["current_files"]["files"]

    if current_files:
        table = Table(
            title="Current Files", show_header=True, header_style="bold magenta"
        )
        table.add_column("File", style="green")
        for file in current_files:
            table.add_row(os.path.relpath(file, project_root))
        console.print(Panel(table, border_style="blue"))
    else:
        console.print(
            Panel(
                "No files in the current session.",
                title="Current Files",
                border_style="yellow",
            )
        )


def gen_and_exec_shell_command(query: str):
    from rich.prompt import Confirm    
    from autocoder.common.printer import Printer 
    from rich.console import Console
    
    printer = Printer()
    console = Console()
    # Generate the shell script
    shell_script = generate_shell_command(query)    

    # Ask for confirmation using rich
    if Confirm.ask(
        printer.get_message_from_key("confirm_execute_shell_script"),
        default=False
    ):
        execute_shell_command(shell_script)
    else:
        console.print(
            Panel(
                printer.get_message_from_key("shell_script_not_executed"),
                border_style="yellow"
            )
        )


def lib_command(args: List[str]):
    console = Console()
    lib_dir = os.path.join(".auto-coder", "libs")
    llm_friendly_packages_dir = os.path.join(lib_dir, "llm_friendly_packages")

    if not os.path.exists(lib_dir):
        os.makedirs(lib_dir)

    if "libs" not in memory:
        memory["libs"] = {}

    if not args:
        console.print(
            "Please specify a subcommand: /add, /remove, /list, /list_all, /set-proxy, /refresh, or /get"
        )
        return

    subcommand = args[0]

    if subcommand == "/add":
        if len(args) < 2:
            console.print("Please specify a library name to add")
            return
        lib_name = args[1].strip()

        # Clone the repository if it doesn't exist
        if not os.path.exists(llm_friendly_packages_dir):
            console.print("Cloning llm_friendly_packages repository...")
            try:
                proxy_url = memory.get(
                    "lib-proxy", "https://github.com/allwefantasy/llm_friendly_packages"
                )
                git.Repo.clone_from(
                    proxy_url,
                    llm_friendly_packages_dir,
                )
                console.print(
                    "Successfully cloned llm_friendly_packages repository")
            except git.exc.GitCommandError as e:
                console.print(f"Error cloning repository: {e}")

        if lib_name in memory["libs"]:
            console.print(f"Library {lib_name} is already added")
        else:
            memory["libs"][lib_name] = {}
            console.print(f"Added library: {lib_name}")

            save_memory()

    elif subcommand == "/remove":
        if len(args) < 2:
            console.print("Please specify a library name to remove")
            return
        lib_name = args[1].strip()
        if lib_name in memory["libs"]:
            del memory["libs"][lib_name]
            console.print(f"Removed library: {lib_name}")
            save_memory()
        else:
            console.print(f"Library {lib_name} is not in the list")

    elif subcommand == "/list":
        if memory["libs"]:
            table = Table(title="Added Libraries")
            table.add_column("Library Name", style="cyan")
            for lib_name in memory["libs"]:
                table.add_row(lib_name)
            console.print(table)
        else:
            console.print("No libraries added yet")
            
    elif subcommand == "/list_all":
        if not os.path.exists(llm_friendly_packages_dir):
            console.print("llm_friendly_packages repository does not exist. Please run /lib /add <library_name> command first to clone it.")
            return
            
        available_libs = []
        
        # 遍历所有domain目录
        for domain in os.listdir(llm_friendly_packages_dir):
            domain_path = os.path.join(llm_friendly_packages_dir, domain)
            if os.path.isdir(domain_path):
                # 遍历所有username目录
                for username in os.listdir(domain_path):
                    username_path = os.path.join(domain_path, username)
                    if os.path.isdir(username_path):
                        # 遍历所有lib_name目录
                        for lib_name in os.listdir(username_path):
                            lib_path = os.path.join(username_path, lib_name)
                            if os.path.isdir(lib_path):
                                # 检查是否有Markdown文件
                                has_md_files = False
                                for root, _, files in os.walk(lib_path):
                                    if any(file.endswith('.md') for file in files):
                                        has_md_files = True
                                        break
                                
                                if has_md_files:
                                    available_libs.append({
                                        "domain": domain,
                                        "username": username,
                                        "lib_name": lib_name,
                                        "full_path": f"{username}/{lib_name}",
                                        "is_added": lib_name in memory["libs"]
                                    })
        
        if available_libs:
            table = Table(title="Available Libraries")
            table.add_column("Domain", style="blue")
            table.add_column("Username", style="green")
            table.add_column("Library Name", style="cyan")
            table.add_column("Full Path", style="magenta")
            table.add_column("Status", style="yellow")
            
            # 按domain和username分组排序
            available_libs.sort(key=lambda x: (x["domain"], x["username"], x["lib_name"]))
            
            for lib in available_libs:
                status = "[green]Added[/green]" if lib["is_added"] else "[white]Not Added[/white]"
                table.add_row(
                    lib["domain"],
                    lib["username"],
                    lib["lib_name"],
                    lib["full_path"],
                    status
                )
            
            console.print(table)
        else:
            console.print("No available libraries found in the repository.")

    elif subcommand == "/set-proxy":
        if len(args) == 1:
            current_proxy = memory.get("lib-proxy", "No proxy set")
            console.print(f"Current proxy: {current_proxy}")
        elif len(args) == 2:
            proxy_url = args[1]
            memory["lib-proxy"] = proxy_url
            console.print(f"Set proxy to: {proxy_url}")
            save_memory()
        else:
            console.print("Invalid number of arguments for /set-proxy")

    elif subcommand == "/refresh":
        if os.path.exists(llm_friendly_packages_dir):
            try:
                repo = git.Repo(llm_friendly_packages_dir)
                origin = repo.remotes.origin
                proxy_url = memory.get("lib-proxy")

                current_url = origin.url

                if proxy_url and proxy_url != current_url:
                    new_url = proxy_url
                    origin.set_url(new_url)
                    console.print(f"Updated remote URL to: {new_url}")

                origin.pull()
                console.print(
                    "Successfully updated llm_friendly_packages repository")

            except git.exc.GitCommandError as e:
                console.print(f"Error updating repository: {e}")
        else:
            console.print(
                "llm_friendly_packages repository does not exist. Please run /lib /add <library_name> command first to clone it."
            )

    elif subcommand == "/get":
        if len(args) < 2:
            console.print("Please specify a package name to get")
            return
        package_name = args[1].strip()
        docs = get_llm_friendly_package_docs(package_name, return_paths=True)
        if docs:
            table = Table(title=f"Markdown Files for {package_name}")
            table.add_column("File Path", style="cyan")
            for doc in docs:
                table.add_row(doc)
            console.print(table)
        else:
            console.print(
                f"No markdown files found for package: {package_name}")

    else:
        console.print(f"Unknown subcommand: {subcommand}")


def execute_shell_command(command: str):
    from autocoder.common.shells import execute_shell_command as shell_exec
    shell_exec(command)


def conf_export(path: str):
    from autocoder.common.conf_import_export import export_conf
    export_conf(os.getcwd(), path)

def conf_import(path: str):
    from autocoder.common.conf_import_export import import_conf
    import_conf(os.getcwd(), path)

def generate_new_yaml(query: str):
    memory = get_memory()
    conf = memory.get("conf",{})
    current_files = memory.get("current_files",{}).get("files",[])
    auto_coder_main(["next", "chat_action"])        
    latest_yaml_file = get_last_yaml_file("actions")
    if latest_yaml_file:
        yaml_config = {
            "include_file": ["./base/base.yml"],
            "auto_merge": conf.get("auto_merge", "editblock"),
            "human_as_model": conf.get("human_as_model", "false") == "true",
            "skip_build_index": conf.get("skip_build_index", "true") == "true",
            "skip_confirm": conf.get("skip_confirm", "true") == "true",
            "silence": conf.get("silence", "true") == "true",
            "include_project_structure": conf.get("include_project_structure", "true")
            == "true",
            "exclude_files": memory.get("exclude_files", []),
        }
        yaml_config["context"] = ""                    
        for key, value in conf.items():
            converted_value = convert_config_value(key, value)
            if converted_value is not None:
                yaml_config[key] = converted_value

        yaml_config["urls"] = current_files + get_llm_friendly_package_docs(
            return_paths=True
        )
        # handle image
        v = Image.convert_image_paths_from(query)
        yaml_config["query"] = v                    

        yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)        

        execute_file = os.path.join("actions", latest_yaml_file)
        with open(os.path.join(execute_file), "w",encoding="utf-8") as f:
            f.write(yaml_content)
        return execute_file,convert_yaml_to_config(execute_file)

@run_in_raw_thread()
def auto_command(query: str,extra_args: Dict[str,Any]={}):    
    """处理/auto指令"""        
    args = get_final_config() 
    memory = get_memory()         
    if args.enable_agentic_edit:        
        from autocoder.run_context import get_run_context,RunMode
        execute_file,args = generate_new_yaml(query)
        args.file = execute_file                      
        current_files = memory.get("current_files",{}).get("files",[])
        sources = []
        for file in current_files:
            try:
                with open(file,"r",encoding="utf-8") as f:
                    sources.append(SourceCode(module_name=file,source_code=f.read()))  
            except Exception as e:
                global_logger.error(f"Failed to read file {file}: {e}")
                    
        llm = get_single_llm(args.code_model or args.model,product_mode=args.product_mode) 
        conversation_history = extra_args.get("conversations",[])   
        agent = AgenticEdit(llm=llm,args=args,files=SourceCodeList(sources=sources), 
                            conversation_history=conversation_history,
                            memory_config=MemoryConfig(memory=memory, 
                            save_memory_func=save_memory), command_config=CommandConfig,
                            conversation_name="current"
                            )           
        if get_run_context().mode == RunMode.WEB:
            agent.run_with_events(AgenticEditRequest(user_input=query))
        else:
            agent.run_in_terminal(AgenticEditRequest(user_input=query))
            
        completer.refresh_files()
        return
        
    args = get_final_config()  
    # 准备请求参数
    request = AutoCommandRequest(
        user_input=query        
    )

    # 初始化调优器
    llm = get_single_llm(args.chat_model or args.model,product_mode=args.product_mode)    
    tuner = CommandAutoTuner(llm, 
                             args=args,
                             memory_config=MemoryConfig(memory=memory, save_memory_func=save_memory), 
                             command_config=CommandConfig(
                                 add_files=add_files,
                                 remove_files=remove_files,
                                 list_files=list_files,
                                 conf=configure,
                                 revert=revert,
                                 commit=commit,
                                 help=help,
                                 exclude_dirs=exclude_dirs,
                                 exclude_files=exclude_files,
                                 ask=ask,
                                 chat=chat,
                                 coding=coding,
                                 design=design,
                                 summon=summon,
                                 lib=lib_command,
                                 mcp=mcp,
                                 models=manage_models,
                                 index_build=index_build,
                                 index_query=index_query,  
                                 execute_shell_command=execute_shell_command,  
                                 generate_shell_command=generate_shell_command,
                                 conf_export=conf_export,
                                 conf_import=conf_import,
                                 index_export=index_export,
                                 index_import=index_import                                                                                       
                             ))

    # 生成建议
    response = tuner.analyze(request)
    printer = Printer()
    # 显示建议
    console = Console()        
    console.print(Panel(
        Markdown(response.reasoning or ""),
        title=printer.get_message_from_key_with_format("auto_command_reasoning_title"),
        border_style="blue",
        padding=(1, 2)
    ))
    completer.refresh_files()
