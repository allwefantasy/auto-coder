import byzerllm
from typing import List,Dict,Any,Optional
import argparse 
from autocoder.common import AutoCoderArgs
from autocoder.dispacher import Dispacher 
from autocoder.lang import lang_desc
from autocoder.common import git_utils
import yaml   
import locale
import os
from byzerllm.utils.client import EventCallbackResult,EventName
from prompt_toolkit import prompt
from prompt_toolkit.formatted_text import FormattedText
from typing import List,Dict,Any

from jinja2 import Template
import hashlib


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
    parser.add_argument("--file", default=None, required=False, help=desc["file"])
    parser.add_argument("--anti_quota_limit", type=int, default=1, help=desc["anti_quota_limit"])
    parser.add_argument("--skip_build_index", action='store_false', help=desc["skip_build_index"])
    parser.add_argument("--print_request", action='store_true', help=desc["print_request"])
    parser.add_argument("--py_packages", required=False, default="", help=desc["py_packages"])
    parser.add_argument("--human_as_model", action='store_true', help=desc["human_as_model"])
    parser.add_argument("--urls", default="", help=desc["urls"])
    parser.add_argument("--search_engine", default="", help=desc["search_engine"])
    parser.add_argument("--search_engine_token", default="",help=desc["search_engine_token"])
    parser.add_argument("--auto_merge", action='store_true', help=desc["auto_merge"])

    revert_parser = subparsers.add_parser("revert", help=desc["revert_desc"])
    revert_parser.add_argument("--file", help=desc["revert_desc"])
    
    args = parser.parse_args()

    return AutoCoderArgs(**vars(args)),args


def main():
    args,raw_args = parse_args()
    
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
                
    
    if args.model:
        
        byzerllm.connect_cluster()        
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

        llm.setup_template(model=args.model,template="auto")
        llm.setup_default_model_name(args.model)
        llm.setup_max_output_length(args.model,args.model_max_length)
        llm.setup_extra_generation_params(args.model, {"max_length": args.model_max_length})
    else:
        llm = None

    dispacher = Dispacher(args, llm)
    dispacher.dispach()

if __name__ == "__main__":
    main()
