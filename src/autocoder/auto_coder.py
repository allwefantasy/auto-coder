import byzerllm
from typing import List,Dict,Any,Optional
import argparse 
from autocoder.common import AutoCoderArgs
from autocoder.dispacher import Dispacher 
from autocoder.lang import lang_desc
from autocoder.common import git_utils,code_auto_execute
from autocoder.rag.simple_rag import SimpleRAG
from autocoder.utils.llm_client_interceptors import token_counter_interceptor
from autocoder.db.store import Store
import yaml   
import locale
import os
from byzerllm.utils.client import EventCallbackResult,EventName
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import FormattedText
from typing import List,Dict,Any

from jinja2 import Template
import hashlib
from autocoder.index.index import IndexManager
from autocoder.utils.rest import HttpDoc
from byzerllm.apps.command import get_latest_byzer_retrieval_lib

def parse_args() -> AutoCoderArgs:
    system_lang, _ = locale.getdefaultlocale()
    lang = "zh" if system_lang and system_lang.startswith("zh") else "en"
    desc = lang_desc[lang]

    parser = argparse.ArgumentParser(description=desc["parser_desc"])
    subparsers = parser.add_subparsers(dest="command")
    
    parser.add_argument("--source_dir", required=False, help=desc["source_dir"])
    parser.add_argument("--git_url", help=desc["git_url"])
    parser.add_argument("--target_file", required=False, help=desc["target_file"])
    parser.add_argument("--query", help=desc["query"])
    parser.add_argument("--template", default="common", help=desc["template"])
    parser.add_argument("--project_type", default="py", help=desc["project_type"])
    parser.add_argument("--execute", action='store_true', help=desc["execute"])
    parser.add_argument("--package_name", default="", help=desc["package_name"])  
    parser.add_argument("--script_path", default="", help=desc["script_path"])
    
    parser.add_argument("--model", default="", help=desc["model"])    
    parser.add_argument("--model_max_length", type=int, default=2000, help=desc["model_max_length"])
    parser.add_argument("--model_max_input_length", type=int, default=6000, help=desc["model_max_input_length"])

    parser.add_argument("--vl_model", default="", help=desc["vl_model"])
    parser.add_argument("--sd_model", default="", help=desc["sd_model"])
    parser.add_argument("--emb_model", default="", help=desc["emb_model"])
    
    parser.add_argument("--index_model", default="", help=desc["index_model"])
    parser.add_argument("--index_model_max_length", type=int, default=0, help=desc["model_max_length"])
    parser.add_argument("--index_model_max_input_length", type=int, default=0, help=desc["model_max_input_length"])
    parser.add_argument("--index_model_anti_quota_limit", type=int, default=0, help=desc["anti_quota_limit"])
    parser.add_argument("--index_filter_level",type=int, default=0, help=desc["index_filter_level"])
    parser.add_argument("--index_filter_workers",type=int, default=1, help=desc["index_filter_workers"])
    
    parser.add_argument("--file", default=None, required=False, help=desc["file"])
    parser.add_argument("--ray_address", default="auto", help=desc["ray_address"])
    parser.add_argument("--anti_quota_limit", type=int, default=1, help=desc["anti_quota_limit"])
    parser.add_argument("--skip_build_index", action='store_false', help=desc["skip_build_index"])
    parser.add_argument("--print_request", action='store_true', help=desc["print_request"])
    parser.add_argument("--py_packages", required=False, default="", help=desc["py_packages"])
    parser.add_argument("--human_as_model", action='store_true', help=desc["human_as_model"])
    parser.add_argument("--urls", default="", help=desc["urls"])
    parser.add_argument("--urls_use_model", action='store_true', help=desc["urls_use_model"])
    
    
    parser.add_argument("--search_engine", default="", help=desc["search_engine"])
    parser.add_argument("--search_engine_token", default="",help=desc["search_engine_token"])
    parser.add_argument("--enable_rag_search", action='store_true',help="")

    parser.add_argument("--auto_merge", action='store_true', help=desc["auto_merge"])

    parser.add_argument("--image_file", default="", help=desc["image_file"])
    parser.add_argument("--image_max_iter",type=int, default=1, help=desc["image_max_iter"])
    

    revert_parser = subparsers.add_parser("revert", help=desc["revert_desc"])
    revert_parser.add_argument("--file", help=desc["revert_desc"])

    store_parser = subparsers.add_parser("store", help=desc["store_desc"])
    store_parser.add_argument("--source_dir", help=desc["source_dir"])
    store_parser.add_argument("--ray_address", default="auto", help=desc["ray_address"])

    index_parser = subparsers.add_parser("index", help=desc["index_desc"])  # New subcommand
    index_parser.add_argument("--file", help=desc["file"])
    index_parser.add_argument("--model", default="", help=desc["model"]) 
    index_parser.add_argument("--index_model", default="", help=desc["index_model"])
    index_parser.add_argument("--source_dir", required=False, help=desc["source_dir"])
    index_parser.add_argument("--project_type", default="py", help=desc["project_type"])
    index_parser.add_argument("--ray_address", default="auto", help=desc["ray_address"])

    index_query_parser = subparsers.add_parser("index-query", help=desc["index_query_desc"])  # New subcommand  
    index_query_parser.add_argument("--file", help=desc["file"])
    index_query_parser.add_argument("--model", default="", help=desc["model"]) 
    index_query_parser.add_argument("--index_model", default="", help=desc["index_model"])
    index_query_parser.add_argument("--source_dir", required=False, help=desc["source_dir"])    
    index_query_parser.add_argument("--query", help=desc["query"])
    index_query_parser.add_argument("--index_filter_level",type=int, default=2, help=desc["index_filter_level"])        
    index_query_parser.add_argument("--ray_address", default="auto", help=desc["ray_address"])

    doc_parser = subparsers.add_parser("doc", help=desc["doc_desc"])
    doc_parser.add_argument("--urls", default="", help=desc["urls"])
    doc_parser.add_argument("--model", default="", help=desc["model"]) 
    doc_parser.add_argument("--target_file", default="", help=desc["target_file"])
    doc_parser.add_argument("--file",default="", help=desc["file"])
    doc_parser.add_argument("--source_dir", required=False, help=desc["source_dir"]) 
    doc_parser.add_argument("--human_as_model", action='store_true', help=desc["human_as_model"])
    doc_parser.add_argument("--urls_use_model", action='store_true', help=desc["urls_use_model"])
    doc_parser.add_argument("--ray_address", default="auto", help=desc["ray_address"])

    doc_subparsers = doc_parser.add_subparsers(dest="doc_command")
    doc_build_parse = doc_subparsers.add_parser("build",help="")
    doc_build_parse.add_argument("--source_dir", default="", help="")
    doc_build_parse.add_argument("--model", default="", help=desc["model"]) 
    doc_build_parse.add_argument("--emb_model", default="", help=desc["emb_model"])
    doc_build_parse.add_argument("--file",default="", help=desc["file"])
    doc_build_parse.add_argument("--ray_address", default="auto", help=desc["ray_address"])
    doc_build_parse.add_argument("--required_exts", default="", help="")

    doc_query_parse = doc_subparsers.add_parser("query",help="")
    doc_query_parse.add_argument("--query", default="", help="")
    doc_query_parse.add_argument("--source_dir", default="", help="")
    doc_query_parse.add_argument("--model", default="", help=desc["model"])
    doc_query_parse.add_argument("--emb_model", default="", help=desc["emb_model"]) 
    doc_query_parse.add_argument("--file",default="", help=desc["file"])
    doc_query_parse.add_argument("--ray_address", default="auto", help=desc["ray_address"])
    doc_query_parse.add_argument("--execute", action='store_true', help=desc["execute"])

    args = parser.parse_args()

    return AutoCoderArgs(**vars(args)),args


def main():
    args,raw_args = parse_args()
    args:AutoCoderArgs = args
    
    if args.file:
        with open(args.file, "r") as f:
            config = yaml.safe_load(f)
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

    if args.model:
        
        home = os.path.expanduser("~")
        auto_coder_dir = os.path.join(home, ".auto-coder")
        libs_dir = os.path.join(auto_coder_dir, "storage", "libs")                
        code_search_path = None
        if os.path.exists(libs_dir):        
            retrieval_libs_dir = os.path.join(libs_dir,get_latest_byzer_retrieval_lib(libs_dir))            
            if os.path.exists(retrieval_libs_dir):
                code_search_path = [retrieval_libs_dir]
        
        byzerllm.connect_cluster(address=args.ray_address,code_search_path=code_search_path)        

        llm = byzerllm.ByzerLLM(verbose=args.print_request)
        
        if args.human_as_model:
            def intercept_callback(llm,model: str, input_value: List[Dict[str, Any]]) -> EventCallbackResult:            
                if input_value[0].get("embedding",False) or input_value[0].get("tokenizer",False) or input_value[0].get("apply_chat_template",False) or input_value[0].get("meta",False):
                        return True,None
                if not input_value[0].pop("human_as_model",None):
                    return True, None
                
                print(f"Intercepted request to model: {model}")        
                instruction = input_value[0]["instruction"] 
                history = input_value[0]["history"]
                final_ins = instruction + "\n".join([item["content"] for item in history])                    

                with open(args.target_file, "w") as f:
                    f.write(final_ins)

                print(f'''\033[92m {final_ins[0:100]}....\n\n(The instruction to model have be saved in: {args.target_file})\033[0m''')    
                
                lines = []
                while True:
                    line = prompt(FormattedText([("#00FF00", "> ")]), multiline=False)
                    if line.strip() == "EOF":
                        break
                    lines.append(line)
                
                result = "\n".join(lines)

                with open(args.target_file, "w") as f:
                    f.write(result)

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