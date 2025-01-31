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
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from prompt_toolkit.shortcuts import confirm
from autocoder.common import AutoCoderArgs
from pydantic import Field, BaseModel
from autocoder.version import __version__
from autocoder.auto_coder import main as auto_coder_main
from autocoder.common.command_completer import CommandTextParser
from autocoder.utils import get_last_yaml_file
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
from rich.text import Text
from rich.live import Live
from rich.markdown import Markdown
from byzerllm.utils.nontext import Image
import git
from autocoder.common import git_utils
from autocoder.chat_auto_coder_lang import get_message
from autocoder.utils import operate_config_api
from autocoder.agent.auto_guess_query import AutoGuessQuery
from autocoder.common.mcp_server import get_mcp_server, McpRequest, McpInstallRequest, McpRemoveRequest, McpListRequest, McpListRunningRequest, McpRefreshRequest
import byzerllm
from byzerllm.utils import format_str_jinja2
from autocoder.common.memory_manager import get_global_memory_file_paths 
from autocoder import models
import shlex
from autocoder.utils.llms import get_single_llm

class SymbolItem(BaseModel):
    symbol_name: str
    symbol_type: SymbolType
    file_name: str


def parse_arguments():
    import argparse

    parser = argparse.ArgumentParser(description="Chat Auto Coder")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode")
    parser.add_argument(
        "--quick",
        action="store_true",
        help="Enter the auto-coder.chat without initializing the system",
    )

    parser.add_argument(
        "--product_mode",
        type=str,
        default="pro",
        help="The mode of the auto-coder.chat, lite/pro default is pro",
    )

    parser.add_argument("--lite", action="store_true", help="Lite mode")
    parser.add_argument("--pro", action="store_true", help="Pro mode")

    return parser.parse_args()


ARGS = None

if platform.system() == "Windows":
    from colorama import init

    init()


memory = {
    "conversation": [],
    "current_files": {"files": [], "groups": {}},
    "conf": {},
    "exclude_dirs": [],
    "mode": "normal",  # 新增mode字段,默认为normal模式
}

project_root = os.getcwd()

base_persist_dir = os.path.join(".auto-coder", "plugins", "chat-auto-coder")

defaut_exclude_dirs = [".git", "node_modules", "dist", "build", "__pycache__"]

commands = [
    "/add_files",
    "/remove_files",
    "/list_files",
    "/conf",
    "/coding",
    "/chat",
    "/ask",
    "/commit",
    "/revert",
    "/index/query",
    "/index/build",
    "/exclude_dirs",
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
]


def show_help():
    print(f"\033[1m{get_message('supported_commands')}\033[0m")
    print()
    print(
        f"  \033[94m{get_message('commands')}\033[0m - \033[93m{get_message('description')}\033[0m"
    )
    print(
        f"  \033[94m/add_files\033[0m \033[93m<file1> <file2> ...\033[0m - \033[92m{get_message('add_files_desc')}\033[0m"
    )
    print(
        f"  \033[94m/remove_files\033[0m \033[93m<file1>,<file2> ...\033[0m - \033[92m{get_message('remove_files_desc')}\033[0m"
    )
    print(
        f"  \033[94m/chat\033[0m \033[93m<query>\033[0m - \033[92m{get_message('chat_desc')}\033[0m"
    )
    print(
        f"  \033[94m/coding\033[0m \033[93m<query>\033[0m - \033[92m{get_message('coding_desc')}\033[0m"
    )
    print(
        f"  \033[94m/ask\033[0m \033[93m<query>\033[0m - \033[92m{get_message('ask_desc')}\033[0m"
    )
    print(
        f"  \033[94m/summon\033[0m \033[93m<query>\033[0m - \033[92m{get_message('summon_desc')}\033[0m"
    )
    print(
        f"  \033[94m/revert\033[0m - \033[92m{get_message('revert_desc')}\033[0m")
    print(
        f"  \033[94m/commit\033[0m - \033[92m{get_message('commit_desc')}\033[0m")
    print(
        f"  \033[94m/conf\033[0m \033[93m<key>:<value>\033[0m  - \033[92m{get_message('conf_desc')}\033[0m"
    )
    print(
        f"  \033[94m/index/query\033[0m \033[93m<args>\033[0m - \033[92m{get_message('index_query_desc')}\033[0m"
    )
    print(
        f"  \033[94m/index/build\033[0m - \033[92m{get_message('index_build_desc')}\033[0m"
    )
    print(
        f"  \033[94m/list_files\033[0m - \033[92m{get_message('list_files_desc')}\033[0m"
    )
    print(
        f"  \033[94m/help\033[0m - \033[92m{get_message('help_desc')}\033[0m")
    print(
        f"  \033[94m/exclude_dirs\033[0m \033[93m<dir1>,<dir2> ...\033[0m - \033[92m{get_message('exclude_dirs_desc')}\033[0m"
    )
    print(
        f"  \033[94m/shell\033[0m \033[93m<command>\033[0m - \033[92m{get_message('shell_desc')}\033[0m"
    )
    print(
        f"  \033[94m/voice_input\033[0m - \033[92m{get_message('voice_input_desc')}\033[0m"
    )
    print(
        f"  \033[94m/mode\033[0m - \033[92m{get_message('mode_desc')}\033[0m")
    print(f"  \033[94m/lib\033[0m - \033[92m{get_message('lib_desc')}\033[0m")
    print(f"  \033[94m/models\033[0m - \033[92m{get_message('models_desc')}\033[0m")
    print(
        f"  \033[94m/exit\033[0m - \033[92m{get_message('exit_desc')}\033[0m")
    print()


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

    project_type = prompt(
        get_message("enter_project_type"), default="py", style=style
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


def initialize_system(args):
    print(f"\n\033[1;34m{get_message('initializing')}\033[0m")

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
        first_time = False
        if not os.path.exists(".auto-coder"):
            first_time = True
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
            print_status(get_message("created_dir").format(
                base_persist_dir), "success")

        if first_time:
            configure_project_type()

        print_status(get_message("init_complete"), "success")

    init_project()

    if args.product_mode == "lite":
        # Setup deepseek api key
        api_key_dir = os.path.expanduser("~/.auto-coder/keys")
        api_key_file = os.path.join(api_key_dir, "api.deepseek.com")
        
        if not os.path.exists(api_key_file):
            print_status(get_message("model_not_available"), "warning")
            api_key = prompt(HTML(f"<b>{get_message('enter_api_key')} </b>"))
            
            # Create directory if it doesn't exist
            os.makedirs(api_key_dir, exist_ok=True)
            
            # Save the API key
            with open(api_key_file, "w") as f:
                f.write(api_key)
            
            print_status(f"API key saved successfully: {api_key_file}", "success")                    

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
                ["easy-byzerllm", "chat", "deepseek_chat", "你好"],
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
            "deepseek_chat",
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
                ["easy-byzerllm", "chat", "deepseek_chat", "你好"],
                capture_output=True,
                text=True,
                timeout=30,
                check=True,
            )
            print_status(get_message("validation_success"), "success")
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
            print_status(get_message("validation_fail"), "error")
            print_status(get_message("manual_start"), "warning")
            print_status("easy-byzerllm chat deepseek_chat 你好", "")

        print_status(get_message("init_complete_final"), "success")


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
        if value.lower() in ["true", "false"]:
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
    parts = conf.split(None, 1)
    if len(parts) == 2 and parts[0] in ["/drop", "/unset", "/remove"]:
        key = parts[1].strip()
        if key in memory["conf"]:
            del memory["conf"][key]
            save_memory()
            print(f"\033[92mDeleted configuration: {key}\033[0m")
        else:
            print(f"\033[93mConfiguration not found: {key}\033[0m")
    else:
        parts = conf.split(":", 1)
        if len(parts) != 2:
            print(
                "\033[91mError: Invalid configuration format. Use 'key:value' or '/drop key'.\033[0m"
            )
            return
        key, value = parts
        key = key.strip()
        value = value.strip()
        if not value:
            print("\033[91mError: Value cannot be empty. Use 'key:value'.\033[0m")
            return
        memory["conf"][key] = value
        save_memory()
        if not skip_print:
            print(f"\033[92mSet {key} to {value}\033[0m")

# word_completer = WordCompleter(commands)


def get_symbol_list() -> List[SymbolItem]:
    list_of_symbols = []
    index_file = os.path.join(".auto-coder", "index.json")

    if os.path.exists(index_file):
        with open(index_file, "r") as file:
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


class CommandCompleter(Completer):
    def __init__(self, commands):
        self.commands = commands
        self.all_file_names = get_all_file_names_in_project()
        self.all_files = get_all_file_in_project()
        self.all_dir_names = get_all_dir_names_in_project()
        self.all_files_with_dot = get_all_file_in_project_with_dot()
        self.symbol_list = get_symbol_list()
        self.current_file_names = []

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()

        if len(words) > 0:
            if words[0] == "/mode":
                left_word = text[len("/mode"):]
                for mode in ["normal", "auto_detect", "voice_input"]:
                    if mode.startswith(left_word.strip()):
                        yield Completion(mode, start_position=-len(left_word.strip()))

            if words[0] == "/add_files":
                new_text = text[len("/add_files"):]
                parser = CommandTextParser(new_text, words[0])
                parser.add_files()
                current_word = parser.current_word()

                if parser.last_sub_command() == "/refresh":
                    return

                for command in parser.get_sub_commands():
                    if command.startswith(current_word):
                        yield Completion(command, start_position=-len(current_word))

                if parser.first_sub_command() == "/group" and (
                    parser.last_sub_command() == "/group"
                    or parser.last_sub_command() == "/drop"
                ):
                    group_names = memory["current_files"]["groups"].keys()
                    if "," in current_word:
                        current_word = current_word.split(",")[-1]

                    for group_name in group_names:
                        if group_name.startswith(current_word):
                            yield Completion(
                                group_name, start_position=-len(current_word)
                            )

                if parser.first_sub_command() != "/group":
                    if current_word and current_word.startswith("."):
                        for file_name in self.all_files_with_dot:
                            if file_name.startswith(current_word):
                                yield Completion(
                                    file_name, start_position=-
                                    len(current_word)
                                )
                    else:
                        for file_name in self.all_file_names:
                            if file_name.startswith(current_word):
                                yield Completion(
                                    file_name, start_position=-
                                    len(current_word)
                                )
                        for file_name in self.all_files:
                            if current_word and current_word in file_name:
                                yield Completion(
                                    file_name, start_position=-
                                    len(current_word)
                                )
            elif words[0] in ["/chat", "/coding"]:
                image_extensions = (
                    ".png",
                    ".jpg",
                    ".jpeg",
                    ".gif",
                    ".bmp",
                    ".tiff",
                    ".tif",
                    ".webp",
                    ".svg",
                    ".ico",
                    ".heic",
                    ".heif",
                    ".raw",
                    ".cr2",
                    ".nef",
                    ".arw",
                    ".dng",
                    ".orf",
                    ".rw2",
                    ".pef",
                    ".srw",
                    ".eps",
                    ".ai",
                    ".psd",
                    ".xcf",
                )
                new_text = text[len(words[0]):]
                parser = CommandTextParser(new_text, words[0])

                parser.coding()
                current_word = parser.current_word()

                if len(new_text.strip()) == 0 or new_text.strip() == "/":
                    for command in parser.get_sub_commands():
                        if command.startswith(current_word):
                            yield Completion(command, start_position=-len(current_word))

                all_tags = parser.tags

                if current_word.startswith("@"):
                    name = current_word[1:]
                    target_set = set()

                    for file_name in self.current_file_names:
                        base_file_name = os.path.basename(file_name)
                        if name in base_file_name:
                            target_set.add(base_file_name)
                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else file_name
                            )
                            relative_path = os.path.relpath(
                                file_name, project_root)
                            yield Completion(
                                relative_path,
                                start_position=-len(name),
                                display=f"{display_name} (in active files)",
                            )

                    for file_name in self.all_file_names:
                        if file_name.startswith(name) and file_name not in target_set:
                            target_set.add(file_name)

                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else file_name
                            )
                            relative_path = os.path.relpath(
                                file_name, project_root)

                            yield Completion(
                                relative_path,
                                start_position=-len(name),
                                display=f"{display_name}",
                            )

                    for file_name in self.all_files:
                        if name in file_name and file_name not in target_set:
                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else file_name
                            )
                            relative_path = os.path.relpath(
                                file_name, project_root)
                            yield Completion(
                                relative_path,
                                start_position=-len(name),
                                display=f"{display_name}",
                            )

                if current_word.startswith("@@"):
                    name = current_word[2:]
                    for symbol in self.symbol_list:
                        if name in symbol.symbol_name:
                            file_name = symbol.file_name
                            path_parts = file_name.split(os.sep)
                            display_name = (
                                os.sep.join(path_parts[-3:])
                                if len(path_parts) > 3
                                else symbol.symbol_name
                            )
                            relative_path = os.path.relpath(
                                file_name, project_root)
                            yield Completion(
                                f"{symbol.symbol_name}(location: {relative_path})",
                                start_position=-len(name),
                                display=f"{symbol.symbol_name} ({display_name}/{symbol.symbol_type})",
                            )

                tags = [tag for tag in parser.tags]

                if current_word.startswith("<"):
                    name = current_word[1:]
                    for tag in ["<img>", "</img>"]:
                        if all_tags and all_tags[-1].start_tag == "<img>":
                            if tag.startswith(name):
                                yield Completion(
                                    "</img>", start_position=-len(current_word)
                                )
                        elif tag.startswith(name):
                            yield Completion(tag, start_position=-len(current_word))

                if tags and tags[-1].start_tag == "<img>" and tags[-1].end_tag == "":
                    raw_file_name = tags[0].content
                    file_name = raw_file_name.strip()
                    parent_dir = os.path.dirname(file_name)
                    file_basename = os.path.basename(file_name)
                    search_dir = parent_dir if parent_dir else "."
                    for root, dirs, files in os.walk(search_dir):
                        # 只处理直接子目录
                        if root != search_dir:
                            continue

                        # 补全子目录
                        for dir in dirs:
                            full_path = os.path.join(root, dir)
                            if full_path.startswith(file_name):
                                relative_path = os.path.relpath(
                                    full_path, search_dir)
                                yield Completion(
                                    relative_path,
                                    start_position=-len(file_basename),
                                )

                        # 补全文件
                        for file in files:
                            if file.lower().endswith(
                                image_extensions
                            ) and file.startswith(file_basename):
                                full_path = os.path.join(root, file)
                                relative_path = os.path.relpath(
                                    full_path, search_dir)
                                yield Completion(
                                    relative_path,
                                    start_position=-len(file_basename),
                                )

                        # 只处理一层子目录，然后退出循环
                        break

            elif words[0] == "/remove_files":
                new_words = text[len("/remove_files"):].strip().split(",")

                is_at_space = text[-1] == " "
                last_word = new_words[-2] if len(new_words) > 1 else ""
                current_word = new_words[-1] if new_words else ""

                if is_at_space:
                    last_word = current_word
                    current_word = ""

                # /remove_files /all [cursor] or /remove_files /all p[cursor]
                if not last_word and not current_word:
                    if "/all".startswith(current_word):
                        yield Completion("/all", start_position=-len(current_word))
                    for file_name in self.current_file_names:
                        yield Completion(file_name, start_position=-len(current_word))

                # /remove_files /a[cursor] or /remove_files p[cursor]
                if current_word:
                    if "/all".startswith(current_word):
                        yield Completion("/all", start_position=-len(current_word))
                    for file_name in self.current_file_names:
                        if current_word and current_word in file_name:
                            yield Completion(
                                file_name, start_position=-len(current_word)
                            )
            elif words[0] == "/exclude_dirs":
                new_words = text[len("/exclude_dirs"):].strip().split(",")
                current_word = new_words[-1]

                for file_name in self.all_dir_names:
                    if current_word and current_word in file_name:
                        yield Completion(file_name, start_position=-len(current_word))

            elif words[0] == "/lib":
                new_text = text[len("/lib"):]
                parser = CommandTextParser(new_text, words[0])
                parser.lib()
                current_word = parser.current_word()

                for command in parser.get_sub_commands():
                    if command.startswith(current_word):
                        yield Completion(command, start_position=-len(current_word))

                if parser.last_sub_command() in ["/add", "/remove", "/get"]:
                    for lib_name in memory.get("libs", {}).keys():
                        if lib_name.startswith(current_word):
                            yield Completion(
                                lib_name, start_position=-len(current_word)
                            )
            elif words[0] == "/mcp":
                new_text = text[len("/mcp"):]
                parser = CommandTextParser(new_text, words[0])
                parser.lib()
                current_word = parser.current_word()
                for command in parser.get_sub_commands():
                    if command.startswith(current_word):
                        yield Completion(command, start_position=-len(current_word))
            elif words[0] == "/models":
                new_text = text[len("/models"):]
                parser = CommandTextParser(new_text, words[0])
                parser.lib()
                current_word = parser.current_word()
                for command in parser.get_sub_commands():
                    if command.startswith(current_word):
                        yield Completion(command, start_position=-len(current_word))

            elif words[0] == "/coding":
                new_text = text[len("/coding"):]
                parser = CommandTextParser(new_text, words[0])
                parser.lib()
                current_word = parser.current_word()
                for command in parser.get_sub_commands():
                    if command.startswith(current_word):
                        yield Completion(command, start_position=-len(current_word))

            elif words[0] == "/conf":
                new_words = text[len("/conf"):].strip().split()
                is_at_space = text[-1] == " "
                last_word = new_words[-2] if len(new_words) > 1 else ""
                current_word = new_words[-1] if new_words else ""
                completions = []

                if is_at_space:
                    last_word = current_word
                    current_word = ""

                # /conf /drop [curor] or /conf /drop p[cursor]
                if last_word == "/drop":
                    completions = [
                        field_name
                        for field_name in memory["conf"].keys()
                        if field_name.startswith(current_word)
                    ]
                # /conf [curosr]
                elif not last_word and not current_word:
                    completions = [
                        "/drop"] if "/drop".startswith(current_word) else []
                    completions += [
                        field_name + ":"
                        for field_name in AutoCoderArgs.model_fields.keys()
                        if field_name.startswith(current_word)
                    ]
                # /conf p[cursor]
                elif not last_word and current_word:
                    completions = [
                        "/drop"] if "/drop".startswith(current_word) else []
                    completions += [
                        field_name + ":"
                        for field_name in AutoCoderArgs.model_fields.keys()
                        if field_name.startswith(current_word)
                    ]

                for completion in completions:
                    yield Completion(completion, start_position=-len(current_word))

            else:
                for command in self.commands:
                    if command.startswith(text):
                        yield Completion(command, start_position=-len(text))

        else:
            for command in self.commands:
                if command.startswith(text):
                    yield Completion(command, start_position=-len(text))

    def update_current_files(self, files):
        self.current_file_names = [f for f in files]

    def refresh_files(self):
        self.all_file_names = get_all_file_names_in_project()
        self.all_files = get_all_file_in_project()
        self.all_dir_names = get_all_dir_names_in_project()
        self.all_files_with_dot = get_all_file_in_project_with_dot()
        self.symbol_list = get_symbol_list()


completer = CommandCompleter(commands)


def save_memory():
    with open(os.path.join(base_persist_dir, "memory.json"), "w") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)
    load_memory()


def load_memory():
    global memory
    memory_path = os.path.join(base_persist_dir, "memory.json")
    if os.path.exists(memory_path):
        with open(memory_path, "r") as f:
            memory = json.load(f)
    completer.update_current_files(memory["current_files"]["files"])


def revert():
    last_yaml_file = get_last_yaml_file("actions")
    if last_yaml_file:
        file_path = os.path.join("actions", last_yaml_file)

        with redirect_stdout() as output:
            auto_coder_main(["revert", "--file", file_path])
        s = output.getvalue()
        print(s, flush=True)
        if "Successfully reverted changes" in s:
            print(
                "Reverted the last chat action successfully. Remove the yaml file {file_path}"
            )
            os.remove(file_path)
    else:
        print("No previous chat action found to revert.")


def add_files(args: List[str]):

    if "groups" not in memory["current_files"]:
        memory["current_files"]["groups"] = {}
    if "groups_info" not in memory["current_files"]:
        memory["current_files"]["groups_info"] = {}
    if "current_groups" not in memory["current_files"]:
        memory["current_files"]["current_groups"] = []
    groups = memory["current_files"]["groups"]
    groups_info = memory["current_files"]["groups_info"]

    console = Console()

    if not args:
        console.print(
            Panel(
                "Please provide arguments for the /add_files command.",
                title="Error",
                border_style="red",
            )
        )
        return

    if args[0] == "/refresh":
        completer.refresh_files()
        load_memory()
        console.print(
            Panel("Refreshed file list.",
                  title="Files Refreshed", border_style="green")
        )
        return

    if args[0] == "/group":
        if len(args) == 1 or (len(args) == 2 and args[1] == "list"):
            if not groups:
                console.print(
                    Panel("No groups defined.", title="Groups",
                          border_style="yellow")
                )
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
        elif len(args) >= 2 and args[1] == "/reset":
            memory["current_files"]["current_groups"] = []
            console.print(
                Panel(
                    "Active group names have been reset. If you want to clear the active files, you should use the command /remove_files /all.",
                    title="Groups Reset",
                    border_style="green",
                )
            )
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
            else:
                console.print(
                    Panel(
                        f"Group '{group_name}' not found.",
                        title="Error",
                        border_style="red",
                    )
                )
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
            elif not missing_groups:
                console.print(
                    Panel(
                        "No files in the specified groups.",
                        title="No Files Added",
                        border_style="yellow",
                    )
                )
    else:
        existing_files = memory["current_files"]["files"]
        matched_files = find_files_in_project(args)

        files_to_add = [f for f in matched_files if f not in existing_files]
        if files_to_add:
            memory["current_files"]["files"].extend(files_to_add)
            table = Table(
                title="Added Files",
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
        else:
            console.print(
                Panel(
                    "All specified files are already in the current session or no matches found.",
                    title="No Files Added",
                    border_style="yellow",
                )
            )

    completer.update_current_files(memory["current_files"]["files"])
    save_memory()


def remove_files(file_names: List[str]):
    console = Console()
    project_root = os.getcwd()

    if "/all" in file_names:
        memory["current_files"]["files"] = []
        memory["current_files"]["current_groups"] = []
        console.print(
            Panel("Removed all files.",
                  title="Files Removed", border_style="green")
        )
    else:
        removed_files = []
        for file in memory["current_files"]["files"]:
            if os.path.basename(file) in file_names:
                removed_files.append(file)
            elif file in file_names:
                removed_files.append(file)
        for file in removed_files:
            memory["current_files"]["files"].remove(file)

        if removed_files:
            table = Table(
                title="Removed Files", show_header=True, header_style="bold magenta"
            )
            table.add_column("File", style="green")
            for f in removed_files:
                table.add_row(os.path.relpath(f, project_root))
            console.print(Panel(table, border_style="green"))
        else:
            console.print(
                Panel(
                    "No files were removed.",
                    title="No Files Removed",
                    border_style="yellow",
                )
            )

    completer.update_current_files(memory["current_files"]["files"])
    save_memory()


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

    with open(os.path.join(execute_file), "w") as f:
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
        print("llm_friendly_packages directory not found.")
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
                                            with open(file_path, "r") as f:
                                                docs.append(f.read())

    return docs


def convert_yaml_to_config(yaml_file: str):
    from autocoder.auto_coder import AutoCoderArgs, load_include_files, Template

    args = AutoCoderArgs()
    with open(yaml_file, "r") as f:
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


def mcp(query: str):
    query = query.strip()
    mcp_server = get_mcp_server()

    # Handle remove command
    if query.startswith("/remove"):
        server_name = query.replace("/remove", "", 1).strip()
        response = mcp_server.send_request(
            McpRemoveRequest(server_name=server_name))
        if response.error:
            print(f"Error removing MCP server: {response.error}")
        else:
            print(f"Successfully removed MCP server: {response.result}")
        return

    # Handle list command
    if query.startswith("/list_running"):
        response = mcp_server.send_request(McpListRunningRequest())
        if response.error:
            print(f"Error listing running MCP servers: {response.error}")
        else:
            print("Running MCP servers:")
            print(response.result)
        return

    # Handle list command
    if query.startswith("/list"):
        response = mcp_server.send_request(McpListRequest())
        if response.error:
            print(f"Error listing builtin MCP servers: {response.error}")
        else:
            print("Available builtin MCP servers:")
            print(response.result)
        return

    # Handle refresh command
    if query.startswith("/refresh"):
        server_name = query.replace("/refresh", "", 1).strip()    
        response = mcp_server.send_request(McpRefreshRequest(name=server_name or None))
        if response.error:
            print(f"Error refreshing MCP servers: {response.error}")
        else:
            print("Successfully refreshed MCP servers")
        return

    # Handle add command
    if query.startswith("/add"):
        query = query.replace("/add", "", 1).strip()
        request = McpInstallRequest(server_name_or_config=query)
        response = mcp_server.send_request(request)

        if response.error:
            print(f"Error installing MCP server: {response.error}")
        else:
            print(f"Successfully installed MCP server: {response.result}")
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
    }
    for key, value in conf.items():
        converted_value = convert_config_value(key, value)
        if converted_value is not None:
            yaml_config[key] = converted_value

    temp_yaml = os.path.join("actions", f"{uuid.uuid4()}.yml")
    try:
        with open(temp_yaml, "w") as f:
            f.write(convert_yaml_config_to_str(yaml_config=yaml_config))
        args = convert_yaml_to_config(temp_yaml)
    finally:
        if os.path.exists(temp_yaml):
            os.remove(temp_yaml)

    mcp_server = get_mcp_server()
    response = mcp_server.send_request(
        McpRequest(
            query=query,
            model=args.inference_model or args.model
        )
    )
    console = Console()
    if response.error:
        console.print(Panel(
            f"Error from MCP server: {response.error}",
            title="Error",
            border_style="red"
        ))
    else:
        # Save conversation
        mcp_dir = os.path.join(".auto-coder", "mcp", "conversations")
        os.makedirs(mcp_dir, exist_ok=True)
        timestamp = str(int(time.time()))
        file_path = os.path.join(mcp_dir, f"{timestamp}.md")
        
        # Format response as markdown
        markdown_content = f"# MCP Response\n\n{response.result}"
        
        # Save to file
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)
            
        # Print with markdown formatting
        console.print(Panel(
            Markdown(markdown_content),            
            border_style="green"
        ))


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
    }
    for key, value in conf.items():
        converted_value = convert_config_value(key, value)
        if converted_value is not None:
            yaml_config[key] = converted_value

    temp_yaml = os.path.join("actions", f"{uuid.uuid4()}.yml")
    try:
        with open(temp_yaml, "w") as f:
            f.write(convert_yaml_config_to_str(yaml_config=yaml_config))
        args = convert_yaml_to_config(temp_yaml)
    finally:
        if os.path.exists(temp_yaml):
            os.remove(temp_yaml)

    llm = byzerllm.ByzerLLM.from_default_model(
        args.inference_model or args.model)

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

            if conf.get("enable_global_memory", "true") in ["true", "True",True]:
                yaml_config["urls"] += get_global_memory_file_paths()

            # 临时保存yaml文件，然后读取yaml文件，转换为args
            temp_yaml = os.path.join("actions", f"{uuid.uuid4()}.yml")
            try:
                with open(temp_yaml, "w") as f:
                    f.write(convert_yaml_config_to_str(
                        yaml_config=yaml_config))
                args = convert_yaml_to_config(temp_yaml)
            finally:
                if os.path.exists(temp_yaml):
                    os.remove(temp_yaml)

            llm = get_single_llm(args.code_model or args.model, product_mode)
            uncommitted_changes = git_utils.get_uncommitted_changes(".")
            commit_message = git_utils.generate_commit_message.with_llm(llm).run(
                uncommitted_changes
            )
            memory["conversation"].append(
                {"role": "user", "content": commit_message})
            yaml_config["query"] = commit_message
            yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)
            with open(os.path.join(execute_file), "w") as f:
                f.write(yaml_content)

            file_content = open(execute_file).read()
            md5 = hashlib.md5(file_content.encode("utf-8")).hexdigest()
            file_name = os.path.basename(execute_file)
            commit_result = git_utils.commit_changes(
                ".", f"auto_coder_{file_name}_{md5}"
            )
            git_utils.print_commit_info(commit_result=commit_result)
        except Exception as e:
            import traceback
            traceback.print_exc()            
            print(f"Failed to commit: {e}")
            if execute_file:
                os.remove(execute_file)


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

    memory["conversation"].append({"role": "user", "content": query})
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
        }

        yaml_config["context"] = ""

        for key, value in conf.items():
            converted_value = convert_config_value(key, value)
            if converted_value is not None:
                yaml_config[key] = converted_value
        
        yaml_config["urls"] = current_files + get_llm_friendly_package_docs(
            return_paths=True
        )

        if conf.get("enable_global_memory", "true") in ["true", "True",True]:
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

            if not os.path.exists(memory_file):
                error_message()
                return

            with open(memory_file, "r") as f:
                chat_history = json.load(f)

            if not chat_history["ask_conversation"]:
                error_message()
                return

            conversations = chat_history["ask_conversation"]

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
        with open(os.path.join(execute_file), "w") as f:
            f.write(yaml_content)

        def execute_chat():
            cmd = ["--file", execute_file]
            auto_coder_main(cmd)

        execute_chat()
    else:
        print("Failed to create new YAML file.")

    save_memory()
    completer.refresh_files()


@byzerllm.prompt()
def code_review(query: str) -> str:
    """
    对代码进行review，参考如下检查点。
    1. 有没有调用不符合方法，类的签名的调用
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
    }

    current_files = memory["current_files"]["files"] + get_llm_friendly_package_docs(
        return_paths=True
    )

    if conf.get("enable_global_memory", "true") in ["true", "True",True]:
        current_files += get_global_memory_file_paths()

    yaml_config["urls"] = current_files

    if "emb_model" in conf:
        yaml_config["emb_model"] = conf["emb_model"]

    is_new = "/new" in query
    if is_new:
        query = query.replace("/new", "", 1).strip()

    yaml_config["action"] = []    

    if "/mcp " in query:
        yaml_config["action"].append("mcp")
        query = query.replace("/mcp ", "", 1).strip()

    if "/rag " in query:
        yaml_config["action"].append("rag")
        query = query.replace("/rag ", "", 1).strip()

    if "/copy" in query:
        yaml_config["action"].append("copy")
        query = query.replace("/copy", "", 1).strip()   

    if "/save" in query:
        yaml_config["action"].append("save")
        query = query.replace("/save", "", 1).strip()        

    is_review = query.strip().startswith("/review")
    if is_review:
        query = query.replace("/review", "", 1).strip()
        if "prompt_review" in conf:
            query = format_str_jinja2(conf["prompt_review"], query=query)
        else:
            query = code_review.prompt(query)

    is_no_context = query.strip().startswith("/no_context")
    if is_no_context:
        query = query.replace("/no_context", "", 1).strip()

    for key, value in conf.items():
        converted_value = convert_config_value(key, value)
        if converted_value is not None:
            yaml_config[key] = converted_value

    query = Image.convert_image_paths_from(query)

    yaml_config["query"] = query

    yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)

    execute_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(os.path.join(execute_file), "w") as f:
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


def summon(query: str):
    conf = memory.get("conf", {})
    current_files = memory["current_files"]["files"]

    file_contents = []
    for file in current_files:
        if os.path.exists(file):
            try:
                with open(file, "r") as f:
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

    with open(os.path.join(execute_file), "w") as f:
        f.write(yaml_content)

    def execute_summon():
        auto_coder_main(["agent", "auto_tool", "--file", execute_file])

    try:
        execute_summon()
    finally:
        os.remove(execute_file)


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

    with open(os.path.join(execute_file), "w") as f:
        f.write(yaml_content)

    def execute_design():
        auto_coder_main(["agent", "designer", "--file", execute_file])

    try:
        execute_design()
    finally:
        os.remove(execute_file)


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

    with open(os.path.join(execute_file), "w") as f:
        f.write(yaml_content)

    def execute_voice2text_command():
        auto_coder_main(["agent", "voice2text", "--file", execute_file])

    try:
        execute_voice2text_command()
        with open(os.path.join(".auto-coder", "exchange.txt"), "r") as f:
            return f.read()
    finally:
        os.remove(execute_file)


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

    with open(os.path.join(execute_file), "w") as f:
        f.write(yaml_content)

    try:
        auto_coder_main(["agent", "generate_command", "--file", execute_file])
        with open(os.path.join(".auto-coder", "exchange.txt"), "r") as f:
            shell_script = f.read()
        return shell_script
    finally:
        os.remove(execute_file)

def manage_models(params, query: str):
    """    
    Handle /models subcommands:
      /models /list - List all models (default + custom)
      /models /add <name> <api_key> - Add model with simplified params
      /models /add_model name=xxx base_url=xxx ... - Add model with custom params
      /models /remove <name> - Remove model by name
    """
    print("manage_models", params, query)
    console = Console()
    
    if params.product_mode != "lite":
        console.print(f"[red]{get_message('models_lite_only')}[/red]")
        return
        
    models_data = models.load_models()
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
    
    if "/remove" in query:
        subcmd = "/remove"
        query = query.replace("/remove", "", 1).strip()
    if not subcmd:
        console.print(get_message("models_usage"))
        return    

    if subcmd == "/list":                    
        if models_data:
            table = Table(title=get_message("models_title"))
            table.add_column("Name", style="cyan")
            table.add_column("Model Type", style="green")
            table.add_column("Model Name", style="magenta")             
            table.add_column("Description", style="white")
            for m in models_data:
                # Check if api_key_path exists and file exists
                api_key_path = m.get("api_key_path", "")
                name = m.get("name", "")
                if api_key_path:
                    api_key_file = os.path.expanduser(f"~/.auto-coder/keys/{api_key_path}")
                    if os.path.exists(api_key_file):
                        name = f"{name}*"
                
                table.add_row(
                    name,
                    m.get("model_type", ""),
                    m.get("model_name", ""),                    
                    m.get("description", "")
                )
            console.print(table)
        else:
            console.print(f"[yellow]{get_message('models_no_models')}[/yellow]")

    elif subcmd == "/add":
        # Support both simplified and legacy formats
        args = query.strip().split(" ")        
        if len(args) == 2:
            # Simplified: /models /add <name> <api_key>
            name, api_key = args[0], args[1]            
            result = models.update_model_with_api_key(name, api_key)
            if result:
                console.print(f"[green]{get_message('models_added').format(name=name)}[/green]")
            else:
                console.print(f"[red]{get_message('models_add_failed').format(name=name)}[/red]")
        else:
            console.print(f"[red]{get_message('models_add_usage')}[/red]")

    elif subcmd == "/add_model":
        # Parse key=value pairs: /models /add_model name=abc base_url=http://xx ...       
        # Collect key=value pairs
        kv_pairs = shlex.split(query)
        data_dict = {}
        for pair in kv_pairs:
            if '=' not in pair:
                console.print(f"[red]Invalid parameter: {pair}, should be key=value[/red]")
                continue
            k, v = pair.split('=', 1)
            data_dict[k.strip()] = v.strip()

        # Name is required
        if "name" not in data_dict:
            console.print(f"[red]{get_message('models_add_model_name_required')}[/red]")
            return

        # Check duplication
        if any(m["name"] == data_dict["name"] for m in models_data):
            console.print(f"[yellow]{get_message('models_add_model_exists').format(name=data_dict['name'])}[/yellow]")
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
        models.save_models(models_data)
        console.print(f"[green]{get_message('models_add_model_success').format(name=data_dict['name'])}[/green]")

    elif subcmd == "/remove":
        args = query.strip().split(" ")
        if len(args) < 1:
            console.print(f"[red]{get_message('models_add_usage')}[/red]")
            return
        name = args[0]
        filtered_models = [m for m in models_data if m["name"] != name]
        if len(filtered_models) == len(models_data):
            console.print(f"[yellow]{get_message('models_add_model_remove').format(name=name)}[/yellow]")
            return
        models.save_models(filtered_models)
        console.print(f"[green]{get_message('models_add_model_removed').format(name=name)}[/green]")

    else:
        console.print(f"[yellow]{get_message('models_unknown_subcmd').format(subcmd=subcmd)}[/yellow]")

def exclude_dirs(dir_names: List[str]):
    new_dirs = dir_names
    existing_dirs = memory.get("exclude_dirs", [])
    dirs_to_add = [d for d in new_dirs if d not in existing_dirs]
    if dirs_to_add:
        existing_dirs.extend(dirs_to_add)
        if "exclude_dirs" not in memory:
            memory["exclude_dirs"] = existing_dirs
        print(f"Added exclude dirs: {dirs_to_add}")
    else:
        print("All specified dirs are already in the exclude list.")
    save_memory()
    completer.refresh_files()


def index_build():
    conf = memory.get("conf", {})
    yaml_config = {
        "include_file": ["./base/base.yml"],
    }

    for key, value in conf.items():
        converted_value = convert_config_value(key, value)
        if converted_value is not None:
            yaml_config[key] = converted_value

    yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)
    yaml_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(yaml_file, "w") as f:
        f.write(yaml_content)
    try:
        with redirect_stdout() as output:
            auto_coder_main(["index", "--file", yaml_file])
        print(output.getvalue(), flush=True)
        completer.refresh_files()
    finally:
        os.remove(yaml_file)


def index_query(query: str):
    conf = memory.get("conf", {})
    yaml_config = {
        "include_file": ["./base/base.yml"],
    }

    for key, value in conf.items():
        converted_value = convert_config_value(key, value)
        if converted_value is not None:
            yaml_config[key] = converted_value

    yaml_config["query"] = query

    yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)
    yaml_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(yaml_file, "w") as f:
        f.write(yaml_content)
    try:
        with redirect_stdout() as output:
            auto_coder_main(["index-query", "--file", yaml_file])
        print(output.getvalue(), flush=True)
    finally:
        os.remove(yaml_file)


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


def execute_shell_command(command: str):
    console = Console()
    try:
        # Use shell=True to support shell mode
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
            shell=True,
        )

        output = []
        with Live(console=console, refresh_per_second=4) as live:
            while True:
                output_line = process.stdout.readline()
                error_line = process.stderr.readline()

                if output_line:
                    output.append(output_line.strip())
                    live.update(
                        Panel(
                            Text("\n".join(output[-20:])),
                            title="Shell Output",
                            border_style="green",
                        )
                    )
                if error_line:
                    output.append(f"ERROR: {error_line.strip()}")
                    live.update(
                        Panel(
                            Text("\n".join(output[-20:])),
                            title="Shell Output",
                            border_style="red",
                        )
                    )

                if (
                    output_line == ""
                    and error_line == ""
                    and process.poll() is not None
                ):
                    break

        if process.returncode != 0:
            console.print(
                f"[bold red]Command failed with return code {process.returncode}[/bold red]"
            )
        else:
            console.print(
                "[bold green]Command completed successfully[/bold green]")

    except FileNotFoundError:
        console.print(
            f"[bold red]Command not found:[/bold red] [yellow]{command}[/yellow]"
        )
    except subprocess.SubprocessError as e:
        console.print(
            f"[bold red]Error executing command:[/bold red] [yellow]{str(e)}[/yellow]"
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
            "Please specify a subcommand: /add, /remove, /list, /set-proxy, /refresh, or /get"
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


def main():
    ARGS = parse_arguments()
    
    if ARGS.lite:
        ARGS.product_mode = "lite"
    
    if ARGS.pro:
        ARGS.product_mode = "pro" 

    if not ARGS.quick:
        initialize_system(ARGS)    
    
    load_memory()
    
    configure(f"product_mode:{ARGS.product_mode}")

    MODES = {
        "normal": "normal",
        "auto_detect": "nature language auto detect",
        "voice_input": "voice input",
    }

    kb = KeyBindings()

    @kb.add("c-c")
    def _(event):
        event.app.exit()

    @kb.add("tab")
    def _(event):
        b = event.current_buffer
        if b.complete_state:
            b.complete_next()
        else:
            b.start_completion(select_first=False)

    @kb.add("c-g")
    def _(event):
        transcription = voice_input()
        if transcription:
            event.app.current_buffer.insert_text(transcription)

    @kb.add("c-k")
    def _(event):
        if "mode" not in memory:
            memory["mode"] = "normal"

        current_mode = memory["mode"]
        if current_mode == "normal":
            memory["mode"] = "auto_detect"
        elif current_mode == "auto_detect":
            memory["mode"] = "voice_input"
        else:  # voice_input
            memory["mode"] = "normal"

        event.app.invalidate()

    @kb.add("c-n")
    def _(event):
        if "human_as_model" not in memory["conf"]:
            memory["conf"]["human_as_model"] = "false"

        current_status = memory["conf"]["human_as_model"]
        new_status = "true" if current_status == "false" else "false"
        configure(f"human_as_model:{new_status}", skip_print=True)
        event.app.invalidate()

    def get_bottom_toolbar():
        if "mode" not in memory:
            memory["mode"] = "normal"
        mode = memory["mode"]
        human_as_model = memory["conf"].get("human_as_model", "false")
        if mode not in MODES:
            mode = "normal"
        return f" Mode: {MODES[mode]} (ctl+k) | Human as Model: {human_as_model} (ctl+n or /conf human_as_model:true/false)"

    session = PromptSession(
        history=InMemoryHistory(),
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=False,
        completer=completer,
        complete_while_typing=True,
        key_bindings=kb,
        bottom_toolbar=get_bottom_toolbar,
    )
    print(
        f"""
    \033[1;32m  ____ _           _          _         _               ____          _           
    / ___| |__   __ _| |_       / \  _   _| |_ ___        / ___|___   __| | ___ _ __ 
    | |   | '_ \ / _` | __|____ / _ \| | | | __/ _ \ _____| |   / _ \ / _` |/ _ \ '__|
    | |___| | | | (_| | ||_____/ ___ \ |_| | || (_) |_____| |__| (_) | (_| |  __/ |   
    \____|_| |_|\__,_|\__|   /_/   \_\__,_|\__\___/       \____\___/ \__,_|\___|_| 
                                                                        v{__version__}
    \033[0m"""
    )
    print("\033[1;34mType /help to see available commands.\033[0m\n")
    show_help()

    style = Style.from_dict(
        {
            "username": "#884444",
            "at": "#00aa00",
            "colon": "#0000aa",
            "pound": "#00aa00",
            "host": "#00ffff bg:#444400",
        }
    )

    new_prompt = ""

    while True:
        try:
            prompt_message = [
                ("class:username", "coding"),
                ("class:at", "@"),
                ("class:host", "auto-coder.chat"),
                ("class:colon", ":"),
                ("class:path", "~"),
                ("class:dollar", "$ "),
            ]

            if new_prompt:
                user_input = session.prompt(
                    FormattedText(prompt_message), default=new_prompt, style=style
                )
            else:
                user_input = session.prompt(
                    FormattedText(prompt_message), style=style)
            new_prompt = ""

            if "mode" not in memory:
                memory["mode"] = "normal"

            if (
                memory["mode"] == "auto_detect"
                and user_input
                and not user_input.startswith("/")
            ):
                shell_script = generate_shell_command(user_input)
                if confirm("Do you want to execute this script?"):
                    execute_shell_command(shell_script)
                else:
                    continue
            elif memory["mode"] == "voice_input" and not user_input.startswith("/"):
                text = voice_input()
                new_prompt = "/coding " + text

            elif user_input.startswith("/voice_input"):
                text = voice_input()
                new_prompt = "/coding " + text

            elif user_input.startswith("/add_files"):
                args = user_input[len("/add_files"):].strip().split()
                add_files(args)
            elif user_input.startswith("/remove_files"):
                file_names = user_input[len(
                    "/remove_files"):].strip().split(",")
                remove_files(file_names)
            elif user_input.startswith("/index/query"):
                query = user_input[len("/index/query"):].strip()
                index_query(query)

            elif user_input.startswith("/index/build"):
                index_build()

            elif user_input.startswith("/list_files"):
                list_files()

            elif user_input.startswith("/models"):
                query = user_input[len("/models"):].strip()
                if not query:
                    print("Please enter your query.")
                else:
                    manage_models(ARGS,query) 

            elif user_input.startswith("/mode"):
                conf = user_input[len("/mode"):].strip()
                if not conf:
                    print(memory["mode"])
                else:
                    memory["mode"] = conf                    

            elif user_input.startswith("/conf"):
                conf = user_input[len("/conf"):].strip()
                if not conf:
                    print(memory["conf"])
                else:
                    configure(conf)
            elif user_input.startswith("/revert"):
                revert()
            elif user_input.startswith("/commit"):
                query = user_input[len("/commit"):].strip()
                commit(query)
            elif user_input.startswith("/help"):
                show_help()
            elif user_input.startswith("/exclude_dirs"):
                dir_names = user_input[len(
                    "/exclude_dirs"):].strip().split(",")
                exclude_dirs(dir_names)
            elif user_input.startswith("/ask"):
                query = user_input[len("/ask"):].strip()
                if not query:
                    print("Please enter your question.")
                else:
                    ask(query)

            elif user_input.startswith("/exit"):
                raise EOFError()

            elif user_input.startswith("/coding"):
                query = user_input[len("/coding"):].strip()
                if not query:
                    print("\033[91mPlease enter your request.\033[0m")
                    continue
                coding(query)
            elif user_input.startswith("/chat"):
                query = user_input[len("/chat"):].strip()
                if not query:
                    print("\033[91mPlease enter your request.\033[0m")
                else:
                    chat(query)

            elif user_input.startswith("/design"):
                query = user_input[len("/design"):].strip()
                if not query:
                    print("\033[91mPlease enter your design request.\033[0m")
                else:
                    design(query)

            elif user_input.startswith("/summon"):
                query = user_input[len("/summon"):].strip()
                if not query:
                    print("\033[91mPlease enter your request.\033[0m")
                else:
                    summon(query)

            elif user_input.startswith("/lib"):
                args = user_input[len("/lib"):].strip().split()
                lib_command(args)

            elif user_input.startswith("/mcp"):
                query = user_input[len("/mcp"):].strip()
                if not query:
                    print("Please enter your query.")
                else:
                    mcp(query)

            elif user_input.startswith("/debug"):
                code = user_input[len("/debug"):].strip()
                try:
                    result = eval(code)
                    print(f"Debug result: {result}")
                except Exception as e:
                    print(f"Debug error: {str(e)}")            

            # elif user_input.startswith("/shell"):
            else:
                command = user_input
                if user_input.startswith("/shell"):
                    command = user_input[len("/shell"):].strip()
                if not command:
                    print("Please enter a shell command to execute.")
                else:
                    execute_shell_command(command)

        except KeyboardInterrupt:
            continue
        except EOFError:
            try:
                save_memory()
                try:
                    if get_mcp_server():
                        get_mcp_server().stop()
                except Exception as e:
                    pass
            except Exception as e:
                print(
                    f"\033[91mAn error occurred while saving memory:\033[0m \033[93m{type(e).__name__}\033[0m - {str(e)}"
                )
            print("\n\033[93mExiting Chat Auto Coder...\033[0m")
            break
        except Exception as e:
            print(
                f"\033[91mAn error occurred:\033[0m \033[93m{type(e).__name__}\033[0m - {str(e)}"
            )
            if ARGS and ARGS.debug:
                import traceback

                traceback.print_exc()


if __name__ == "__main__":
    main()
