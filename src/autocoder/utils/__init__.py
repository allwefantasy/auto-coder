import os
from typing import Optional
import subprocess
import shutil
from loguru import logger
from autocoder.common.action_yml_file_manager import ActionYmlFileManager

def get_last_yaml_file(actions_dir:str)->Optional[str]:
    """
    获取最新的 YAML 文件
    
    Args:
        actions_dir: actions 目录路径
        
    Returns:
        Optional[str]: 最新的 YAML 文件名，如果没有则返回 None
    """
    # 兼容已有代码，创建临时 ActionYmlFileManager
    action_manager = ActionYmlFileManager(os.path.dirname(actions_dir))
    return action_manager.get_latest_action_file()

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