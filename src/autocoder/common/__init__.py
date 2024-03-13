import pydantic
import ast
from typing import List,Dict,Any,Optional

class SourceCode(pydantic.BaseModel):
    module_name: str
    source_code: str


class TranslateReadme(pydantic.BaseModel):
    filename:str = pydantic.Field(...,description="需要翻译的文件路径")
    content:str  = pydantic.Field(...,description="翻译后的内容")


class Translates(pydantic.BaseModel):
    readmes:List[TranslateReadme]

class TranslateArgs(pydantic.BaseModel):
    '''
    示例：把项目中的markdown文档翻译成中文
    此时对应的字段值应该是
    target_lang=中文
    file_suffix=.md
    new_file_mark=cn
    '''
    target_lang: str = pydantic.Field(..., description="The target language to translate to")
    file_suffix: str = pydantic.Field(..., description="to filter the file by suffix, e.g. py, ts, md, etc. if multiple, use comma to separate")    
    new_file_mark: str = pydantic.Field(..., description="according to the file suffix, the new file name should be like this: filename-new_file_mark.file_suffix")    

class AutoCoderArgs(pydantic.BaseModel):
    source_dir: Optional[str] = pydantic.Field(..., description="Path to the project")
    git_url: Optional[str] = pydantic.Field(None, description="URL of the git repository")
    target_file: Optional[str] = pydantic.Field(None, description="the file to write the source code to")
    query: Optional[str] = pydantic.Field(None, description="the instruction to handle the source code")
    template: str = pydantic.Field("common", description="the instruction to handle the source code")
    project_type: str = pydantic.Field("py", description="the type of the project. py, ts, py-script, translate, or file suffix. default is py")
    execute: bool = pydantic.Field(False, description="Execute command line or not")
    package_name: str = pydantic.Field("", description="only works for py-script project type. The package name of the script. default is empty.")
    script_path: str = pydantic.Field("", description="only works for py-script project type. The path to the Python script. default is empty.")
    model: str = pydantic.Field("", description="the model name to use")


def is_likely_useful_file(file_path):
    """Determine if the file is likely to be useful by excluding certain directories and specific file types."""
    excluded_dirs = ["docs", "examples", "tests", "test", "__pycache__", "scripts", "benchmarks"]
    utility_or_config_files = ["hubconf.py", "setup.py"]
    github_workflow_or_docs = ["stale.py", "gen-card-", "write_model_card"]
    
    if any(part.startswith('.') for part in file_path.split('/')):
        return False
    if 'test' in file_path.lower():
        return False
    for excluded_dir in excluded_dirs:
        if f"/{excluded_dir}/" in file_path or file_path.startswith(excluded_dir + "/"):
            return False
    for file_name in utility_or_config_files:
        if file_name in file_path:
            return False
    for doc_file in github_workflow_or_docs:
        if doc_file in file_path:
            return False
    return True

def is_test_file(file_content):
    """Determine if the file content suggests it is a test file."""
    test_indicators = ["import unittest", "import pytest", "from unittest", "from pytest"]
    return any(indicator in file_content for indicator in test_indicators)

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
