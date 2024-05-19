
import pydantic
import ast
import sys
import subprocess
import os
import time
from typing import List,Dict,Any,Optional,Union

class SourceCode(pydantic.BaseModel):
    module_name: str
    source_code: str
    tag: str = ""


class TranslateReadme(pydantic.BaseModel):
    filename:str = pydantic.Field(...,description="需要翻译的文件路径")
    content:str  = pydantic.Field(...,description="翻译后的内容")


class Translates(pydantic.BaseModel):
    readmes:List[TranslateReadme]

class TranslateArgs(pydantic.BaseModel):
    '''
    示例：把项目中的markdown文档翻译成中文, 只翻译  test/abc.md 文件, 保存到test1目录下,翻译文件名
    此时对应的字段值应该是
    target_lang=中文
    file_suffix=.md
    new_file_mark=cn
    file_list=test/abc.md
    output_dir=test1
    should_translate_file_name=True
    '''
    target_lang: str = pydantic.Field(..., description="The target language to translate to")
    file_suffix: str = pydantic.Field(..., description="to filter the file by suffix, e.g. py, ts, md, etc. if multiple, use comma to separate")    
    new_file_mark: str = pydantic.Field(..., description="according to the file suffix, the new file name should be like this: filename-new_file_mark.file_suffix")    
    file_list: List[str] = pydantic.Field(..., description="the file list to translate provied")    
    output_dir: str = pydantic.Field(..., description="the output directory to save the translated files")    
    should_translate_file_name: bool = pydantic.Field(..., description="whether to translate the file name or not") 

class ExecuteStep(pydantic.BaseModel):
    code: str = pydantic.Field(..., description="The code line to execute, e.g. `print('hello world')` or `ls -l`, shell or python code.")
    lang: str = pydantic.Field(..., description="The language to execute the code line, python,shell. default is python")
    total_steps: Optional[int] = pydantic.Field(-1, description="The total steps to finish the user's question")
    current_step: Optional[int] = pydantic.Field(-1, description="The current step to finish the user's question")
    cwd: Optional[str] = pydantic.Field(None, description="The current working directory to execute the command line")
    env: Optional[Dict[str, Any]] = pydantic.Field(None, description="The environment variables to execute the command line")
    timeout: Optional[int] = pydantic.Field(None, description="The timeout to execute the command line")
    ignore_error: Optional[bool] = pydantic.Field(False, description="Ignore the error of the command line")

class ExecuteSteps(pydantic.BaseModel):
    steps:List[ExecuteStep]


class EnvInfo(pydantic.BaseModel):
    os_name: str
    os_version: str
    python_version: str
    conda_env: Optional[str]
    virtualenv: Optional[str] 
    has_bash: bool



def has_sufficient_content(file_content, min_line_count=10):
    """Check if the file has a minimum number of substantive lines."""
    lines = [line for line in file_content.split('\n') if line.strip() and not line.strip().startswith('#')]
    return len(lines) >= min_line_count

def remove_comments_and_docstrings(source):
    """Remove comments and docstrings from the Python source code."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and ast.get_docstring(node):
            node.body = node.body[1:]  # Remove docstring
        elif isinstance(node, ast.Expr) and isinstance(node.value, ast.Str):
            node.value.s = ""  # Remove comments
    return ast.unparse(tree)

def split_code_into_segments(source_code, max_tokens=1024):
    """Split the source code into segments of length up to max_tokens."""
    segments = []
    while len(source_code) > max_tokens:
        split_point = source_code.rfind('\n', 0, max_tokens)
        if split_point == -1:  # If no newline is found,
            split_point = max_tokens  # split at max_tokens
        segments.append(source_code[:split_point])
        source_code = source_code[split_point:]
    segments.append(source_code)
    return segments


def detect_env() -> EnvInfo:
        os_name = sys.platform
        os_version = ""
        if os_name == "win32":
            os_version = sys.getwindowsversion().major
        elif os_name == "darwin":
            os_version = subprocess.check_output(["sw_vers", "-productVersion"]).decode('utf-8').strip()
        elif os_name == "linux":
            os_version = subprocess.check_output(["uname", "-r"]).decode('utf-8').strip()
         
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        
        conda_env = os.environ.get("CONDA_DEFAULT_ENV")
        
        virtualenv = os.environ.get("VIRTUAL_ENV")
        
        has_bash = True
        try:
            subprocess.check_output(["bash", "--version"])
        except:
            has_bash = False
            
        return EnvInfo(
            os_name=os_name,
            os_version=os_version,
            python_version=python_version,
            conda_env=conda_env,
            virtualenv=virtualenv,
            has_bash=has_bash
        )


def chat_with_llm_step_by_step(llm,conversations, 
                               response_class, 
                               max_steps=30, 
                               anti_quota_limit=1):
    if max_steps == -1:
        max_steps = 30

    result = []
    t = llm.chat_oai(conversations=conversations, response_class=response_class,enable_default_sys_message=True)
    total_steps = max_steps
    current_step = 0

    while current_step < total_steps and t[0].value:        
        result.append(t[0].value)
        conversations.append({
            "role": "assistant",
            "content": t[0].response.output
        })
        print(f"{conversations[-1]['role']}: {conversations[-1]['content']}\n", flush=True)

        conversations.append({
            "role": "user",
            "content": "继续"
        })
        print(f"{conversations[-1]['role']}: {conversations[-1]['content']}\n", flush=True)        
        t = llm.chat_oai(conversations=conversations, response_class=response_class,enable_default_sys_message=True)        
        current_step += 1
        time.sleep(anti_quota_limit)

    return result, conversations

class AutoCoderArgs(pydantic.BaseModel):
    source_dir: Optional[str] = None
    git_url: Optional[str] = None
    target_file: Optional[str] = None
    query: Optional[str] = None
    template: Optional[str] = None
    project_type: Optional[str] = None
    execute: Optional[bool] = None
    package_name: Optional[str] = ""
    script_path: Optional[str] = ""
    model: Optional[str] = ""
    model_max_length: Optional[int] = 2000
    model_max_input_length: Optional[int] = 6000
    vl_model: Optional[str] = ""
    sd_model: Optional[str] = ""
    emb_model: Optional[str] = ""
    index_model: Optional[str] = ""
    index_model_max_length: Optional[int] = 0    
    index_model_max_input_length: Optional[int] = 0    
    index_model_anti_quota_limit:Optional[int] = 0
    index_filter_level: Optional[int] = 0
    index_filter_workers: Optional[int] = 1
    index_build_workers: Optional[int] = 1
    file: Optional[str] = ""
    ray_address: Optional[str] = ""
    anti_quota_limit: Optional[int] = 1
    skip_build_index: Optional[bool] = False
    print_request: Optional[bool] = False
    py_packages: Optional[str] = ""
    search: Optional[Union[str,List[str]]] = ""
    search_engine: Optional[str] = ""
    search_engine_token: Optional[str] = ""
    enable_rag_search: Optional[bool] = False
    enable_rag_context: Optional[bool] = False
    auto_merge: Optional[bool] = False
    image_file: Optional[str] = ""
    image_mode: Optional[str] = "direct"
    image_max_iter: Optional[int] = 1
    human_as_model:Optional[bool] = False
    urls: Optional[Union[str,List[str]]] = ""
    urls_use_model: Optional[bool] = False
    enable_multi_round_generate: Optional[bool] = False
    command: Optional[str] = None
    doc_command: Optional[str] = None
    required_exts: Optional[str] = None
    collection: Optional[str] = None  
    collections: Optional[str] = None
    description: Optional[str] = ""
    skip_confirm: Optional[bool] = False
    exclude_files: Optional[Union[str,List[str]]] = ""

    class Config:
        protected_namespaces = ()

