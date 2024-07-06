from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import yaml
import json
import uuid
import glob
from autocoder.common import AutoCoderArgs
from autocoder.auto_coder import main as auto_coder_main
from autocoder.utils import get_last_yaml_file
from autocoder.utils.request_queue import request_queue
import subprocess

app = FastAPI()

# 全局变量,模拟 chat_auto_coder.py 中的 memory
memory = {
    "conversation": [],
    "current_files": {"files": []},
    "conf": {},
    "exclude_dirs": [],
}

base_persist_dir = os.path.join(".auto-coder", "plugins", "chat-auto-coder")
defaut_exclude_dirs = [".git", "node_modules", "dist", "build", "__pycache__"]

# 辅助函数
def save_memory():
    with open(os.path.join(base_persist_dir, "memory.json"), "w") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)

def load_memory():
    global memory
    memory_path = os.path.join(base_persist_dir, "memory.json")
    if os.path.exists(memory_path):
        with open(memory_path, "r") as f:
            memory = json.load(f)

# 加载内存
load_memory()

# 定义请求模型
class FileRequest(BaseModel):
    files: List[str]

class QueryRequest(BaseModel):
    query: str

class ConfigRequest(BaseModel):
    key: str
    value: str

# API 路由
@app.post("/add_files")
async def add_files(request: FileRequest):
    project_root = os.getcwd()
    existing_files = memory["current_files"]["files"]
    matched_files = find_files_in_project(request.files)

    files_to_add = [f for f in matched_files if f not in existing_files]
    if files_to_add:
        memory["current_files"]["files"].extend(files_to_add)
        save_memory()
        return {"message": f"Added files: {[os.path.relpath(f, project_root) for f in files_to_add]}"}
    else:
        return {"message": "All specified files are already in the current session or no matches found."}

@app.post("/remove_files")
async def remove_files(request: FileRequest):
    if "/all" in request.files:
        memory["current_files"]["files"] = []
        save_memory()
        return {"message": "Removed all files."}
    else:
        removed_files = []
        for file in memory["current_files"]["files"]:
            if os.path.basename(file) in request.files or file in request.files:
                removed_files.append(file)
        for file in removed_files:
            memory["current_files"]["files"].remove(file)
        save_memory()
        return {"message": f"Removed files: {[os.path.basename(f) for f in removed_files]}"}

@app.get("/list_files")
async def list_files():
    return {"files": memory["current_files"]["files"]}

@app.post("/conf")
async def configure(request: ConfigRequest):
    memory["conf"][request.key] = request.value
    save_memory()
    return {"message": f"Set {request.key} to {request.value}"}

@app.delete("/conf/{key}")
async def delete_config(key: str):
    if key in memory["conf"]:
        del memory["conf"][key]
        save_memory()
        return {"message": f"Deleted configuration: {key}"}
    else:
        raise HTTPException(status_code=404, detail=f"Configuration not found: {key}")

@app.post("/coding")
async def coding(request: QueryRequest, background_tasks: BackgroundTasks):
    memory["conversation"].append({"role": "user", "content": request.query})
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
            "urls": current_files,
            "query": request.query
        }

        for key, value in conf.items():
            converted_value = convert_config_value(key, value)
            if converted_value is not None:
                yaml_config[key] = converted_value

        yaml_content = yaml.safe_dump(
            yaml_config,
            encoding="utf-8",
            allow_unicode=True,
            default_flow_style=False,
            default_style=None,
        ).decode("utf-8")
        execute_file = os.path.join("actions", latest_yaml_file)
        with open(execute_file, "w") as f:
            f.write(yaml_content)

        background_tasks.add_task(auto_coder_main, ["--file", execute_file])
        return {"message": "Coding task started in background"}
    else:
        raise HTTPException(status_code=500, detail="Failed to create new YAML file.")

@app.post("/chat")
async def chat(request: QueryRequest, background_tasks: BackgroundTasks):
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
        "query": request.query,
        "context": json.dumps({"file_content": all_file_content}, ensure_ascii=False)
    }

    if "emb_model" in conf:
        yaml_config["emb_model"] = conf["emb_model"]

    yaml_content = yaml.safe_dump(
        yaml_config, encoding="utf-8", allow_unicode=True, default_flow_style=False
    ).decode("utf-8")

    execute_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(execute_file, "w") as f:
        f.write(yaml_content)

    request_id = str(uuid.uuid4())

    def process_chat():
        try:
            auto_coder_main(["agent", "chat", "--file", execute_file, "--request_id", request_id])            
        finally:
            os.remove(execute_file)

    background_tasks.add_task(process_chat)
    return {"request_id": request_id}

@app.post("/ask")
async def ask(request: QueryRequest):
    conf = memory.get("conf", {})
    yaml_config = {
        "include_file": ["./base/base.yml"],
        "query": request.query
    }

    if "project_type" in conf:
        yaml_config["project_type"] = conf["project_type"]

    for model_type in ["model", "index_model", "vl_model", "code_model"]:
        if model_type in conf:
            yaml_config[model_type] = conf[model_type]

    yaml_content = yaml.safe_dump(
        yaml_config, encoding="utf-8", allow_unicode=True, default_flow_style=False
    ).decode("utf-8")

    execute_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

    with open(execute_file, "w") as f:
        f.write(yaml_content)

    try:
        result = auto_coder_main(["agent", "project_reader", "--file", execute_file])
        return {"result": result}
    finally:
        os.remove(execute_file)

@app.post("/revert")
async def revert():
    last_yaml_file = get_last_yaml_file("actions")
    if last_yaml_file:
        file_path = os.path.join("actions", last_yaml_file)
        result = auto_coder_main(["revert", "--file", file_path])
        if "Successfully reverted changes" in result:
            os.remove(file_path)
            return {"message": "Reverted the last chat action successfully"}
        else:
            return {"message": result}
    else:
        return {"message": "No previous chat action found to revert."}

@app.post("/index/build")
async def index_build():
    yaml_file = os.path.join("actions", f"{uuid.uuid4()}.yml")
    yaml_content = """
include_file:
  - ./base/base.yml  
"""
    with open(yaml_file, "w") as f:
        f.write(yaml_content)
    try:
        result = auto_coder_main(["index", "--file", yaml_file])
        return {"result": result}
    finally:
        os.remove(yaml_file)

@app.post("/index/query")
async def index_query(request: QueryRequest):
    yaml_file = os.path.join("actions", f"{uuid.uuid4()}.yml")
    yaml_content = f"""
include_file:
  - ./base/base.yml  
query: |
  {request.query}
"""
    with open(yaml_file, "w") as f:
        f.write(yaml_content)
    try:
        result = auto_coder_main(["index-query", "--file", yaml_file])
        return {"result": result}
    finally:
        os.remove(yaml_file)

@app.post("/exclude_dirs")
async def exclude_dirs(request: FileRequest):
    new_dirs = request.files
    existing_dirs = memory.get("exclude_dirs", [])
    dirs_to_add = [d for d in new_dirs if d not in existing_dirs]
    if dirs_to_add:
        existing_dirs.extend(dirs_to_add)
        memory["exclude_dirs"] = existing_dirs
        save_memory()
        return {"message": f"Added exclude dirs: {dirs_to_add}"}
    else:
        return {"message": "All specified dirs are already in the exclude list."}

@app.post("/shell")
async def execute_shell(request: QueryRequest):
    command = request.query
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            return {"output": result.stdout}
        else:
            return {"error": result.stderr}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/result/{request_id}")
async def get_result(request_id: str):
    result = request_queue.get_request(request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found or not ready yet")
    v = {"result": result}    
    return v

# 辅助函数
def find_files_in_project(patterns: List[str]) -> List[str]:
    project_root = os.getcwd()
    matched_files = []
    final_exclude_dirs = defaut_exclude_dirs + memory.get("exclude_dirs", [])

    for pattern in patterns:
        if "*" in pattern or "?" in pattern:
            for file_path in glob.glob(pattern, recursive=True):
                if os.path.isfile(file_path):
                    abs_path = os.path.abspath(file_path)
                    if not any(exclude_dir in abs_path.split(os.sep) for exclude_dir in final_exclude_dirs):
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
        return None

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)