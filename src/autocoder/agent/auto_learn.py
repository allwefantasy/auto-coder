from typing import Generator, List, Dict, Union, Tuple, Optional
import os
import byzerllm
import pydantic
import git
from rich.console import Console
from autocoder.common.printer import Printer
from autocoder.common import AutoCoderArgs
from autocoder.common.utils_code_auto_generate import stream_chat_with_continue
from autocoder.common import SourceCode, SourceCodeList
from autocoder.common.action_yml_file_manager import ActionYmlFileManager


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
    def analyze_commit(self,
                       querie_with_urls_and_changes: List[Tuple[str, List[str], Dict[str, Tuple[str, str]]]],                       
                       new_query:str,            
                       ) -> str:
        """
        作为高级软件工程师，请对提供的代码提交变更进行深入分析，提取具有通用价值的功能模式和设计模式，转化为可在其他项目中复用的代码规则（rules）。

        ## 任务目标
        - 识别代码变更中具有普遍应用价值的功能点和模式
        - 将这些功能点提炼为结构化规则，便于在其他项目中快速复用
        - 生成清晰的使用示例，包含完整依赖和调用方式
        - 这些规则将被存储在项目的 {{ project_root }}/.autocoderrules 目录，供后续自动化代码生成使用        

        ## 分析对象        
        下面是本次提交的代码变更：
        <changes>
        {% for query,urls,changes in querie_with_urls_and_changes %}
        ## 原始的任务需求
        {{ query }}

        修改的文件:
        {% for url in urls %}
        - {{ url }}
        {% endfor %}

        代码变更:
        {% for file_path, (before, after) in changes.items() %}
        ##File: {{ file_path }}
        ##修改前:

        {{ before or "New file" }}        

        ##File: {{ file_path }}
        ##修改后:

        {{ after or "File deleted" }}

        {% endfor %}
        {% endfor %}
        </changes>

        {% if index_file_content %}
        ## 现有索引内容
        index.md 当前内容:        
        <files>  
        <file>
        ##File: 
        {{ index_file_content }}      
        </file>
        </files>
        {% endif %}

        ## 用户需求
        {{ new_query }}

        ## 生成或者更新的规则文件结构

            ---
            description: [简明描述规则的功能，20字以内]
            globs: [匹配应用此规则的文件路径，如"src/services/*.py"]
            alwaysApply: [是否总是应用，通常为false]
            ---

            # [规则主标题]

            ## 简要说明
            [该规则的功能、适用场景和价值，100字以内]

            ## 典型用法
            ```python
            # 完整的代码示例，包含:
            # 1. 必要的import语句
            # 2. 类/函数定义
            # 3. 参数说明
            # 4. 调用方式
            # 5. 关键注释        
            ```

            ## 依赖说明
            - [必要的依赖库及版本]
            - [环境要求]
            - [初始化流程(如有)]

            ## 学习来源
            [从哪个提交变更的哪部分代码中提取的该功能点]                

        ## 生成或者更新的规则文件示例
        
            ---
            description: Git提交分析工具
            globs: "src/utils/git_analyzer.py"
            alwaysApply: false
            ---

            # Git提交分析工具

            ## 简要说明
            提供从Git仓库中获取提交变更并分析差异的工具函数，支持首次提交和普通提交的差异获取，适用于代码审查、变更追踪和自动化分析场景。

            ## 典型用法
            ```python
            import git
            from typing import Dict, Tuple, List, Optional

            def get_commit_changes(repo_path: str, commit_id: str) -> Dict[str, Tuple[Optional[str], Optional[str]]]:
                '''
                获取指定commit的文件变更内容

                Args:
                    repo_path: Git仓库路径
                    commit_id: 提交ID

                Returns:
                    Dict[str, Tuple[Optional[str], Optional[str]]]: 文件路径到(变更前内容,变更后内容)的映射
                '''
                changes = {}
                try:
                    repo = git.Repo(repo_path)
                    commit = repo.commit(commit_id)

                    # 检查是否是首次提交（没有父提交）
                    if not commit.parents:
                        # 首次提交，获取所有文件
                        for item in commit.tree.traverse():
                            if item.type == 'blob':  # 只处理文件，不处理目录
                                file_path = item.path
                                # 首次提交前没有内容
                                before_content = None
                                # 获取提交后的内容
                                after_content = repo.git.show(f"{commit.hexsha}:{file_path}")
                                changes[file_path] = (before_content, after_content)
                    else:
                        # 获取parent commit
                        parent = commit.parents[0]
                        # 获取变更的文件列表
                        for diff_item in parent.diff(commit):
                            file_path = diff_item.a_path if diff_item.a_path else diff_item.b_path

                            # 获取变更前内容
                            before_content = None
                            try:
                                if diff_item.a_blob:
                                    before_content = repo.git.show(f"{parent.hexsha}:{file_path}")
                            except git.exc.GitCommandError:
                                pass  # 文件可能是新增的

                            # 获取变更后内容
                            after_content = None
                            try:
                                if diff_item.b_blob:
                                    after_content = repo.git.show(f"{commit.hexsha}:{file_path}")
                            except git.exc.GitCommandError:
                                pass  # 文件可能被删除

                            changes[file_path] = (before_content, after_content)

                    return changes
                except Exception as e:
                    print(f"获取提交变更时出错: {str(e)}")
                    return {}
            ```

            ## 依赖说明
            - GitPython>=3.1.0
            - Python>=3.7

            ## 学习来源
            从代码提交变更中提取的Git仓库差异分析功能        

        ## 索引文件更新说明

        除了生成规则文件外，请务必更新index.md索引文件，记录所有规则及其作用。如果 index.md 当前内容为空，请按如下格式创建:
              
        # Rules索引

        本文档记录项目中所有可用的代码规则(rules)及其用途。

        ## [规则文件路径]
        [规则文件的主要功能和适用场景简述]    

        ## 评价标准
        - 提取的功能点必须具备独立价值，能在其他项目中实际复用
        - 代码示例必须完整、可执行，包含所有必要组件
        - 文档结构清晰，遵循规定格式
        - 依赖说明明确具体，便于用户快速配置环境

        请根据要求生成或者更新规则文件(markdown文件)，并将规则文件存储在项目的 {{ project_root }}/.autocoderrules 目录，供后续自动化代码生成使用。
        """
        return {
            "project_root": os.path.abspath(self.args.source_dir),
            "index_file_content": self._get_index_file_content()
        }

    @byzerllm.prompt()
    def analyze_modules(self, sources: SourceCodeList, query: str) -> str:
        """
        作为高级软件工程师，请对提供的模块代码进行深入分析，提取具有通用价值的功能模式和设计模式，转化为可在其他项目中复用的代码规则（rules）。

        ## 任务目标
        - 识别代码中具有普遍应用价值的功能点和模式
        - 将这些功能点提炼为结构化规则，便于在其他项目中快速复用
        - 生成清晰的使用示例，包含完整依赖和调用方式
        - 这些规则将被存储在项目的 {{ project_root }}/.autocoderrules 目录，供后续自动化代码生成使用

        项目根目录: {{ project_root }}

        ## 分析对象                
        {% if sources.sources %}
        分析目标文件:
        {% for source in sources.sources %}
        - {{ source.module_name }}
        {% endfor %}
        {% else %}
        前面提供的文件。
        {% endif %}

        {% if sources.sources %}
        ## 源代码内容
        <files>
        {% for source in sources.sources %}
        ##File: {{ source.module_name }}        
        {{ source.source_code }}        
        {% endfor %}
        </files>
        {% endif %}

        {% if index_file_content %}
        ## 现有索引内容
        index.md 当前内容:        
        <files>  
        <file>
        ##File: 
        {{ index_file_content }}      
        </file>
        </files>
        {% endif %}

        ## 用户需求
        {{ query }}

        ## 生成或者更新的规则文件结构
        
            ---
            description: [简明描述规则的功能，20字以内]
            globs: [匹配应用此规则的文件路径，如"src/services/*.py"]
            alwaysApply: [是否总是应用，通常为false]
            ---

            # [规则主标题]

            ## 简要说明
            [该规则的功能、适用场景和价值，100字以内]

            ## 典型用法
            ```python
            # 完整的代码示例，包含:
            # 1. 必要的import语句
            # 2. 类/函数定义
            # 3. 参数说明
            # 4. 调用方式
            # 5. 关键注释        

            ## 依赖说明
            - [必要的依赖库及版本]
            - [环境要求]
            - [初始化流程(如有)]

            ## 学习来源
            [从哪个模块的哪部分代码中提取的该功能点]
            </markdown>        

        ## 生成或者更新的规则文件示例
        
            ---
            description: RPC服务模板
            globs: "src/services/rpc_service.py"
            alwaysApply: false
            ---

            # RPC服务快速实现模板

            ## 简要说明
            提供gRPC服务端与客户端的标准实现模板，包含服务定义、请求处理、错误处理和客户端调用。适用于需要高性能RPC通信的微服务架构。

            ## 典型用法
            ```python
            # 服务端实现
            import grpc
            from concurrent import futures
            import logging
            import time
            from typing import Dict, Any

            import service_pb2
            import service_pb2_grpc

            class ServiceImplementation(service_pb2_grpc.MyServiceServicer):
                def __init__(self, config: Dict[str, Any] = None):
                    self.config = config or {}
                    logging.info("RPC服务初始化完成")

                def ProcessRequest(self, request, context):                
                    try:
                        # 业务逻辑处理
                        result = self._process_business_logic(request)

                        # 构建响应
                        return service_pb2.Response(
                            status=200,
                            message="处理成功",
                            data=result
                        )
                    except Exception as e:
                        logging.error(f"处理请求时发生错误: {str(e)}")
                        context.set_code(grpc.StatusCode.INTERNAL)
                        context.set_details(f"服务器内部错误: {str(e)}")
                        return service_pb2.Response(
                            status=500,
                            message=f"处理失败: {str(e)}",
                            data={}
                        )

                def _process_business_logic(self, request):
                    # 实际业务逻辑处理
                    return {"result": request.param1 + request.param2}

            def serve(port=50051, max_workers=10):            
                server = grpc.server(futures.ThreadPoolExecutor(max_workers=max_workers))
                service_pb2_grpc.add_MyServiceServicer_to_server(
                    ServiceImplementation(), server
                )
                server.add_insecure_port(f'[::]:{port}')
                server.start()
                logging.info(f"服务已启动，监听端口: {port}")

                try:
                    while True:
                        time.sleep(86400)  # 一天
                except KeyboardInterrupt:
                    server.stop(0)
                    logging.info("服务已停止")

            if __name__ == '__main__':
                logging.basicConfig(level=logging.INFO)
                serve()
            ```

            ## 依赖说明
            - 需要安装 grpcio>=1.44.0 和 grpcio-tools>=1.44.0
            - 需要预先定义proto文件并生成对应Python代码:
            ```bash
            python -m grpc_tools.protoc -I./protos --python_out=. --grpc_python_out=. ./protos/service.proto
            ```
            - 示例proto文件结构:
            ```protobuf
            syntax = "proto3";

            service MyService {
                rpc ProcessRequest (Request) returns (Response) {}
            }

            message Request {
                int32 param1 = 1;
                int32 param2 = 2;
            }

            message Response {
                int32 status = 1;
                string message = 2;
                map<string, string> data = 3;
            }
            ```

            ## 学习来源
            从src/services/rpc_service.py模块中的Server类和RequestHandler实现提取        

        ## 索引文件更新说明

        除了生成规则文件外，请务必更新index.md索引文件，记录所有规则及其作用。如果 index.md 当前内容为空，请按如下格式创建:
               
        # Rules索引

        本文档记录项目中所有可用的代码规则(rules)及其用途。

        ## [规则文件路径]
        [规则文件的主要功能和适用场景简述]    

        ## 评价标准
        - 提取的功能点必须具备独立价值，能在其他项目中实际复用
        - 代码示例必须完整、可执行，包含所有必要组件
        - 文档结构清晰，遵循规定格式
        - 依赖说明明确具体，便于用户快速配置环境

        请根据要求生成或者更新规则文件(markdown文件)，并将规则文件存储在项目的 {{ project_root }}/.autocoderrules 目录，供后续自动化代码生成使用。
        """

        # 获取索引文件内容
        index_file_content = self._get_index_file_content()

        return {
            "project_root": os.path.abspath(self.args.source_dir),
            "index_file_content": index_file_content
        }

    def get_commit_changes(self, commit_id: str) -> Tuple[List[Tuple[str, List[str], Dict[str, Tuple[str, str]]]], Optional[str]]:
        """
        直接从Git仓库获取指定commit的变更

        Args:
            commit_id: Git commit的ID

        Returns:
            List[Tuple[str, List[str], Dict[str, Tuple[str, str]]]]: 包含查询、URL和变更信息的列表
        """
        printer = Printer()
        querie_with_urls_and_changes = []
        try:
            repo = git.Repo(self.args.source_dir)
            commit = repo.commit(commit_id)
            modified_files = []
            changes = {}

            # 检查是否是首次提交（没有父提交）
            if not commit.parents:
                # 首次提交，获取所有文件
                for item in commit.tree.traverse():
                    if item.type == 'blob':  # 只处理文件，不处理目录
                        file_path = item.path
                        modified_files.append(file_path)
                        # 首次提交前没有内容
                        before_content = None
                        # 获取提交后的内容
                        after_content = repo.git.show(
                            f"{commit.hexsha}:{file_path}")
                        changes[file_path] = (before_content, after_content)
            else:
                # 获取parent commit
                parent = commit.parents[0]
                # 获取变更的文件列表
                for diff_item in parent.diff(commit):
                    file_path = diff_item.a_path if diff_item.a_path else diff_item.b_path
                    modified_files.append(file_path)

                    # 获取变更前内容
                    before_content = None
                    try:
                        if diff_item.a_blob:
                            before_content = repo.git.show(
                                f"{parent.hexsha}:{file_path}")
                    except git.exc.GitCommandError:
                        pass  # 文件可能是新增的

                    # 获取变更后内容
                    after_content = None
                    try:
                        if diff_item.b_blob:
                            after_content = repo.git.show(
                                f"{commit.hexsha}:{file_path}")
                    except git.exc.GitCommandError:
                        pass  # 文件可能被删除

                    changes[file_path] = (before_content, after_content)

            # 使用commit消息作为查询内容
            query = commit.message
            querie_with_urls_and_changes.append(
                (query, modified_files, changes))

        except git.exc.GitCommandError as e:
            printer.print_in_terminal(
                "git_command_error", style="red", error=str(e))
        except Exception as e:
            printer.print_in_terminal(
                "get_commit_changes_error", style="red", error=str(e))

        return querie_with_urls_and_changes, None

    def analyze_commit_changes(self, query: str, commit_id: str, conversations: List[Dict] = []) -> Optional[Generator[str, None, None]]:
        """
        分析指定commit的代码变更

        Args:
            query: 用户的查询/要求
            commit_id: 指定的commit ID
            conversations: 之前的对话历史 (可选)

        Returns:
            Optional[Generator]: 分析结果生成器，如果出错则返回None
        """
        printer = Printer()

        # 获取commit的变更信息
        changes, _ = self.get_commit_changes(commit_id)

        if not changes:
            printer.print_in_terminal("no_commit_changes", style="red")
            return None

        # 调用LLM进行代码分析
        try:
            # 获取prompt内容
            prompt_content = self.analyze_commit.prompt(
                querie_with_urls_and_changes=changes,
                new_query=query
            )

            # 准备对话历史
            if conversations:
                new_conversations = conversations[:-1]
            else:
                new_conversations = []
            new_conversations.append(
                {"role": "user", "content": prompt_content})

            # 调用LLM
            v = stream_chat_with_continue(
                llm=self.llm,
                conversations=new_conversations,
                llm_config={},
                args=self.args
            )
            return v
        except Exception as e:
            printer.print_in_terminal(
                "commit_analysis_error", style="red", error=str(e))
            return None

    def _get_index_file_content(self) -> str:
        """获取索引文件内容"""
        index_file_path = os.path.join(os.path.abspath(
            self.args.source_dir), ".autocoderrules", "index.md")
        index_file_content = ""

        try:
            if os.path.exists(index_file_path):
                with open(index_file_path, 'r', encoding='utf-8') as f:
                    index_file_content = f.read()
        except Exception as e:
            self.printer.print_str_in_terminal(
                f"读取索引文件时出错: {str(e)}", style="yellow")

        return index_file_content

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
