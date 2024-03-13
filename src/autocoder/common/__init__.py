import pydantic
import ast

class SourceCode(pydantic.BaseModel):
    module_name: str
    source_code: str


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
