from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from autocoder.index.index import IndexManager
from autocoder.pyproject import PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs,SourceCode
from autocoder.rag.simple_rag import SimpleRAG
from byzerllm.apps.llama_index.byzerai import ByzerAI
from loguru import logger
import os
import byzerllm
import yaml


@byzerllm.prompt()
def context():
    """
    你的目标是帮助用户阅读和理解一个项目。    
    """


def get_tools(args: AutoCoderArgs, llm: byzerllm.ByzerLLM):
    def get_project_related_files(query: str) -> str:
        """
        该工具会根据查询描述，返回项目中与查询相关的文件。
        返回文件路径列表。
        """
        if args.project_type == "ts":
            pp = TSProject(args=args, llm=llm)
        elif args.project_type == "py":
            pp = PyProject(args=args, llm=llm)
        else:
            pp = SuffixProject(args=args, llm=llm, file_filter=None)
        pp.run()
        sources = pp.sources

        index_manager = IndexManager(llm=llm, sources=sources, args=args)
        target_files = index_manager.get_target_files_by_query(query)
        file_list = target_files.file_list
        return ",".join([file.file_path for file in file_list])
    
    def get_project_map()->str:
        """
        该工具会返回项目中所有文件以及文件的信息，诸如该文件的用途，导入的包，定义的类，函数，变量等信息。
        """
        if args.project_type == "ts":
            pp = TSProject(args=args, llm=llm)
        elif args.project_type == "py":
            pp = PyProject(args=args, llm=llm)
        else:
            pp = SuffixProject(args=args, llm=llm, file_filter=None)
        pp.run()
        sources = pp.sources

        index_manager = IndexManager(llm=llm, sources=sources, args=args)        
        return index_manager.read_index_as_str()    
    
    def read_source_codes(paths:str)->str:
        '''
        你可以通过使用该工具获取相关文件的源代码。
        输入参数 paths: 逗号分隔的文件路径列表,需要是绝对路径
        返回值是文件的源代码。
        
        注意，paths数量务必不要太多，否则内容会太多，推荐输入最相关的2-3个文件来进行阅读。
        '''
        paths = [p.strip() for p in paths.split(",")]
        source_code_str = ""
        for path in paths:
            with open(path, "r") as f:
                source_code = f.read()
                sc = SourceCode(module_name=path, source_code=source_code)
                source_code_str += f"##File: {sc.module_name}\n"
                source_code_str += f"{sc.source_code}\n\n"

        return source_code_str

    
    tools = [
        FunctionTool.from_defaults(get_project_related_files),
        FunctionTool.from_defaults(get_project_map),        
        FunctionTool.from_defaults(read_source_codes)
    ]
    return tools


class ProjectReader:
    def __init__(self, args: AutoCoderArgs, llm: byzerllm.ByzerLLM):
        self.llm = llm
        if args.planner_model:
            self.llm = self.llm.get_sub_client("planner_model")
        self.args = args
        self.tools = get_tools(args=args, llm=llm)    

    def run(self, query: str, max_iterations: int = 10):
        agent = ReActAgent.from_tools(
            tools=self.tools,
            llm=ByzerAI(llm=self.llm),
            verbose=True,
            max_iterations=max_iterations,
            context=context.prompt(),
        )
        r = agent.chat(message=query)
        return r.response
