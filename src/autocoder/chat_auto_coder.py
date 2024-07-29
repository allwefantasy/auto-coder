import os
import yaml
import json
import sys
import io
import uuid
import glob
import time
from contextlib import contextmanager
from typing import List, Dict, Any
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from autocoder.common import AutoCoderArgs
from pydantic import Field, BaseModel
from autocoder.version import __version__
from autocoder.auto_coder import main as auto_coder_main
from autocoder.command_args import parse_args
from autocoder.utils import get_last_yaml_file
import platform
import subprocess
import shlex
from rich.console import Console
from rich.panel import Panel
from rich.live import Live
from rich.text import Text
from rich.table import Table


def parse_arguments():
    import argparse

    parser = argparse.ArgumentParser(description="Chat Auto Coder")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    return parser.parse_args()


ARGS = None

if platform.system() == "Windows":
    from colorama import init

    init()

from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import radiolist_dialog
from prompt_toolkit.formatted_text import HTML

memory = {
    "conversation": [],
    "current_files": {"files": [], "groups": {}},
    "conf": {},
    "exclude_dirs": [],
}

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
    "/revert",
    "/index/query",
    "/index/build",
    "/exclude_dirs",
    "/help",
    "/shell",
    "/exit",
    "/summon",
]

add_files_subcommands = ["/group"]


def initialize_system():
    print("\n\033[1;34m🚀 Initializing system...\033[0m")

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
        if not os.path.exists(".auto-coder"):
            print_status(
                "The current directory is not initialized as an auto-coder project.",
                "warning",
            )
            init_choice = (
                input("  Do you want to initialize the project now? (y/n): ")
                .strip()
                .lower()
            )
            if init_choice == "y":
                try:
                    subprocess.run(
                        ["auto-coder", "init", "--source_dir", "."], check=True
                    )
                    print_status("Project initialized successfully.", "success")
                except subprocess.CalledProcessError:
                    print_status("Failed to initialize the project.", "error")
                    print_status(
                        "Please try manually: auto-coder init --source_dir .", "warning"
                    )
                    exit(1)
            else:
                print_status("Exiting without initialization.", "warning")
                exit(1)

        if not os.path.exists(base_persist_dir):
            os.makedirs(base_persist_dir, exist_ok=True)
            print_status(f"Created directory: {base_persist_dir}", "success")

        print_status("Project initialization completed.", "success")

    # Check if Ray is running
    print_status("Checking Ray status...", "")
    ray_status = subprocess.run(["ray", "status"], capture_output=True, text=True)
    if ray_status.returncode != 0:
        print_status("Ray is not running. Starting Ray...", "warning")
        try:
            subprocess.run(["ray", "start", "--head"], check=True)
            print_status("Ray started successfully.", "success")
        except subprocess.CalledProcessError:
            print_status("Failed to start Ray. Please start it manually.", "error")
            return
    else:
        print_status("Ray is already running.", "success")

    # Check if deepseek_chat model is available
    print_status("Checking deepseek_chat model availability...", "")
    try:
        result = subprocess.run(
            ["easy-byzerllm", "chat", "deepseek_chat", "你好"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            print_status("deepseek_chat model is available.", "success")
            init_project()
            print_status("Initialization completed successfully.", "success")
            return
    except subprocess.TimeoutExpired:
        print_status(
            "Command timed out. deepseek_chat model might not be available.", "error"
        )
    except subprocess.CalledProcessError:
        print_status("Error occurred while checking deepseek_chat model.", "error")

    # If deepseek_chat is not available, prompt user to choose a provider
    print_status(
        "deepseek_chat model is not available. Please choose a provider:", "warning"
    )
    choice = radiolist_dialog(
        title="Provider Selection",
        text="Select a provider for deepseek_chat model:",
        values=[
            ("1", "硅基流动(https://siliconflow.cn)"),
            ("2", "Deepseek官方(https://www.deepseek.com/)"),
        ],
    ).run()

    if choice is None:
        print_status("No provider selected. Exiting initialization.", "error")
        return

    api_key = prompt(HTML("<b>Please enter your API key: </b>"))

    if choice == "1":
        print_status("Deploying deepseek_chat model using 硅基流动...", "")
        deploy_cmd = [
            "easy-byzerllm",
            "deploy",
            "deepseek-ai/deepseek-v2-chat",
            "--token",
            api_key,
            "--alias",
            "deepseek_chat",
        ]
    else:
        print_status("Deploying deepseek_chat model using Deepseek官方...", "")
        deploy_cmd = [
            "easy-byzerllm",
            "deploy",
            "deepseek-chat",
            "--token",
            api_key,
            "--alias",
            "deepseek_chat",
        ]

    try:
        subprocess.run(deploy_cmd, check=True)
        print_status("Deployment completed.", "success")
    except subprocess.CalledProcessError:
        print_status("Deployment failed. Please try again or deploy manually.", "error")
        return

    # Validate the deployment
    print_status("Validating the deployment...", "")
    try:
        validation_result = subprocess.run(
            ["easy-byzerllm", "chat", "deepseek_chat", "你好"],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        print_status(
            "Validation successful. deepseek_chat model is now available.", "success"
        )
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError):
        print_status(
            "Validation failed. The model might not be deployed correctly.", "error"
        )
        print_status("Please try to start the model manually using:", "warning")
        print_status("easy-byzerllm chat deepseek_chat 你好", "")

    print_status("Initialization completed.", "success")
    init_project()


def convert_yaml_config_to_str(yaml_config):
    yaml_content = yaml.safe_dump(
        yaml_config,
        allow_unicode=True,
        default_flow_style=False,
        default_style=None,
    )
    return yaml_content


def get_all_file_names_in_project() -> List[str]:
    project_root = os.getcwd()
    file_names = []
    final_exclude_dirs = defaut_exclude_dirs + memory.get("exclude_dirs", [])
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in final_exclude_dirs]
        file_names.extend(files)
    return file_names


def get_all_file_in_project() -> List[str]:
    project_root = os.getcwd()
    file_names = []
    final_exclude_dirs = defaut_exclude_dirs + memory.get("exclude_dirs", [])
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in final_exclude_dirs]
        for file in files:
            file_names.append(os.path.join(root, file))
    return file_names


def get_all_dir_names_in_project() -> List[str]:
    project_root = os.getcwd()
    dir_names = []
    final_exclude_dirs = defaut_exclude_dirs + memory.get("exclude_dirs", [])
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in final_exclude_dirs]
        for dir in dirs:
            dir_names.append(dir)
    return dir_names


def find_files_in_project(patterns: List[str]) -> List[str]:
    project_root = os.getcwd()
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
            for root, dirs, files in os.walk(project_root):
                dirs[:] = [d for d in dirs if d not in final_exclude_dirs]
                if pattern in files:
                    matched_files.append(os.path.join(root, pattern))
                    is_added = True
                else:
                    for file in files:
                        if pattern in os.path.join(root, file):
                            matched_files.append(os.path.join(root, file))
                            is_added = True
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


def configure(conf: str):
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
        print(f"\033[92mSet {key} to {value}\033[0m")


def show_help():
    print("\033[1mSupported commands:\033[0m")
    print()
    print("  \033[94mCommands\033[0m - \033[93mDescription\033[0m")
    print(
        "  \033[94m/add_files\033[0m \033[93m<file1> <file2> ...\033[0m - \033[92mAdd files to the current session\033[0m"
    )
    print(
        "  \033[94m/remove_files\033[0m \033[93m<file1>,<file2> ...\033[0m - \033[92mRemove files from the current session\033[0m"
    )
    print(
        "  \033[94m/chat\033[0m \033[93m<query>\033[0m - \033[92mChat with the AI about the current active files to get insights\033[0m"
    )
    print(
        "  \033[94m/coding\033[0m \033[93m<query>\033[0m - \033[92mRequest the AI to modify code based on requirements\033[0m"
    )
    print(
        "  \033[94m/ask\033[0m \033[93m<query>\033[0m - \033[92mAsk the AI any questions or get insights about the current project, without modifying code\033[0m"
    )
    print(
        "  \033[94m/summon\033[0m \033[93m<query>\033[0m - \033[92mSummon the AI to perform complex tasks using the auto_tool agent\033[0m"
    )
    print(
        "  \033[94m/revert\033[0m - \033[92mRevert commits from last coding chat\033[0m"
    )
    print(
        "  \033[94m/conf\033[0m \033[93m<key>:<value>\033[0m  - \033[92mSet configuration. Use /conf project_type:<type> to set project type for indexing\033[0m"
    )
    print(
        "  \033[94m/index/query\033[0m \033[93m<args>\033[0m - \033[92mQuery the project index\033[0m"
    )
    print(
        "  \033[94m/index/build\033[0m - \033[92mTrigger building the project index\033[0m"
    )
    print(
        "  \033[94m/list_files\033[0m - \033[92mList all active files in the current session\033[0m"
    )
    print("  \033[94m/help\033[0m - \033[92mShow this help message\033[0m")
    print(
        "  \033[94m/exclude_dirs\033[0m \033[93m<dir1>,<dir2> ...\033[0m - \033[92mAdd directories to exclude from project\033[0m"
    )
    print(
        "  \033[94m/shell\033[0m \033[93m<command>\033[0m - \033[92mExecute a shell command\033[0m"
    )
    print("  \033[94m/exit\033[0m - \033[92mExit the program\033[0m")
    print()


# word_completer = WordCompleter(commands)


class CommandCompleter(Completer):
    def __init__(self, commands):
        self.commands = commands
        self.all_file_names = get_all_file_names_in_project()
        self.all_files = get_all_file_in_project()
        self.all_dir_names = get_all_dir_names_in_project()
        self.current_file_names = []

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()

        if len(words) > 0:
            if words[0] == "/add_files":
                if len(words) >= 2:
                    if words[1] == "/group":
                        return
                new_words = text[len("/add_files") :].strip().split()
                current_word = new_words[-1] if new_words else ""
                for file_name in self.all_file_names:
                    if file_name.startswith(current_word):
                        yield Completion(file_name, start_position=-len(current_word))
                for file_name in self.all_files:
                    if current_word and current_word in file_name:
                        yield Completion(file_name, start_position=-len(current_word))

            elif words[0] == "/remove_files":
                new_words = text[len("/remove_files") :].strip().split(",")

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
                new_words = text[len("/exclude_dirs") :].strip().split(",")
                current_word = new_words[-1]

                for file_name in self.all_dir_names:
                    if current_word and current_word in file_name:
                        yield Completion(file_name, start_position=-len(current_word))

            elif words[0] == "/conf":
                new_words = text[len("/conf") :].strip().split()
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
                    completions = ["/drop"] if "/drop".startswith(current_word) else []
                    completions += [
                        field_name + ":"
                        for field_name in AutoCoderArgs.model_fields.keys()
                        if field_name.startswith(current_word)
                    ]
                # /conf p[cursor]
                elif not last_word and current_word:
                    completions = ["/drop"] if "/drop".startswith(current_word) else []
                    completions += [
                        field_name + ":"
                        for field_name in AutoCoderArgs.model_fields.keys()
                        if field_name.startswith(current_word)
                    ]
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
    project_root = os.getcwd()
    if "groups" not in memory["current_files"]:
        memory["current_files"]["groups"] = {}
    groups = memory["current_files"]["groups"]

    console = Console()

    if args and args[0] == "/group":
        if len(args) == 1 or (len(args) == 2 and args[1] == "list"):
            if not groups:
                console.print(
                    Panel("No groups defined.", title="Groups", border_style="yellow")
                )
            else:
                table = Table(
                    title="Defined Groups",
                    show_header=True,
                    header_style="bold magenta",
                )
                table.add_column("Group Name", style="cyan", no_wrap=True)
                table.add_column("Files", style="green")
                for group_name, files in groups.items():
                    table.add_row(
                        group_name,
                        "\n".join([os.path.relpath(f, project_root) for f in files]),
                    )
                console.print(Panel(table, border_style="blue"))
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
                console.print(
                    Panel(
                        f"Merged files from groups: {', '.join(group_names)}",
                        title="Files Merged",
                        border_style="green",
                    )
                )
                table = Table(
                    title="Current Files", show_header=True, header_style="bold magenta"
                )
                table.add_column("File", style="green")
                for f in memory["current_files"]["files"]:
                    table.add_row(os.path.relpath(f, project_root))
                console.print(Panel(table, border_style="blue"))
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
                title="Added Files", show_header=True, header_style="bold magenta"
            )
            table.add_column("File", style="green")
            for f in files_to_add:
                table.add_row(os.path.relpath(f, project_root))
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
        console.print(
            Panel("Removed all files.", title="Files Removed", border_style="green")
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


def coding(query: str):
    console = Console()
    is_apply = query.strip().startswith("/apply")
    if is_apply:
        query = query.replace("/apply", "", 1).strip()

    memory["conversation"].append({"role": "user", "content": query})
    conf = memory.get("conf", {})

    current_files = memory["current_files"]["files"]

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
        }

        for key, value in conf.items():
            converted_value = convert_config_value(key, value)
            if converted_value is not None:
                yaml_config[key] = converted_value

        yaml_config["urls"] = current_files
        yaml_config["query"] = query

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

            yaml_config["context"] = (
                f"下面是我们的历史对话，参考我们的历史对话从而更好的理解需求和修改代码。\n\n"
            )
            for conv in conversations:
                if conv["role"] == "user":
                    yaml_config["context"] += f"用户: {conv['content']}\n"
                elif conv["role"] == "assistant":
                    yaml_config["context"] += f"你: {conv['content']}\n"

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


def chat(query: str):
    conf = memory.get("conf", {})
    current_files = memory["current_files"]["files"]

    file_contents = []
    for file in current_files:
        if os.path.exists(file):
            with open(file, "r") as f:
                content = f.read()
                s = f"##File: {file}\n{content}\n\n"
                file_contents.append(s)

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

    is_new = query.strip().startswith("/new")
    if is_new:
        query = query.replace("/new", "", 1).strip()

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
            with open(file, "r") as f:
                content = f.read()
                s = f"##File: {file}\n{content}\n\n"
                file_contents.append(s)

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
    yaml_file = os.path.join("actions", f"{uuid.uuid4()}.yml")
    yaml_content = f"""
include_file:
  - ./base/base.yml  
"""
    with open(yaml_file, "w") as f:
        f.write(yaml_content)
    try:
        with redirect_stdout() as output:
            auto_coder_main(["index", "--file", yaml_file])
        print(output.getvalue(), flush=True)

    finally:
        os.remove(yaml_file)


def index_query(query: str):
    yaml_file = os.path.join("actions", f"{uuid.uuid4()}.yml")
    yaml_content = f"""
include_file:
  - ./base/base.yml  
query: |
  {query}
"""
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


def main():
    ARGS = parse_arguments()

    initialize_system()

    load_memory()

    kb = KeyBindings()

    @kb.add("c-c")
    def _(event):
        event.app.exit()

    @kb.add("tab")
    def _(event):
        event.current_buffer.complete_next()

    session = PromptSession(
        history=InMemoryHistory(),
        auto_suggest=AutoSuggestFromHistory(),
        enable_history_search=False,
        completer=completer,
        complete_while_typing=True,
        key_bindings=kb,
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
            user_input = session.prompt(FormattedText(prompt_message))

            if user_input.startswith("/add_files"):
                args = user_input[len("/add_files") :].strip().split()
                add_files(args)
            elif user_input.startswith("/remove_files"):
                file_names = user_input[len("/remove_files") :].strip().split(",")
                remove_files(file_names)
            elif user_input.startswith("/index/query"):
                query = user_input[len("/index/query") :].strip()
                index_query(query)

            elif user_input.startswith("/index/build"):
                index_build()

            elif user_input.startswith("/list_files"):
                list_files()
            elif user_input.startswith("/conf"):
                conf = user_input[len("/conf") :].strip()
                if not conf:
                    print(memory["conf"])
                else:
                    configure(conf)
            elif user_input.startswith("/revert"):
                revert()
            elif user_input.startswith("/help"):
                show_help()
            elif user_input.startswith("/exclude_dirs"):
                dir_names = user_input[len("/exclude_dirs") :].strip().split(",")
                exclude_dirs(dir_names)
            elif user_input.startswith("/ask"):
                query = user_input[len("/ask") :].strip()
                if not query:
                    print("Please enter your question.")
                else:
                    ask(query)

            elif user_input.startswith("/exit"):
                raise KeyboardInterrupt
            elif user_input.startswith("/coding"):
                query = user_input[len("/coding") :].strip()
                if not query:
                    print("\033[91mPlease enter your request.\033[0m")
                    continue
                coding(query)
            elif user_input.startswith("/chat"):
                query = user_input[len("/chat") :].strip()
                if not query:
                    print("\033[91mPlease enter your request.\033[0m")
                else:
                    chat(query)

            elif user_input.startswith("/summon"):
                query = user_input[len("/summon") :].strip()
                if not query:
                    print("\033[91mPlease enter your request.\033[0m")
                else:
                    summon(query)

            # elif user_input.startswith("/shell"):
            else:
                command = user_input
                if user_input.startswith("/shell"):
                    command = user_input[len("/shell") :].strip()
                if not command:
                    print("Please enter a shell command to execute.")
                else:
                    console = Console()
                    try:
                        # Use shlex.split() to properly handle quoted arguments
                        command_args = shlex.split(command)
                        process = subprocess.Popen(
                            command_args,
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            text=True,
                            bufsize=1,
                            universal_newlines=True,
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
                                "[bold green]Command completed successfully[/bold green]"
                            )

                    except FileNotFoundError:
                        console.print(
                            f"[bold red]Command not found:[/bold red] [yellow]{command}[/yellow]"
                        )
                    except subprocess.SubprocessError as e:
                        console.print(
                            f"[bold red]Error executing command:[/bold red] [yellow]{str(e)}[/yellow]"
                        )
            # else:
            #     print(
            #         "\033[91mInvalid command.\033[0m Please type \033[93m/help\033[0m to see the list of supported commands."
            #     )

        except KeyboardInterrupt:
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
