from fastapi import FastAPI, Request
from autocoder.command_args import parse_args
from autocoder.auto_coder import Dispacher, resolve_include_path, load_include_files
from autocoder.common import AutoCoderArgs
from autocoder.utils.rest import HttpDoc
from autocoder.agent.planner import Planner
from autocoder.common.screenshots import gen_screenshots
from autocoder.common.anything2images import Anything2Images
from autocoder.rag.simple_rag import SimpleRAG
from autocoder.index.for_command import index_command, index_query_command
from autocoder.common import git_utils, code_auto_execute
from autocoder.rag.llm_wrapper import LLWrapper
from autocoder.utils.llm_client_interceptors import token_counter_interceptor
from autocoder.db.store import Store
from autocoder.rag.api_server import serve, ServerArgs
from loguru import logger
import byzerllm
import yaml
import os
import hashlib

app = FastAPI()

@app.post("/v1/run")
async def run(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    if args.file:
        with open(args.file, "r") as f:
            config = yaml.safe_load(f)
            config = load_include_files(config, args.file)
            for key, value in config.items():
                if key != "file":  
                    if isinstance(value, str) and value.startswith("ENV"):
                        from jinja2 import Template
                        template = Template(value.removeprefix("ENV").strip())
                        value = template.render(os.environ)
                    setattr(args, key, value)

    print("Command Line Arguments:")
    print("-" * 50)
    for arg, value in vars(args).items():
        print(f"{arg:20}: {value}")
    print("-" * 50)

    # init store
    store = Store(os.path.join(args.source_dir, ".auto-coder", "metadata.db"))
    store.update_token_counter(os.path.basename(args.source_dir), 0, 0)
                        
    llm = setup_llm(args)

    args.query = add_query_prefix_suffix(args)
    
    dispacher = Dispacher(args, llm)
    result = dispacher.dispach()
    
    return {"result": result}


@app.post("/v1/revert")
async def revert(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    repo_path = args.source_dir

    file_content = open(args.file).read()
    md5 = hashlib.md5(file_content.encode("utf-8")).hexdigest()
    file_name = os.path.basename(args.file)

    revert_result = git_utils.revert_changes(repo_path, f"auto_coder_{file_name}_{md5}")
    
    if revert_result:
        return {"message": f"Successfully reverted changes for {args.file}"}
    else:
        return {"message": f"Failed to revert changes for {args.file}"}

@app.post("/v1/store")
async def store(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    from autocoder.utils.print_table import print_table
    store = Store(os.path.join(args.source_dir, ".auto-coder", "metadata.db"))
    tc = store.get_token_counter()

    return {"token_counter": tc}    

@app.post("/v1/init")
async def init(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    if not args.project_type:
        logger.error(
            "Please specify the project type.The available project types are: py|ts| or any other file extension(for example: .java,.scala), you can specify multiple file extensions separated by commas."
        )
        return {"message": "Please specify the project type."}
    
    os.makedirs(os.path.join(args.source_dir, "actions"), exist_ok=True)
    os.makedirs(os.path.join(args.source_dir, ".auto-coder"), exist_ok=True)

    from autocoder.common.command_templates import create_actions

    source_dir = os.path.abspath(args.source_dir)
    create_actions(
        source_dir=source_dir,
        params={"project_type": args.project_type, "source_dir": source_dir},
    )
    git_utils.init(os.path.abspath(args.source_dir))
    
    return {"message": f"""Successfully initialized auto-coder project in {os.path.abspath(args.source_dir)}."""}

@app.post("/v1/screenshot")
async def screenshot(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    gen_screenshots(args.urls, args.output)

    return {"message": f"Successfully captured screenshot of {args.urls} and saved to {args.output}"}

@app.post("/v1/agent/planner")
async def agent_planner(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    llm = setup_llm(args)
    planner = Planner(args, llm)
    result = planner.run(args.query)

    return {"result": result}

@app.post("/v1/index")
async def index(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    llm = setup_llm(args)
    index_command(args, llm)
    
    return {"message": "Indexing completed"}

@app.post("/v1/index-query")
async def index_query(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    llm = setup_llm(args)
    result = index_query_command(args, llm)
    
    return result

@app.post("/v1/doc/build")
async def doc_build(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    llm = setup_llm(args)
    rag = SimpleRAG(llm=llm, args=args, path=args.source_dir)
    rag.build()

    return {"message": "Successfully built the document index"}

@app.post("/v1/doc/query")
async def doc_query(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)

    llm = setup_llm(args)
    rag = SimpleRAG(llm=llm, args=args, path="")
    response, contexts = rag.stream_search(args.query)

    s = ""
    for res in response:
        s += res

    contexts_result = "\n".join(set([ctx["doc_url"] for ctx in contexts]))

    if args.execute:
        executor = code_auto_execute.CodeAutoExecute(
            llm, args, code_auto_execute.Mode.SINGLE_ROUND
        )
        executor.run(query=args.query, context=s, source_code="")

    result = {
        "response": s,
        "contexts": contexts_result
    }

    return result

@app.post("/v1/doc/chat")
async def doc_chat(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    llm = setup_llm(args)
    rag = SimpleRAG(llm=llm, args=args, path="")
    rag.stream_chat_repl(args.query)
    
    return {"message": "Chat session ended"}

@app.post("/v1/doc/serve")
async def doc_serve(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    llm = setup_llm(args)
    server_args = ServerArgs(**{arg: getattr(args, arg) for arg in vars(ServerArgs())})
    server_args.served_model_name = server_args.served_model_name or args.model
    rag = SimpleRAG(llm=llm, args=args, path="")
    llm_wrapper = LLWrapper(llm=llm, rag=rag)
    serve(llm=llm_wrapper, args=server_args)
    
    return {"message": "Serving document retrieval API"}

@app.post("/v1/doc2html")
async def doc2html(request: Request):
    args_dict = await request.json()
    args = AutoCoderArgs(**args_dict)
    
    llm = setup_llm(args)
    a2i = Anything2Images(llm=llm, args=args)
    html = a2i.to_html(args.urls)
    output_path = os.path.join(
        args.output, f"{os.path.splitext(os.path.basename(args.urls))[0]}.html"
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
        
    return {"message": f"Successfully converted {args.urls} to {output_path}"}


def setup_llm(args):
    byzerllm.connect_cluster(address=args.ray_address)
    llm = byzerllm.ByzerLLM(verbose=args.print_request)
    
    if args.human_as_model:
        from byzerllm.utils.client import EventCallbackResult, EventName
        from prompt_toolkit import prompt
        from prompt_toolkit.formatted_text import FormattedText

        def intercept_callback(llm, model: str, input_value):
            if (
                input_value[0].get("embedding", False)
                or input_value[0].get("tokenizer", False)
                or input_value[0].get("apply_chat_template", False)
                or input_value[0].get("meta", False)
            ):
                return True, None
            if not input_value[0].pop("human_as_model", None):
                return True, None

            print(f"Intercepted request to model: {model}")
            instruction = input_value[0]["instruction"]
            final_ins = instruction

            print(
                f"""\033[92m {final_ins[0:100]}....\n\n(The instruction to model have be saved in: {args.target_file})\033[0m"""
            )

            lines = []
            while True:
                line = prompt(FormattedText([("#00FF00", "> ")]), multiline=False)
                if line.strip() == "EOF":
                    break
                lines.append(line)

            result = "\n".join(lines)

            if result.lower() == "c":
                return True, None
            else:
                v = [
                    {
                        "predict": result,
                        "input": input_value[0]["instruction"],
                        "metadata": {},
                    }
                ]
                return False, v

        llm.add_event_callback(EventName.BEFORE_CALL_MODEL, intercept_callback)
        
    llm.add_event_callback(EventName.AFTER_CALL_MODEL, token_counter_interceptor)

    llm.setup_template(model=args.model, template="auto")
    llm.setup_default_model_name(args.model)
    llm.setup_max_output_length(args.model, args.model_max_length)
    llm.setup_max_input_length(args.model, args.model_max_input_length)
    llm.setup_extra_generation_params(
        args.model, {"max_length": args.model_max_length}
    )

    if args.vl_model:
        vl_model = byzerllm.ByzerLLM()
        vl_model.setup_default_model_name(args.vl_model)
        vl_model.setup_template(model=args.vl_model, template="auto")
        llm.setup_sub_client("vl_model", vl_model)
        
    if args.sd_model:
        sd_model = byzerllm.ByzerLLM()
        sd_model.setup_default_model_name(args.sd_model)
        sd_model.setup_template(model=args.sd_model, template="auto") 
        llm.setup_sub_client("sd_model", sd_model)
    
    if args.index_model:
        index_model = byzerllm.ByzerLLM()
        index_model.setup_default_model_name(args.index_model)
        index_model.setup_max_output_length(args.index_model, args.index_model_max_length or args.model_max_length)
        index_model.setup_max_input_length(args.index_model, args.index_model_max_input_length or args.model_max_input_length)
        index_model.setup_extra_generation_params(
            args.index_model,
            {"max_length": args.index_model_max_length or args.model_max_length},
        )
        llm.setup_sub_client("index_model", index_model)
    
    if args.emb_model:
        llm.setup_default_emb_model_name(args.emb_model)
        emb_model = byzerllm.ByzerLLM()
        emb_model.setup_default_emb_model_name(args.emb_model)
        emb_model.setup_template(model=args.emb_model, template="auto")
        llm.setup_sub_client("emb_model", emb_model) 
        
    if args.code_model:
        code_model = byzerllm.ByzerLLM()
        code_model.setup_default_model_name(args.code_model)
        llm.setup_sub_client("code_model", code_model)
        
    if args.planner_model:
        planner_model = byzerllm.ByzerLLM()
        planner_model.setup_default_model_name(args.planner_model)
        llm.setup_sub_client("planner_model", planner_model)
            
    return llm

def add_query_prefix_suffix(args):
    if args.query_prefix:
        args.query = f"{args.query_prefix}\n{args.query}"
    if args.query_suffix:
        args.query = f"{args.query}\n{args.query_suffix}"
    
    return args.query