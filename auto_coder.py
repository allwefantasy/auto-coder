import importlib.util
import os
import ray
import ast
import byzerllm
from typing import List,Dict,Any
import argparse 
from autocoder.pyproject import PyProject,Level1PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
import pydantic


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



class TranslateReadme(pydantic.BaseModel):
    filename:str = pydantic.Field(...,description="需要翻译的文件路径")
    content:str  = pydantic.Field(...,description="翻译后的内容")


class Translates(pydantic.BaseModel):
    readmes:List[TranslateReadme]
    

@byzerllm.prompt(render="jinja")
def translate_readme(content:str,lang:str)->str:
    '''
    下面是一些文件路径以及每个文件对应的内容：

    {{ content }}    
    
    请参考上面的内容，将上面的每一个文件对应的内容翻译成{{ lang }}。
    
    '''
    pass


def main():
    parser = argparse.ArgumentParser(description="Auto-implement missing methods in a Python script.")
    parser.add_argument("--source_dir", required=True, help="Path to the project")
    parser.add_argument("--git_url", help="URL of the git repository")
    parser.add_argument("--target_file", required=False, help="the file to write the source code to")
    parser.add_argument("--query",  help="the instruction to handle the source code")
    parser.add_argument("--template",  default="common",help="the instruction to handle the source code")
    parser.add_argument("--project_type",  default="py",help="the type of the project. py,ts,or py-script, default is py")
    parser.add_argument("--execute", action='store_true', help="Execute command line or not")    

    parser.add_argument("--package_name",  default="",help="only works for py-script project type. The package name of the script. default is empty.")
    parser.add_argument("--script_path",  default="",help="only works for py-script project type. The path to the Python script. default is empty.")

    parser.add_argument("--model",  default="",help="the model name to use")

    args = parser.parse_args()

    if args.model:
        byzerllm.connect_cluster()
        llm = byzerllm.ByzerLLM()
        llm.setup_template(model=args.model,template="auto")
        llm.setup_default_model_name(args.model)
    else:
        llm = None

    source_dir = args.source_dir    
    git_url = args.git_url or None
    target_file = args.target_file or None    
    template = args.template 
    project_type = args.project_type
    should_execute = args.execute

    lang = "中文"
    tranlate_file_suffix = ""

    if project_type == "ts":
        pp = TSProject(source_dir=source_dir, git_url=git_url, target_file=target_file)
    elif project_type == "py-script":
        pp = Level1PyProject(script_path=args.script_path, package_name=args.package_name)          
    elif project_type == "py":
        pp = PyProject(source_dir=source_dir, git_url=git_url, target_file=target_file)
    elif project_type.startswith("translate"):
        #translate/中文/.md/cn
        [_,lang,suffix,tranlate_file_suffix] = project_type.split("/")
        pp = SuffixProject(source_dir=source_dir, git_url=git_url, target_file=target_file,project_type=suffix) 
        template = "translate"
        lang = lang 
        should_execute = False
    else:
        pp = SuffixProject(source_dir=source_dir, git_url=git_url, target_file=target_file,project_type=project_type)

    pp.run()
    content = pp.output()
    
    if template == "common":
        instruction = args.query or "Please implement the following methods"
        content = instruction_template(instruction=instruction, content=content)
    elif template == "auto_implement":            
        content = auto_implement_function_template(instruction="", content=content)
    elif template == "translate":
        content = translate_readme(content=content,lang=lang)
        t = llm.chat_oai(conversations=[{
            "role": "user",
            "content": content
        }],response_class=Translates)         
        readmes:Translates = t[0].value
        for readme in readmes.readmes:
            filename, extension = os.path.splitext(readme.filename)
            chinese_filename = f"{filename}-{tranlate_file_suffix}{extension}"
            with open(chinese_filename, "w") as file:        
                file.write(readme.content)
                
        
    if should_execute:
        t = llm.chat_oai(conversations=[{
            "role": "user",
            "content": content
        }]) 
        content = t[0].output
    
    with open(target_file, "w") as file:        
        file.write(content)


if __name__ == "__main__":
    main()



    
    
