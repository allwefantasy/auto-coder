from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.requests import Request
from pydantic import BaseModel
from typing import List, Dict, Optional
import os
import yaml
import json
import uuid
import glob
import argparse
from typing import List
from autocoder.common import AutoCoderArgs
from autocoder.auto_coder import main as auto_coder_main
from autocoder.utils import get_last_yaml_file
from pydantic import BaseModel
from autocoder.utils.request_queue import (
    request_queue,
    RequestValue,
    StreamValue,
    DefaultValue,
    RequestOption,
)
from autocoder.utils.queue_communicate import (
    queue_communicate,
    CommunicateEvent,
    CommunicateEventType,
)
import subprocess
from byzerllm.utils.langutil import asyncfy_with_semaphore
from contextlib import contextmanager
import sys
import io
from autocoder.utils.log_capture import LogCapture

# If support dotenv, use it
if os.path.exists(".env"):
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

def convert_yaml_config_to_str(yaml_config):
    yaml_content = yaml.safe_dump(
        yaml_config,
        allow_unicode=True,
        default_flow_style=False,
        default_style=None,
    )
    return yaml_content

app = FastAPI()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@contextmanager
def redirect_stdout():
    original_stdout = sys.stdout
    sys.stdout = f = io.StringIO()
    try:
        yield f
    finally:
        sys.stdout = original_stdout


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
    os.makedirs(base_persist_dir, exist_ok=True)
    with open(os.path.join(base_persist_dir, "memory.json"), "w") as f:
        json.dump(memory, f, indent=2, ensure_ascii=False)


def load_memory():
    global memory
    memory_path = os.path.join(base_persist_dir, "memory.json")
    if os.path.exists(memory_path):
        with open(memory_path, "r",encoding="utf-8") as f:
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


class FileQueryRequest(BaseModel):
    query: str


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
        return {
            "message": f"Added files: {[os.path.relpath(f, project_root) for f in files_to_add]}"
        }
    else:
        return {
            "message": "All specified files are already in the current session or no matches found."
        }


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
        return {
            "message": f"Removed files: {[os.path.basename(f) for f in removed_files]}"
        }


@app.get("/list_files")
@app.post("/list_files")
async def list_files():
    return {"files": memory["current_files"]["files"]}


@app.get("/extra/conf/list")
@app.post("/extra/conf/list")
async def list_all_config_options():
    return {"options": list(AutoCoderArgs.model_fields.keys())}


@app.get("/conf/list")
@app.post("/conf/list")
async def list_user_config():
    return {"config": memory["conf"]}


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
    # memory["conversation"].append({"role": "user", "content": request.query})
    conf = memory.get("conf", {})
    current_files = memory["current_files"]["files"]
    request_id = str(uuid.uuid4())

    def process():
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
                "silence": conf.get("silence", "false") == "true",
                "urls": current_files,
                "query": request.query,
            }

            for key, value in conf.items():
                converted_value = convert_config_value(key, value)
                if converted_value is not None:
                    yaml_config[key] = converted_value

            yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)
            execute_file = os.path.join("actions", latest_yaml_file)
            with open(execute_file, "w", encoding="utf-8") as f:
                f.write(yaml_content)

            try:
                auto_coder_main(["--file", execute_file, "--request_id", request_id])
            finally:
                try:
                    os.remove(execute_file)
                except FileNotFoundError:
                    pass
                _ = queue_communicate.send_event(
                    request_id=request_id,
                    event=CommunicateEvent(
                        event_type=CommunicateEventType.CODE_END.value, data=""
                    ),
                )

    _ = queue_communicate.send_event(
        request_id=request_id,
        event=CommunicateEvent(
            event_type=CommunicateEventType.CODE_START.value, data=request.query
        ),
    )
    background_tasks.add_task(process)
    return {"request_id": request_id}


@app.post("/chat")
async def chat(request: QueryRequest, background_tasks: BackgroundTasks):
    conf = memory.get("conf", {})
    current_files = memory["current_files"]["files"]

    request_id = str(uuid.uuid4())

    def process_chat():
        execute_file = os.path.join("actions", f"{uuid.uuid4()}.yml")
        try:
            file_contents = []
            for file in current_files:
                if os.path.exists(file):
                    with open(file, "r",encoding="utf-8") as f:
                        content = f.read()
                        s = f"##File: {file}\n{content}\n\n"
                        file_contents.append(s)

            all_file_content = "".join(file_contents)

            yaml_config = {
                "include_file": ["./base/base.yml"],
                "query": request.query,
                "context": json.dumps(
                    {"file_content": all_file_content}, ensure_ascii=False
                ),
            }

            if "emb_model" in conf:
                yaml_config["emb_model"] = conf["emb_model"]

            yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)

            with open(execute_file, "w",encoding="utf-8") as f:
                f.write(yaml_content)
            auto_coder_main(
                ["agent", "chat", "--file", execute_file, "--request_id", request_id]
            )
        finally:
            os.remove(execute_file)

    request_queue.add_request(
        request_id,
        RequestValue(value=StreamValue(value=[""]), status=RequestOption.RUNNING),
    )
    background_tasks.add_task(process_chat)

    return {"request_id": request_id}


@app.post("/ask")
async def ask(request: QueryRequest, background_tasks: BackgroundTasks):
    conf = memory.get("conf", {})
    request_id = str(uuid.uuid4())

    def process():
        yaml_config = {"include_file": ["./base/base.yml"], "query": request.query}

        if "project_type" in conf:
            yaml_config["project_type"] = conf["project_type"]

        for model_type in ["model", "index_model", "vl_model", "code_model"]:
            if model_type in conf:
                yaml_config[model_type] = conf[model_type]

        yaml_content = convert_yaml_config_to_str(yaml_config=yaml_config)

        execute_file = os.path.join("actions", f"{uuid.uuid4()}.yml")

        with open(execute_file, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        try:
            auto_coder_main(
                [
                    "agent",
                    "project_reader",
                    "--file",
                    execute_file,
                    "--request_id",
                    request_id,
                ]
            )
        finally:
            os.remove(execute_file)

    request_queue.add_request(
        request_id,
        RequestValue(value=DefaultValue(value=""), status=RequestOption.RUNNING),
    )
    background_tasks.add_task(process)

    return {"request_id": request_id}


@app.post("/revert")
async def revert():
    last_yaml_file = get_last_yaml_file("actions")
    if last_yaml_file:
        file_path = os.path.join("actions", last_yaml_file)
        with redirect_stdout() as output:
            auto_coder_main(["revert", "--file", file_path])
        result = output.getvalue()

        if "Successfully reverted changes" in result:
            os.remove(file_path)
            return {"message": "Reverted the last chat action successfully"}
        else:
            return {"message": result}
    else:
        return {"message": "No previous chat action found to revert."}


@app.post("/index/build")
async def index_build(background_tasks: BackgroundTasks):
    request_id = str(uuid.uuid4())

    def run():
        yaml_file = os.path.join("actions", f"{uuid.uuid4()}.yml")
        yaml_content = """
include_file:
  - ./base/base.yml  
"""
        with open(yaml_file, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        log_capture = LogCapture(request_id=request_id)
        with log_capture.capture() as log_queue:
            try:
                auto_coder_main(
                    ["index", "--file", yaml_file, "--request_id", request_id]
                )
            finally:
                os.remove(yaml_file)

    background_tasks.add_task(run)
    return {"request_id": request_id}


@app.post("/index/query")
async def index_query(request: QueryRequest, background_tasks: BackgroundTasks):
    request_id = str(uuid.uuid4())

    def run():
        yaml_file = os.path.join("actions", f"{uuid.uuid4()}.yml")
        yaml_content = f"""
    include_file:
    - ./base/base.yml  
    query: |
    {request.query}
    """
        with open(yaml_file, "w", encoding="utf-8") as f:
            f.write(yaml_content)
        try:
            auto_coder_main(
                ["index-query", "--file", yaml_file, "--request_id", request_id]
            )
        finally:
            os.remove(yaml_file)

    request_queue.add_request(
        request_id,
        RequestValue(value=DefaultValue(value=""), status=RequestOption.RUNNING),
    )
    background_tasks.add_task(run)
    v: RequestValue = await asyncfy_with_semaphore(request_queue.get_request_block)(
        request_id, timeout=60
    )
    return {"message": v.value.value}


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


@app.get("/extra/result/{request_id}")
async def get_result(request_id: str):
    result = request_queue.get_request(request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Result not found or not ready yet")

    v = {"result": result.value, "status": result.status.value}
    return v


@app.post("/extra/files")
async def find_files(request: FileQueryRequest):
    query = request.query
    matched_files = find_files_in_project([query])
    return {"files": matched_files}


@app.post("/test/event/send")
async def test_event(request: Request, background_tasks: BackgroundTasks):
    request_json = await request.json()
    request_id = request_json.get("request_id")
    if not request_id:
        raise HTTPException(status_code=400, detail="request_id is required")

    def send_event():
        v = queue_communicate.send_event(
            request_id,
            CommunicateEvent(
                event_type=CommunicateEventType.CODE_MERGE.value,
                data="xxxxx",
            ),
        )
        with open("test_event_send.log", "a") as f:
            f.write(f"Sender {request_id} received response: {v}\n")

    background_tasks.add_task(send_event)
    return {"message": ""}


class EventGetRequest(BaseModel):
    request_id: str


class EventResponseRequest(BaseModel):
    request_id: str
    event: Dict[str, str]
    response: str


@app.post("/extra/logs")
async def logs(request: EventGetRequest):
    v = LogCapture.get_log_capture(request.request_id)
    logs = v.get_captured_logs() if v else []
    return {"logs": logs}


@app.post("/extra/event/get")
async def extra_event_get(request: EventGetRequest):
    request_id = request.request_id
    if not request_id:
        raise HTTPException(status_code=400, detail="request_id is required")

    v = queue_communicate.get_event(request_id)
    return v


@app.post("/extra/event/response")
async def extra_event_response(request: EventResponseRequest):
    request_id = request.request_id
    if not request_id:
        raise HTTPException(status_code=400, detail="request_id is required")

    event = CommunicateEvent(**request.event)
    response = request.response
    queue_communicate.response_event(request_id, event, response=response)
    return {"message": "success"}


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
        return None


class ServerArgs(BaseModel):
    host: str = None
    port: int = 8000
    uvicorn_log_level: str = "info"
    allow_credentials: bool = False
    allowed_origins: List[str] = ["*"]
    allowed_methods: List[str] = ["*"]
    allowed_headers: List[str] = ["*"]
    api_key: Optional[str] = None
    served_model_name: Optional[str] = None
    prompt_template: Optional[str] = None
    response_role: Optional[str] = "assistant"
    ssl_keyfile: Optional[str] = None
    ssl_certfile: Optional[str] = None


def parse_args() -> ServerArgs:
    parser = argparse.ArgumentParser(description="Auto Coder Server")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to bind the server to"
    )
    parser.add_argument(
        "--port", type=int, default=8000, help="Port to bind the server to"
    )
    parser.add_argument(
        "--uvicorn-log-level", type=str, default="info", help="Uvicorn log level"
    )
    parser.add_argument(
        "--allow-credentials", action="store_true", help="Allow credentials"
    )
    parser.add_argument(
        "--allowed-origins", nargs="+", default=["*"], help="Allowed origins"
    )
    parser.add_argument(
        "--allowed-methods", nargs="+", default=["*"], help="Allowed methods"
    )
    parser.add_argument(
        "--allowed-headers", nargs="+", default=["*"], help="Allowed headers"
    )
    parser.add_argument("--api-key", type=str, help="API key for authentication")
    parser.add_argument(
        "--served-model-name", type=str, help="Name of the served model"
    )
    parser.add_argument("--prompt-template", type=str, help="Prompt template")
    parser.add_argument(
        "--response-role", type=str, default="assistant", help="Response role"
    )
    parser.add_argument("--ssl-keyfile", type=str, help="SSL key file")
    parser.add_argument("--ssl-certfile", type=str, help="SSL certificate file")

    args = parser.parse_args()
    print(vars(args))
    return ServerArgs(**vars(args))


def main():
    import uvicorn

    args = parse_args()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=args.allowed_origins,
        allow_credentials=args.allow_credentials,
        allow_methods=args.allowed_methods,
        allow_headers=args.allowed_headers,
    )

    if args.api_key:

        @app.middleware("http")
        async def authentication(request: Request, call_next):
            if request.headers.get("Authorization") != "Bearer " + args.api_key:
                return JSONResponse(content={"error": "Unauthorized"}, status_code=401)
            return await call_next(request)

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level=args.uvicorn_log_level,
        ssl_keyfile=args.ssl_keyfile,
        ssl_certfile=args.ssl_certfile,
        workers=1,
    )


if __name__ == "__main__":
    main()
