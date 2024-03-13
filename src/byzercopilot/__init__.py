import importlib.util
import os
import ray
import ast
import byzerllm
from typing import List,Dict,Any
import argparse
from byzercopilot.common import SourceCode    

ray.init(address="auto",namespace="default",ignore_reinit_error=True)  
llm = byzerllm.ByzerLLM()
llm.setup_template(model="sparkdesk_chat",template="auto")
llm.setup_default_model_name("sparkdesk_chat")




if __name__ == "__main__":    
    parser = argparse.ArgumentParser(description="Auto-implement missing methods in a project")
    parser.add_argument("", help="Path to the Python script")
    parser.add_argument("package_name", help="Name of the package to filter imports")
    args = parser.parse_args()

    script_path = args.script_path or "/home/winubuntu/projects/ByzerLLMEvaluation/src/byzerevaluation/judge.py"
    package_name = args.package_name or "byzerevaluation"
    s = run(script_path, package_name)
    print(s)

    s = run(script_path, package_name)
    print(s)
    
    
