import argparse
import os
import yaml
import json
import sys
import io
import uuid
from contextlib import contextmanager
from typing import List, Dict, Any
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter, Completer, Completion
from autocoder.common import AutoCoderArgs
from autocoder.auto_coder import main as auto_coder_main
from autocoder.command_args import parse_args
from autocoder.utils import get_last_yaml_file


memory = {"conversation": [], "current_files": {"files": []}, "conf": {}}

base_persist_dir = os.path.join(".auto-coder", "plugins", "chat-auto-coder")

exclude_dirs = [".git", "node_modules", "dist", "build","__pycache__"]

commands = [
    "/add_files",
    "/remove_files",
    "/list_files",
    "/conf", 
    "/chat",
    "/revert",
    "/index/query",
    "/revert",
    "/help",
    "/exit",
]


def get_all_file_names_in_project() -> List[str]:
    project_root = os.getcwd()
    file_names = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        file_names.extend(files)
    return file_names

def get_all_file_in_project() -> List[str]:
    project_root = os.getcwd()
    file_names = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:            
            file_names.append(os.path.join(root, file))
    return file_names


def find_files_in_project(file_names: List[str]) -> List[str]:
    project_root = os.getcwd()
    matched_files = []
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file in file_names:
                matched_files.append(os.path.join(root, file))
            elif os.path.join(root, file) in file_names:
                matched_files.append(os.path.join(root, file))
    return matched_files


@contextmanager
def redirect_stdout():
    original_stdout = sys.stdout
    sys.stdout = f = io.StringIO()
    try:
        yield f.getvalue()
    finally:
        sys.stdout = original_stdout


def configure(conf: str):
    key, value = conf.split(":", 1)
    key = key.strip()
    value = value.strip()
    memory["conf"][key] = value
    save_memory()
    print(f"Set {key} to {value}")


def show_help():
    print("\033[1mSupported commands:\033[0m")
    print()
    print("  \033[94mCommands\033[0m - \033[93mDescription\033[0m")
    print(
        "  \033[94m/add_files\033[0m \033[93m<file1>,<file2> ...\033[0m - \033[92mAdd files to the current session\033[0m"
    )
    print(
        "  \033[94m/remove_files\033[0m \033[93m<file1>,<file2> ...\033[0m - \033[92mRemove files from the current session\033[0m"
    )
    print(
        "  \033[94m/chat\033[0m \033[93m<query>\033[0m - \033[92mChat with the AI about the current files\033[0m"
    )
    print(
        "  \033[94m/revert\033[0m - \033[92mRevert commits from last chat\033[0m"
    )
    print(
        "  \033[94m/index/query\033[0m \033[93m<args>\033[0m - \033[92mQuery the project index\033[0m"
    )
    print(
        "  \033[94m/list_files\033[0m - \033[92mList all files in the current session\033[0m"
    )
    print("  \033[94m/help\033[0m - \033[92mShow this help message\033[0m")
    print("  \033[94m/exit\033[0m - \033[92mExit the program\033[0m")
    print()


# word_completer = WordCompleter(commands)


class CommandCompleter(Completer):
    def __init__(self, commands):
        self.commands = commands
        self.all_file_names = get_all_file_names_in_project()
        self.all_files = get_all_file_in_project()
        self.current_file_names = []

    def get_completions(self, document, complete_event):
        text = document.text_before_cursor
        words = text.split()

        if len(words) > 0:
            if words[0] == "/add_files":
                new_words = text[len("/add_files") :].strip().split(",")
                current_word = new_words[-1]
                for file_name in self.all_file_names:
                    if file_name.startswith(current_word):
                        yield Completion(file_name, start_position=-len(current_word))
                
                for file_name in self.all_files:        
                    if current_word and current_word in file_name:                        
                        yield Completion(file_name, start_position=-len(current_word))

            elif words[0] == "/remove_files":
                new_words = text[len("/remove_files") :].strip().split(",")
                current_word = new_words[-1]

                for file_name in self.all_file_names:
                    if file_name.startswith(current_word):
                        yield Completion(file_name, start_position=-len(current_word))
            
                for file_name in self.all_files:
                    if current_word in file_name:
                        yield Completion(file_name, start_position=-len(current_word))        
            else:
                for command in self.commands:
                    if command.startswith(text):
                        yield Completion(command, start_position=-len(text))

        else:
            for command in self.commands:
                if command.startswith(text):
                    yield Completion(command, start_position=-len(text))

    def update_current_files(self, files):
        self.current_file_names = [os.path.basename(f) for f in files]


completer = CommandCompleter(commands)


def save_memory():
    with open(os.path.join(base_persist_dir, "memory.json"), "w") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


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
        auto_coder_main(["revert", "--file", file_path])
        print("Reverted the last chat action successfully. Remove the yaml file {file_path}")
        os.remove(file_path)
    else:
        print("No previous chat action found to revert.")    


def add_files(file_names: List[str]):
    new_files = find_files_in_project(file_names)
    existing_files = memory["current_files"]["files"]
    files_to_add = [f for f in new_files if f not in existing_files]
    if files_to_add:
        memory["current_files"]["files"].extend(files_to_add)
        print(f"Added files: {[os.path.basename(f) for f in files_to_add]}")
    else:
        print("All specified files are already in the current session.")
    completer.update_current_files(memory["current_files"]["files"])
    save_memory()


def remove_files(file_names: List[str]):
    removed_files = []
    for file in memory["current_files"]["files"]:
        if os.path.basename(file) in file_names:
            removed_files.append(file)
        elif file in file_names:
            removed_files.append(file)
    for file in removed_files:
        memory["current_files"]["files"].remove(file)
    completer.update_current_files(memory["current_files"]["files"])
    save_memory()


def chat(query: str):
    memory["conversation"].append({"role": "user", "content": query})
    conf = memory.get("conf", {})

    current_files = memory["current_files"]["files"]
    files_list = "\n".join([f"- {file}" for file in current_files])

    def prepare_chat_yaml():
        auto_coder_main(["next", "chat_action"])

    prepare_chat_yaml()

    latest_yaml_file = get_last_yaml_file("actions")

    if latest_yaml_file:
        yaml_config = {
            "include_file": ["./base/base.yml"],
            "auto_merge": conf.get("auto_merge", "editblock"),
            "human_as_model": conf.get("human_as_model", "false"),
            "skip_build_index": conf.get("skip_build_index", "true"),
            "skip_confirm": conf.get("skip_confirm", "true"),
        }

        for key, value in conf.items():
            if key not in [
                "auto_merge",
                "human_as_model",
                "skip_build_index",
                "skip_confirm",
            ]:
                yaml_config[key] = value

        yaml_config["urls"] = current_files
        yaml_config["query"] = query

        yaml_content = yaml.safe_dump(
            yaml_config, encoding="utf-8", allow_unicode=True, default_flow_style=False
        ).decode("utf-8")
        execute_file = os.path.join("actions", latest_yaml_file)
        with open(os.path.join(execute_file), "w") as f:
            f.write(yaml_content)

        def execute_chat():
            auto_coder_main(["--file", execute_file])

        execute_chat()
    else:
        print("Failed to create new YAML file.")

    save_memory()


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
        print(output)

    finally:
        os.remove(yaml_file)


def main():
    if not os.path.exists(".auto-coder"):
        print(
            "Please run this command in the root directory of your project which have been inited by auto-coder."
        )
        exit(1)

    if not os.path.exists(base_persist_dir):
        os.makedirs(base_persist_dir, exist_ok=True)

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
        """
\033[1;32m  ____ _           _          _         _               ____          _           
  / ___| |__   __ _| |_       / \  _   _| |_ ___        / ___|___   __| | ___ _ __ 
 | |   | '_ \ / _` | __|____ / _ \| | | | __/ _ \ _____| |   / _ \ / _` |/ _ \ '__|
 | |___| | | | (_| | ||_____/ ___ \ |_| | || (_) |_____| |__| (_) | (_| |  __/ |   
  \____|_| |_|\__,_|\__|   /_/   \_\__,_|\__\___/       \____\___/ \__,_|\___|_| 
\033[0m"""
    )
    print("\033[1;34mType /help to see available commands.\033[0m\n")
    show_help()

    while True:
        try:
            prompt_message = [
                ("class:username", "chat-auto-coder"),
                ("class:at", "@"),
                ("class:host", "localhost"),
                ("class:colon", ":"),
                ("class:path", "~"),
                ("class:dollar", "$ "),
            ]
            user_input = session.prompt(FormattedText(prompt_message))

            if user_input.startswith("/add_files"):
                file_names = user_input[len("/add_files") :].strip().split(",")
                add_files(file_names)
            elif user_input.startswith("/remove_files"):
                file_names = user_input[len("/remove_files") :].strip().split(",")
                remove_files(file_names)
                print(f"Removed files: {file_names}")
            elif user_input.startswith("/index/query"):
                query = user_input[len("/index/query") :].strip()
                index_query(query)
            elif user_input.startswith("/list_files"):
                print("Current files:")
                for file in memory["current_files"]["files"]:
                    print(file)
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
            elif user_input.startswith("/exit"):
                raise KeyboardInterrupt
            else:
                if user_input.startswith("/") and not user_input.startswith("/chat"):
                    print(
                        "Invalid command. Please type /help to see the list of supported commands."
                    )
                    continue
                if not user_input.startswith("/chat"):
                    query = user_input.strip()
                else:
                    query = user_input[len("/chat") :].strip()
                if not query:
                    print("Please enter your request.")
                else:
                    chat(query)

        except KeyboardInterrupt:
            print("Exiting...")
            break
        except Exception as e:
            print(f"An error occurred: {e}")


if __name__ == "__main__":
    main()
