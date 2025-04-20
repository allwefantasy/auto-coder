from typing import Generator, List, Dict, Union, Tuple, Optional
import os
import byzerllm
import pydantic
from rich.console import Console
from autocoder.common.printer import Printer
from autocoder.common import AutoCoderArgs
from autocoder.common.utils_code_auto_generate import stream_chat_with_continue
from autocoder.common import SourceCode, SourceCodeList


class AutoLearn:
    def __init__(self, llm: Union[byzerllm.ByzerLLM, byzerllm.SimpleByzerLLM],
                 args: AutoCoderArgs,
                 console: Optional[Console] = None):
        """
        初始化 AutoLearn

        Args:
            llm: ByzerLLM 实例，用于代码分析和学习
            args: AutoCoderArgs 实例，包含配置信息
            console: Rich Console 实例，用于输出
        """
        self.llm = llm
        self.args = args
        self.console = console or Console()
        self.printer = Printer()

    @byzerllm.prompt()
    def analyze_modules(self, sources: SourceCodeList, query: str) -> str:
        """
        你作为一名高级软件工程师，对以下模块进行分析，总结出其中具有通用价值、可在其他场景下复用的功能点，并给出每个功能点的典型用法示例（代码片段）。每个示例需包含必要的 import、初始化、参数说明及调用方式，便于他人在不同项目中快速上手复用。
        通常而言，这些流程会成为 rules 放到当前项目的 .autocoderrules 目录下。        

        项目根目录:
        {{ project_root }}

        分析目标模块路径：
        {% for source in sources.sources %}
        - {{ source.module_name }}
        {% endfor %}

        下面是这些模块的内容：
        <files>
        {% for source in sources.sources %}
        ##File: {{ source.module_name }}        
        {{ source.source_code }}        
        {% endfor %}
        </files>

        {% if index_file_content %}
        index.md 当前内容如下：        
        <files>  
        <file>
        ##File: 
        {{ index_file_content }}      
        </file>
        </files>
        {% endif %}
        
        用户的具体要求是：
        {{ query }}

        请按照如下格式输出：

        首先是文件头，包含简要描述，相关文件，以及是否每次都会被应用读取。
        ---
        description: RPC Service boilerplate
        globs: "src/services/rpc_service.py"
        alwaysApply: false
        ---
        接下来是功能点列表，每个功能点包含名称、简要说明、典型用法、依赖说明、学习来源。
        
        # 功能点名称
       （例如：自动 Commit Review）
        ## 简要说明
        <该功能点的作用、适用场景>
        ## 典型用法
        ```python
        # 代码片段，包含 import、初始化、参数说明和调用方法
        ```
        ## 依赖说明
        <如有特殊依赖或初始化要求，需说明>
        ## 学习来源
        <从哪个文件的那部分代码学习到的>

        下面是一个简单的示例:

        <markdown>
        ---
        description: RPC Service boilerplate
        globs: "src/services/rpc_service.py"
        alwaysApply: false
        ---

        # RPC Service boilerplate
        
        ## 简要说明
        快速生成RPC服务基础代码模板，包含服务定义、处理器实现和客户端调用代码。适用于需要构建新的微服务或API服务时快速搭建框架。
        
        ## 典型用法
        ```python
        # 服务端定义
        import grpc
        from concurrent import futures
        import service_pb2
        import service_pb2_grpc
        
        class MyServiceHandler(service_pb2_grpc.MyServiceServicer):
            def ProcessRequest(self, request, context):
                # 处理请求逻辑
                response = service_pb2.Response(
                    status=200,
                    message="成功处理请求",
                    data={"result": request.param1 + request.param2}
                )
                return response
                
        def serve():
            server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
            service_pb2_grpc.add_MyServiceServicer_to_server(MyServiceHandler(), server)
            server.add_insecure_port('[::]:50051')
            server.start()
            server.wait_for_termination()
            
        if __name__ == '__main__':
            serve()
        ```
        
        ## 依赖说明
        - 需要安装grpcio和grpcio-tools包
        - 需要先生成proto文件对应的Python代码：`python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. ./protos/service.proto`
        
        ## 学习来源
        从项目中的src/services/rpc_service.py文件中的服务实现部分学习而来
        </markdown>

        请覆盖所有具有独立复用价值的功能点，避免遗漏。输出内容务必简明、准确、易于迁移和复用。

        注意： 无论是新建还是修改 rules 文件，请务必更新 index.md 文件。该文件记录了所有 rules 文件的列表，以及每个 rules 文件的作用。
        如果 index.md 文件内容为空，则按<markdown></markdown> 包裹的格式生成：
        <markdown>        
        # <rules 文件路径>
        ## 作用
        <rules 文件的作用>        
        </markdown>
        """

        return {
            "project_root": os.path.abspath(self.args.source_dir),
            "index_file_content": ""
        }

    def analyze(self, sources: SourceCodeList, query: str, conversations: List[Dict] = []) -> Optional[Generator[str, None, None]]:
        """
        分析给定的模块文件，根据用户需求生成可复用功能点的总结。

        Args:
            sources: 包含模块路径和内容的 SourceCodeList 对象。
            query: 用户的具体分析要求。
            conversations: 之前的对话历史 (可选)。

        Returns:
            Optional[Generator]: LLM 返回的分析结果生成器，如果出错则返回 None。
        """
        if not sources or not sources.sources:
            self.printer.print_str_in_terminal("没有提供有效的模块文件进行分析。", style="red")
            return None

        try:
            # 准备 Prompt
            prompt_content = self.analyze_modules.prompt(
                sources=sources,
                query=query
            )

            # 准备对话历史
            # 如果提供了 conversations，我们假设最后一个是用户的原始查询，替换它
            if conversations:
                new_conversations = conversations[:-1]
            else:
                new_conversations = []
            new_conversations.append(
                {"role": "user", "content": prompt_content})

            # 调用 LLM
            v = stream_chat_with_continue(
                llm=self.llm,
                conversations=new_conversations,
                llm_config={},
                args=self.args
            )
            return v
        except Exception as e:
            self.printer.print_in_terminal(
                "代码分析时出错", style="red", error=str(e))
            return None
