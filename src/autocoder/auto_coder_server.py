import os
import time
import uvicorn
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from autocoder.command_args import parse_args
from autocoder.auto_coder import load_include_files,resolve_include_path,Dispacher,main
from autocoder.rag.api_server import ServerArgs
from autocoder.rag.simple_rag import SimpleRAG
from autocoder.rag.llm_wrapper import LLWrapper
from autocoder.common import git_utils
from autocoder.common.screenshots import gen_screenshots

from pydantic import BaseModel
from typing import List, Optional, Union

from autocoder.index.for_command import index_command, index_query_command
from autocoder.common import AutoCoderArgs
from loguru import logger

import byzerllm
import hashlib

app = FastAPI()

origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class DocBuildArgs(AutoCoderArgs):
    source_dir: str = ""
    model: str = ""
    emb_model: str = ""
    file: str = ""
    ray_address: str = ""
    required_exts: str = ""
    collection: str = "default"
    description: str = ""

class DocQueryArgs(AutoCoderArgs):
    query: str = ""
    source_dir: str = "."
    model: str = ""
    emb_model: str = ""
    file: str = ""
    ray_address: str = ""
    execute: bool = False
    collections: str = "default"
    description: str = ""

class DocChatArgs(AutoCoderArgs):
    file: str = ""
    model: str = ""
    emb_model: str = ""
    ray_address: str = ""
    source_dir: str = "."
    collections: str = "default"
    description: str = ""

class AutoCoderRevertArgs(AutoCoderArgs):
    file: str

class AutoCoderInitArgs(AutoCoderArgs):
    source_dir: str
    project_type: str

class AutoCoderScreenshotArgs(AutoCoderArgs):
    urls: str
    output: str

class AutoCoderNextArgs(BaseModel):
    name: str
    source_dir: str = "."

class AutoCoderRunArgs(AutoCoderArgs):
    pass

async def setup_llm(args: AutoCoderArgs):
    if args.model:
        try:        
            byzerllm.connect_cluster(address=args.ray_address)        
        except Exception as e:
            logger.warning(f"Detecting error when connecting to ray cluster: {e}, try to connect to ray cluster without storage support.")
            byzerllm.connect_cluster(address=args.ray_address)

        llm = byzerllm.ByzerLLM(verbose=args.print_request)

        llm.setup_template(model=args.model,template="auto")
        llm.setup_default_model_name(args.model)
        llm.setup_max_output_length(args.model,args.model_max_length)
        llm.setup_max_input_length(args.model,args.model_max_input_length)
        llm.setup_extra_generation_params(args.model, {"max_length": args.model_max_length})
        
        if args.vl_model:
            vl_model = byzerllm.ByzerLLM()
            vl_model.setup_default_model_name(args.vl_model)
            vl_model.setup_template(model=args.vl_model,template="auto")            
            llm.setup_sub_client("vl_model",vl_model)

        if args.sd_model:
            sd_model = byzerllm.ByzerLLM()
            sd_model.setup_default_model_name(args.sd_model)
            sd_model.setup_template(model=args.sd_model,template="auto")            
            llm.setup_sub_client("sd_model",sd_model)

        if args.index_model:
            index_model = byzerllm.ByzerLLM()
            index_model.setup_default_model_name(args.index_model)
            index_model.setup_max_output_length(args.index_model,args.index_model_max_length or args.model_max_length)
            index_model.setup_max_input_length(args.index_model,args.index_model_max_input_length or args.model_max_input_length)
            index_model.setup_extra_generation_params(args.index_model, {"max_length": args.index_model_max_length or args.model_max_length})  
            llm.setup_sub_client("index_model",index_model)  

        if args.emb_model:
            llm.setup_default_emb_model_name(args.emb_model)
            emb_model = byzerllm.ByzerLLM()
            emb_model.setup_default_emb_model_name(args.emb_model)
            emb_model.setup_template(model=args.emb_model,template="auto")            
            llm.setup_sub_client("emb_model",emb_model)       

        if args.code_model:
            code_model = byzerllm.ByzerLLM()  
            code_model.setup_default_model_name(args.code_model)
            llm.setup_sub_client("code_model",code_model)
    else:
        llm = None

    return llm

@app.post("/api/ac/index")
async def index(args: AutoCoderArgs):
    llm = await setup_llm(args)
    await index_command(args, llm)
    return {"status": "success"}

@app.post("/api/ac/index-query")
async def index_query(args: AutoCoderArgs):
    llm = await setup_llm(args)
    result = await index_query_command(args, llm)
    return {"status": "success", "result": result}

@app.post("/api/ac/revert")
async def revert(args: AutoCoderRevertArgs):
    repo_path = args.source_dir
    file_content = open(args.file).read()
    md5 = hashlib.md5(file_content.encode('utf-8')).hexdigest()        
    file_name = os.path.basename(args.file)
    
    revert_result = git_utils.revert_changes(repo_path, f"auto_coder_{file_name}_{md5}")
    if revert_result:
        return {"status": "success", "message": f"Successfully reverted changes for {args.file}"}
    else:
        return {"status": "failed", "message": f"Failed to revert changes for {args.file}"}

@app.post("/api/ac/init")
async def init(args: AutoCoderInitArgs):
    if not args.project_type:
        return {"status": "failed", "message": "Please specify the project type.The available project types are: py|ts| or any other file extension(for example: .java,.scala), you can specify multiple file extensions separated by commas."}
    
    os.makedirs(os.path.join(args.source_dir, "actions"), exist_ok=True)
    os.makedirs(os.path.join(args.source_dir, ".auto-coder"), exist_ok=True)

    from autocoder.common.command_templates import create_actions
    source_dir=os.path.abspath(args.source_dir)
    create_actions(source_dir=source_dir,params={"project_type":args.project_type,"source_dir":source_dir})        
    git_utils.init(os.path.abspath(args.source_dir))
    return {"status": "success", "message": f"Successfully initialized auto-coder project in {os.path.abspath(args.source_dir)}."}

@app.post("/api/ac/screenshot")
async def screenshot(args: AutoCoderScreenshotArgs):
    gen_screenshots(args.urls, args.output)
    return {"status": "success", "message": f"Successfully captured screenshot of {args.urls} and saved to {args.output}"}

@app.post("/api/ac/next")
async def next_action(args: AutoCoderNextArgs):
    actions_dir = os.path.join(os.getcwd(), "actions")
    if not os.path.exists(actions_dir):
        return {"status": "failed", "message": "Current directory does not have an actions directory"}
    
    action_files = [f for f in os.listdir(actions_dir) if f[:3].isdigit() and f.endswith(".yml") and f[:3] != "101"]
    if not action_files:
        max_seq = 0
    else:
        seqs = [int(f[:3]) for f in action_files]
        max_seq = max(seqs)
    
    new_seq = str(max_seq + 1).zfill(3)
    prev_files = [f for f in action_files if int(f[:3]) < int(new_seq)]
    
    if not prev_files:
        new_file = os.path.join(actions_dir, f"{new_seq}_{args.name}.yml")
        with open(new_file, "w") as f:
            pass
    else:
        prev_file = sorted(prev_files)[-1]  # 取序号最大的文件
        with open(os.path.join(actions_dir, prev_file), "r") as f:
            content = f.read()
        new_file = os.path.join(actions_dir, f"{new_seq}_{args.name}.yml") 
        with open(new_file, "w") as f:
            f.write(content)
    
    return {"status": "success", "message": f"Successfully created new action file: {new_file}"}

@app.post("/api/ac/run")
async def run(args: AutoCoderRunArgs):
    logger.info(f"Received args: {args}")
    llm = await setup_llm(args)
    dispacher = Dispacher(args, llm)
    dispacher.dispach()
    return {"status": "success"}

@app.post("/api/ac/doc/build")
async def doc_build(args: DocBuildArgs):
    llm = await setup_llm(args)
    rag = SimpleRAG(llm=llm,args=args,path = args.source_dir)
    rag.build()
    return {"status": "success"}

@app.post("/api/ac/doc/query")
async def doc_query(args: DocQueryArgs):
    llm = await setup_llm(args)
    rag = SimpleRAG(llm = llm,args=args,path = "")
    response,contexts = rag.stream_search(args.query)
    
    return {"response": response, "contexts": contexts}

@app.post("/api/ac/doc/chat")
async def doc_chat(args: DocChatArgs):
    llm = await setup_llm(args)
    rag = SimpleRAG(llm=llm, args=args, path="")
    rag.stream_chat_repl(args.query)
    return {"status": "success"}

@app.post("/api/ac/doc/serve")
async def doc_serve(args: ServerArgs):
    llm = await setup_llm(args)
    rag = SimpleRAG(llm=llm, args=args, path="")  
    llm_wrapper = LLWrapper(llm=llm, rag=rag)
    serve(llm=llm_wrapper, args=args)
    return {"status": "success"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)