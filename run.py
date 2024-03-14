import byzerllm
from typing import List,Dict,Any,Optional
import argparse 
from autocoder.common import AutoCoderArgs
from autocoder.dispacher import Dispacher 
import yaml   

def main(): 
    args = AutoCoderArgs(source_dir="")  
    args.file = "/home/winubuntu/projects/ByzerRawCopilot/examples/copilot.yml" 
    if args.file:
        with open(args.file, "r") as f:
            config = yaml.safe_load(f)
            for key, value in config.items():
                if key != "file":  # 排除 --file 参数本身
                    setattr(args, key, value)
    
    if args.model:
        byzerllm.connect_cluster()
        llm = byzerllm.ByzerLLM()
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
