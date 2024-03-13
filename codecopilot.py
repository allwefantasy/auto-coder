import importlib.util
import os
import ray
import ast
import byzerllm
from typing import List,Dict,Any
import argparse
from byzercopilot.common import SourceCode    
from byzercopilot.pyproject import PyProject
from byzercopilot.tsproject import TSProject


byzerllm.connect_cluster()
llm = byzerllm.ByzerLLM()
llm.setup_template(model="sparkdesk_chat",template="auto")
llm.setup_default_model_name("sparkdesk_chat")


@byzerllm.prompt(render="jinja")
def auto_implement_function_template(instruction:str, content:str)->str:
    '''
    下面是一些文件路径以及每个文件对应的源码：

    {{ content }}

    请参考上面的内容，重新实现所有文件下方法体标记了如下内容的方法：

    ```python
    raise NotImplementedError("This function should be implemented by the model.")
    ```
    
    {{ instruction }}
        
    '''
    pass

@byzerllm.prompt(render="jinja")
def instruction_template(instruction:str, content:str)->str:
    '''
    下面是一些文件路径以及每个文件对应的源码：

    {{ content }}    
    
    {{ instruction }}
        
    '''
    pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Auto-implement missing methods in a Python script.")
    parser.add_argument("--source_dir", required=True, help="Path to the project")
    parser.add_argument("--git_url", help="URL of the git repository")
    parser.add_argument("--target_file", required=False, help="the file to write the source code to")
    parser.add_argument("--query",  help="the instruction to handle the source code")
    parser.add_argument("--template",  default="common",help="the instruction to handle the source code")
    parser.add_argument("--project_type",  default="py",help="the type of the project. py or ts")
    args = parser.parse_args()

    source_dir = args.source_dir
    if not os.path.exists(source_dir):
        raise ValueError(f"Directory {source_dir} does not exist.")

    git_url = args.git_url or None
    target_file = args.target_file or None    
    template = args.template 
    project_type = args.project_type

    if project_type == "ts":
        pp = TSProject(source_dir=source_dir, git_url=git_url, target_file=target_file)
    else:
        pp = PyProject(source_dir=source_dir, git_url=git_url, target_file=target_file)

    pp.run()
    v = pp.output()
    with open(target_file, "w") as file:
        content = v
        if template == "common":
            instruction = args.query or "Please implement the following methods"
            content = instruction_template(instruction=instruction, content=content)
        elif template == "auto_implement":            
            content = auto_implement_function_template(instruction="", content=content)
        file.write(content)

    
    
