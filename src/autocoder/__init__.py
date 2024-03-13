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


def get_imports_from_script(file_path):
    script = ""
    with open(file_path, "r") as file:
        script = file.read()
        tree = ast.parse(script, filename=file_path)
    
    imports = [node for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
    return imports,script

def filter_imports(imports, package_name):
    filtered_imports = []
    for import_ in imports:
        if isinstance(import_, ast.Import):
            for alias in import_.names:
                if alias.name.startswith(package_name):
                    filtered_imports.append(alias.name)
        elif isinstance(import_, ast.ImportFrom):
            if import_.module and import_.module.startswith(package_name):
                filtered_imports.append(import_.module)
    return filtered_imports



def fetch_source_code(import_name):
    spec = importlib.util.find_spec(import_name)
    if spec and spec.origin:
        with open(spec.origin, "r") as file:
            return file.read()
    return None

# @llm.prompt(render="jinja")
# @byzerllm.prompt(render="jinja")

@llm.prompt(render="jinja")
def auto_implement(instruction:str, sources:List[Dict[str,Any]])->str:
    '''
    下面是一些Python 模块以及对应的源码：

    {% for source in sources %}
    #Module:{{ source.module_name }}
    {{ source.source_code }}
    {% endfor %}

    请参考上面的内容，重新实现所有文件下方法体标记了如下内容的方法：

    ```python
    raise NotImplementedError("This function should be implemented by the model.")
    ```
    
    {{ instruction }}
        
    '''
    pass

def run(script_path, package_name):
    imports,script = get_imports_from_script(script_path)
    filtered_imports = filter_imports(imports, package_name)
    sources = [] 


    for import_name in filtered_imports:
        source_code = fetch_source_code(import_name)
        if source_code:
            sources.append(SourceCode(module_name=import_name, source_code=source_code))            
        else:
            print(f"Could not fetch source code for {import_name}.")

    sources.append(SourceCode(module_name="script", source_code=script))

    sources = [source.dict() for source in sources]
    return auto_implement(instruction="", sources=sources)

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
    
    
