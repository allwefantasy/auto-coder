import byzerllm
from typing import List,Dict,Any,Optional
import argparse 
from autocoder.common import AutoCoderArgs
from autocoder.dispacher import Dispacher    

def parse_args() -> AutoCoderArgs:
    parser = argparse.ArgumentParser(description="Auto-implement missing methods in a Python script.")
    parser.add_argument("--source_dir", required=True, help="Path to the project")
    parser.add_argument("--git_url", help="URL of the git repository") 
    parser.add_argument("--target_file", required=False, help="the file to write the source code to")
    parser.add_argument("--query", help="the instruction to handle the source code")
    parser.add_argument("--template", default="common", help="the instruction to handle the source code")
    parser.add_argument("--project_type", default="py", help="the type of the project. py, ts, py-script, translate, or file suffix. default is py")
    parser.add_argument("--execute", action='store_true', help="Execute command line or not")
    parser.add_argument("--package_name", default="", help="only works for py-script project type. The package name of the script. default is empty.")
    parser.add_argument("--script_path", default="", help="only works for py-script project type. The path to the Python script. default is empty.")  
    parser.add_argument("--model", default="", help="the model name to use")
    
    args = parser.parse_args()
    return AutoCoderArgs(**vars(args))


def main():
    args = parse_args()
    
    if args.model:
        byzerllm.connect_cluster()
        llm = byzerllm.ByzerLLM()
        llm.setup_template(model=args.model,template="auto")
        llm.setup_default_model_name(args.model)
    else:
        llm = None

    dispacher = Dispacher(args, llm)
    dispacher.dispach()

if __name__ == "__main__":
    main()



    
    
