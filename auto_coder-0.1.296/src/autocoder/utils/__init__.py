import os
from typing import Optional
import subprocess
import shutil
from loguru import logger

def get_last_yaml_file(actions_dir:str)->Optional[str]:
    action_files = [
            f for f in os.listdir(actions_dir) if f[:3].isdigit() and "_" in f and f.endswith(".yml")
        ]

    def get_old_seq(name):
        return int(name.split("_")[0])

    sorted_action_files = sorted(action_files, key=get_old_seq)
    return sorted_action_files[-1] if sorted_action_files else None

def open_yaml_file_in_editor(new_file:str):
    try:
        if os.environ.get("TERMINAL_EMULATOR") == "JetBrains-JediTerm":
            subprocess.run(["idea", new_file])
        else:
            if shutil.which("code"):
                subprocess.run(["code", "-r", new_file])
            elif shutil.which("idea"):
                subprocess.run(["idea", new_file])
    except Exception as e:
        logger.info(
            f"Error opening editor, you can manually open the file: {new_file}"
        )