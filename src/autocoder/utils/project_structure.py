from autocoder.pyproject import PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs
import byzerllm
from typing import Union

def get_project_structure(args:AutoCoderArgs, llm:Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM]):
    if args.project_type == "ts":
        pp = TSProject(args=args, llm=llm)
    elif args.project_type == "py":
        pp = PyProject(args=args, llm=llm)
    else:
        pp = SuffixProject(args=args, llm=llm, file_filter=None)
    return pp.get_tree_like_directory_structure()