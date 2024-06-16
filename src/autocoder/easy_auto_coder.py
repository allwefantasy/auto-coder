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

memory = {
    "conversation": [],
    "current_files": {
        "files": []
    }
}

def save_memory():
    with open("memory.json", "w") as f:
        json.dump(memory, f, indent=2)

def load_memory():
    global memory
    if os.path.exists("memory.json"):
        with open("memory.json", "r") as f:
            memory = json.load(f)

def find_files_in_project(file_names: List[str]) -> List[str]:
    project_root = os.getcwd()
    matched_files = []
    for root, dirs, files in os.walk(project_root):
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
    
    yaml_content = f"""
include_file:
  - ./base/base.yml

auto_merge: editblock
human_as_model: false   

query: |
  {query}
"""
    with open("temp_action.yml", "w") as f:
        f.write(yaml_content)

    args = parse_args(["--file", "temp_action.yml"])
    auto_coder_main(args)

    os.remove("temp_action.yml")
    
    save_memory()

def index_query(args: List[str]):
    auto_coder_main(parse_args(["index", "query"] + args))

def main():
    load_memory()

    commands = WordCompleter(["/add_files", "/remove_files", "/chat", "/index/query"])

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
                ('class:username', 'auto-coder'),
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
            else:  
                query = user_input.lstrip("/chat").strip()
                chat(query)

        except KeyboardInterrupt:
            print("Exiting...")
            break

if __name__ == "__main__":
    main()