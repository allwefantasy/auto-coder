import byzerllm
from typing import List,Dict,Any,Optional
from autocoder.common import AutoCoderArgs
from autocoder.dispacher import Dispacher 
from autocoder.common import git_utils,code_auto_execute
from autocoder.rag.simple_rag import SimpleRAG
from autocoder.rag.llm_wrapper import LLWrapper
from autocoder.utils.llm_client_interceptors import token_counter_interceptor
from autocoder.db.store import Store
import yaml   
import os
from byzerllm.utils.client import EventCallbackResult,EventName
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import FormattedText

from jinja2 import Template
import hashlib
from autocoder.utils.rest import HttpDoc
from byzerllm.apps.byzer_storage.env import get_latest_byzer_retrieval_lib
from autocoder.command_args import parse_args
from autocoder.rag.api_server import serve,ServerArgs
from loguru import logger
from autocoder.common.command_templates import init_command_template

def resolve_include_path(base_path, include_path):
   if include_path.startswith('.') or include_path.startswith('..'):
       return os.path.abspath(os.path.join(os.path.dirname(base_path), include_path))
   else:
       return include_path

def load_include_files(config,base_path, max_depth=10, current_depth=0):
   if current_depth >= max_depth:
       raise ValueError(f"Exceeded maximum include depth of {max_depth},you may have a circular dependency in your include files.")
   
   if "include_file" in config:
       include_files = config['include_file']
       if not isinstance(include_files, list):
           include_files = [include_files]
       
       for include_file in include_files:
           abs_include_path = resolve_include_path(base_path, include_file)
           logger.info(f"Loading include file: {abs_include_path}")
           with open(abs_include_path, "r") as f:
               include_config = yaml.safe_load(f)
               if not include_config:
                   logger.info(f"Include file {abs_include_path} is empty,skipping.")
                   continue
               config.update({**load_include_files(include_config, max_depth, current_depth+1),**config})
       
       del config['include_file']
   
   return config

def main():
    args,raw_args = parse_args()
    args:AutoCoderArgs = args
    
    if args.file:
        with open(args.file, "r") as f:
            config = yaml.safe_load(f)
            config = load_include_files(config,args.file)
            for key, value in config.items():
                if key != "file":  # 排除 --file 参数本身   
                    ## key: ENV {{VARIABLE_NAME}}
                    if isinstance(value, str) and value.startswith("ENV"):  
                        template = Template(value.removeprefix("ENV").strip())                  
                        value = template.render(os.environ)                        
                    setattr(args, key, value)

    if raw_args.command == "revert":        
        repo_path = args.source_dir

        file_content = open(args.file).read()
        md5 = hashlib.md5(file_content.encode('utf-8')).hexdigest()        
        file_name = os.path.basename(args.file)
        
        revert_result = git_utils.revert_changes(repo_path, f"auto_coder_{file_name}_{md5}")
        if revert_result:
            print(f"Successfully reverted changes for {args.file}")
        else:
            print(f"Failed to revert changes for {args.file}")
        return                  
    
    print("Command Line Arguments:")
    print("-" * 50)
    for arg, value in vars(args).items():
        print(f"{arg:20}: {value}")
    print("-" * 50)    

    # init store
    store = Store(os.path.join(args.source_dir,".auto-coder","metadata.db"))
    store.update_token_counter(os.path.basename(args.source_dir),0,0)

    if raw_args.command == "store":
        from autocoder.utils.print_table import print_table
        tc = store.get_token_counter()
        print_table([tc])
        return
    
    if raw_args.command == "init":
        os.makedirs(os.path.join(args.source_dir, "actions"), exist_ok=True)
        os.makedirs(os.path.join(args.source_dir, ".auto-coder"), exist_ok=True)

        init_file_path = os.path.join(args.source_dir, "actions", "101_current_work.yml")
        with open(init_file_path, "w") as f:
            f.write(init_command_template.prompt(source_dir=os.path.abspath(args.source_dir)))
        
        git_utils.init(os.path.abspath(args.source_dir))
        print(f'''Successfully initialized auto-coder project in {os.path.abspath(args.source_dir)}.''')
        
        return

    if args.model:
        
        home = os.path.expanduser("~")
        auto_coder_dir = os.path.join(home, ".auto-coder")
        libs_dir = os.path.join(auto_coder_dir, "storage", "libs")                
        code_search_path = None
        if os.path.exists(libs_dir):        
            retrieval_libs_dir = os.path.join(libs_dir,get_latest_byzer_retrieval_lib(libs_dir))            
            if os.path.exists(retrieval_libs_dir):
                code_search_path = [retrieval_libs_dir]

        try:        
            byzerllm.connect_cluster(address=args.ray_address,code_search_path=code_search_path)        
        except Exception as e:
            logger.warning(f"Detecting error when connecting to ray cluster: {e}, try to connect to ray cluster without storage support.")
            byzerllm.connect_cluster(address=args.ray_address)

        llm = byzerllm.ByzerLLM(verbose=args.print_request)
        
        if args.human_as_model:
            def intercept_callback(llm,model: str, input_value: List[Dict[str, Any]]) -> EventCallbackResult:            
                if input_value[0].get("embedding",False) or input_value[0].get("tokenizer",False) or input_value[0].get("apply_chat_template",False) or input_value[0].get("meta",False):
                    return True,None
                if not input_value[0].pop("human_as_model",None):
                    return True, None
                
                print(f"Intercepted request to model: {model}")        
                instruction = input_value[0]["instruction"]                 
                final_ins = instruction                

                print(f'''\033[92m {final_ins[0:100]}....\n\n(The instruction to model have be saved in: {args.target_file})\033[0m''')    
                
                lines = []
                while True:
                    line = prompt(FormattedText([("#00FF00", "> ")]), multiline=False)
                    if line.strip() == "EOF":
                        break
                    lines.append(line)
                
                result = "\n".join(lines)
                
                if result.lower() == 'c':
                    return True, None
                else:            
                    v = [{
                        "predict":result,
                        "input":input_value[0]["instruction"],
                        "metadata":{}
                    }]
                    return False, v
            llm.add_event_callback(EventName.BEFORE_CALL_MODEL, intercept_callback)
        llm.add_event_callback(EventName.AFTER_CALL_MODEL,token_counter_interceptor)

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

    else:
        llm = None

    if raw_args.command == "index":  # New subcommand logic
        from autocoder.index.for_command import index_command
        index_command(args,llm)
        return

    if raw_args.command == "index-query":  # New subcommand logic
        from autocoder.index.for_command import index_query_command
        index_query_command(args,llm)
        return

    if raw_args.command == "doc":            
        if raw_args.doc_command == "build":
            rag = SimpleRAG(llm=llm,args=args,path = args.source_dir)
            rag.build()
            print("Successfully built the document index")
            return        
        elif raw_args.doc_command == "query":
            rag = SimpleRAG(llm = llm,args=args,path = "")
            response,contexts = rag.stream_search(args.query)
            
            s = ""
            print("\n\n=============RESPONSE==================\n\n")                                
            for res in response:                
                print(res,end="")  
                s  += res                          
            
            print("\n\n=============CONTEXTS==================")
        
            print("\n".join(set([ctx["doc_url"] for ctx in contexts])))    

            if args.execute:
                print("\n\n=============EXECUTE==================")
                executor = code_auto_execute.CodeAutoExecute(llm,args,code_auto_execute.Mode.SINGLE_ROUND)
                executor.run(query=args.query,context=s,source_code="")                                    
            return
        elif raw_args.doc_command == "chat": 
            rag = SimpleRAG(llm=llm, args=args, path="")
            rag.stream_chat_repl(args.query)
            return 
        
        elif raw_args.doc_command == "serve":  
            server_args = ServerArgs(**{arg: getattr(raw_args, arg) for arg in vars(ServerArgs())})
            rag = SimpleRAG(llm=llm, args=args, path="")  
            llm_wrapper = LLWrapper(llm=llm, rag=rag)
            serve(llm=llm_wrapper, args=server_args)
            return

        else:
            http_doc = HttpDoc(args = args, llm = llm, urls = None)
            source_codes = http_doc.crawl_urls()
            with open(args.target_file, "w") as f:
                f.write("\n".join([sc.source_code for sc in source_codes]))
            return

    dispacher = Dispacher(args, llm)
    dispacher.dispach()

if __name__ == "__main__":
    main()