import argparse
import os
import yaml
import json
from typing import List, Dict, Any
from prompt_toolkit import PromptSession
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.formatted_text import FormattedText
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.completion import WordCompleter

from autocoder.common import AutoCoderArgs
from autocoder.auto_coder import main as auto_coder_main
from autocoder.command_args import parse_args
from autocoder.utils import get_last_yaml_file
import os

memory = {
    "conversation": [],
    "current_files": {
        "files": []
    }
}

base_persist_dir = os.path.join(".auto-coder","plugins","chat-auto-coder")

def save_memory():
    with open(os.path.join(base_persist_dir,"memory.json"), "w") as f:
        json.dump(memory, f, indent=2,ensure_ascii=False)

def load_memory():
    global memory
    memory_path = os.path.join(base_persist_dir,"memory.json")
    if os.path.exists(memory_path):
        with open(memory_path, "r") as f:
            memory = json.load(f)

def find_files_in_project(file_names: List[str]) -> List[str]:
    project_root = os.getcwd()
    matched_files = []
    exclude_dirs = ['.git', 'node_modules', 'dist']
    for root, dirs, files in os.walk(project_root):
        dirs[:] = [d for d in dirs if d not in exclude_dirs]
        for file in files:
            if file in file_names:
                matched_files.append(os.path.join(root, file))
    return matched_files

def add_files(file_names: List[str]):
    new_files = find_files_in_project(file_names)
    memory["current_files"]["files"].extend(new_files)
    save_memory()

def remove_files(file_names: List[str]):
    removed_files = []
    for file in memory["current_files"]["files"]:
        if os.path.basename(file) in file_names:
            removed_files.append(file)
    for file in removed_files:
        memory["current_files"]["files"].remove(file)
    save_memory()

def chat(query: str):
    memory["conversation"].append({"role": "user", "content": query})
    
    current_files = memory["current_files"]["files"]
    files_list = "\n".join([f"- {file}" for file in current_files])
    
    yaml_content = f"""
include_file:
  - ./base/base.yml

auto_merge: editblock 
human_as_model: true
skip_build_index: true
skip_confirm: true

urls:
{files_list}

query: |
  {query}
"""
    # latest_yaml_file = get_last_yaml_file("actions")
    with open("./actions/temp_action.yml", "w") as f:
        f.write(yaml_content)
    
    auto_coder_main(["--file", "./actions/temp_action.yml"])

    os.remove("./actions/temp_action.yml")
    
    save_memory()

def index_query(args: List[str]):
    auto_coder_main(["index", "query"] + args)

def main():   
    if not os.path.exists(".auto-coder"):
        print("Please run this command in the root directory of your project which have been inited by auto-coder.")
        exit(1)

    if not os.path.exists(base_persist_dir):
        os.makedirs(base_persist_dir, exist_ok=True)

    load_memory()

    commands = WordCompleter(["/add_files", "/remove_files", "/chat", "/index/query", "/list_files"])

    session = PromptSession(history=InMemoryHistory(),
                            auto_suggest=AutoSuggestFromHistory(),
                            enable_history_search=True,
                            completer=commands,
                            complete_while_typing=True)

    kb = KeyBindings()

    @kb.add('c-c')
    def _(event):
        event.app.exit()

    while True:
        try:
            prompt_message = [
                ('class:username', 'chat-auto-coder'),
                ('class:at', '@'),
                ('class:host', 'localhost'),
                ('class:colon', ':'),
                ('class:path', '~'),
                ('class:dollar', '$ '),
            ]
            user_input = session.prompt(FormattedText(prompt_message), key_bindings=kb)
            
            if user_input.startswith("/add_files"):
                file_names = user_input.split(" ")[1:]
                add_files(file_names)
                print(f"Added files: {file_names}")
            elif user_input.startswith("/remove_files"):
                file_names = user_input.split(" ")[1:]
                remove_files(file_names)
                print(f"Removed files: {file_names}")
            elif user_input.startswith("/index/query"):
                args = user_input.split(" ")[1:]
                index_query(args)
            elif user_input.startswith("/list_files"):
                print("Current files:")
                for file in memory["current_files"]["files"]:
                    print(file)
            else:
                query = user_input.lstrip("/chat").strip()
                if not query:
                    print("Please enter your request.")
                else:
                    chat(query)

        except KeyboardInterrupt:
            print("Exiting...")
            break
        except Exception as e:
            pass

if __name__ == "__main__":
    main()