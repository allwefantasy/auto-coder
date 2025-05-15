from autocoder.index.index import IndexManager
from autocoder.pyproject import PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs,SourceCode
from loguru import logger
import os
import byzerllm
import yaml


@byzerllm.prompt()
def context():
    """
    
    auto-coder 是一个命令行 + YAML 配置文件编程辅助工具。
    程序员通过在 YAML 文件里撰写修改代码的逻辑，然后就可以通过下面的命令来执行：
    
    ```
    auto-file --file actions/xxxx.yml 
    ```

    下面是 auto-coder YAML 文件的一个基本配置：

    ```
    query: |
      关注 byzerllm_client.py,command_args.py,common/__init__.py  等几个文件，
      添加一个 byzerllm agent 命令
    ```
    其中 query 部分就是对如何修改代码进行的一个较为详细的描述。 有了这个描述，auto-coder 会自动完成后续的代码修改工作。
    所以 auto-coder 工具实现了代码的”设计“到”实现“。
    
    如果你希望auto-coder能够在解决问题的时候自动查找知识库，那么在YAML中新增一个配置：

    ```
    enable_rag_search: <你希望auto-coder自动查找的query>
    ```
            
    你的目标是根据用户的问题，从”需求/目标“到”设计“，生成一个或者多个 yaml 配置文件。   
    什么是"需求/目标"呢？比如用户说："我想给项目首页换个logo",这个就是需求/目标。
    什么是"设计"呢？ 比如"对当前项目里home.tsx中的logo标签进行替换，替换成 ./images/new_logo.png", 这个就是可以执行的设计。
    你的目标就是把用户的需求/目标转换成一个设计描述，然后生成一个 yaml 配置文件。

    你可以参考如下思路来完成目标：

    1. 你总是需要找到当前问题需要涉及到的文件。注意，你需要对问题进行理解，然后转换成一个查询。比如用户说：我想增加一个 agent命令。那我们的查询应该是："项目的命令行入口相关文件"
    2. 如果有必要，去查看你感兴趣的某个文件的源码。 
    3. 如果在生成的过程中遇到auto-coder yaml 配置相关的问题，可以查阅 auto-coder 的相关知识,除了这种情况，不要使用get_auto_coder_knowledge工具。
    4. 生成 auto-coder 的 yaml 配置文件。
        
    通常 auto-coder YAML 文件的 query 内容要覆盖以下几个方面：

    1. 需要修改/阅读的文件是什么
    2. 修改/阅读逻辑是什么
    3. 具体的修改/阅读范例是什么（可选）

    你需要将用户的原始问题修改成满足上面的描述。
    
    比如用户说：我想增加一个 agent命令，因为我们查找了相关文件路径，
    然后根据get_project_related_files这个工具我们知道用户的目标涉及到 byzerllm_client.py,command_args.py,common/__init__.py 等几个文件。
    通过read_source_codes查看文件源码，我们确认 command_args.py 是最合适的文件，并且获得了更详细的信息，所以我们最终将 query 改成：
    "关注command_args.py 以及它相关的文件，在里面参考 byzerllm deploy  实现一个新的命令 byzerllm agent 命令"，
    这样 auto-coder 就知道应该修改哪些文件，以及怎么修改，满足我们前面的要求。

    如果用户的问题比较复杂，你可能需要拆解成多个步骤，每个步骤生成一个对应一个 yaml 配置文件。

    最后务必需要调用 generate_auto_coder_yaml 工具生成 yaml 配置文件。
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

    def generate_auto_coder_yaml(yaml_file_name: str, yaml_str: str) -> str:
        """
        该工具主要用于生成 auto-coder yaml 配置文件。
        参数 yaml_file_name 不要带后缀名。
        返回生成的 yaml 文件路径。
        """        
        actions_dir = os.path.join(args.source_dir, "actions")
        if not os.path.exists(actions_dir):
            print("Current directory does not have an actions directory")
            return

        action_files = [
            f for f in os.listdir(actions_dir) if f[:3].isdigit() and "_" in f and f.endswith(".yml")
        ]

        def get_old_seq(name):
            return name.split("_")[0]

        if not action_files:
            max_seq = 0
        else:
            seqs = [int(get_old_seq(f)) for f in action_files]
            max_seq = max(seqs)

        new_seq = str(max_seq + 1).zfill(12)
        prev_files = [f for f in action_files if int(get_old_seq(f)) < int(new_seq)]

        if not prev_files:
            new_file = os.path.join(actions_dir, f"{new_seq}_{yaml_file_name}.yml")
            with open(new_file, "w",encoding="utf-8") as f:
                pass
        else:
            prev_file = sorted(prev_files)[-1]  # 取序号最大的文件
            with open(os.path.join(actions_dir, prev_file), "r",encoding="utf-8") as f:
                content = f.read()

            yaml_content = yaml.safe_load(content)
            if yaml_content is None:
                raise Exception("The previous yaml file is empty. Please check it.")
            
            new_temp_yaml_content = yaml.safe_load(yaml_str)            
            
            for k, v in new_temp_yaml_content.items():
                del yaml_content[k]
                         
            new_content = yaml.safe_dump(yaml_content, allow_unicode=True, default_flow_style=False)
            new_file = os.path.join(actions_dir, f"{new_seq}_{yaml_file_name}.yml")
            with open(new_file, "w",encoding="utf-8") as f:
                f.write(new_content + "\n" + yaml_str)

        return new_file
    
    def read_source_codes(paths:str)->str:
        '''
        你可以通过使用该工具获取相关文件的源代码。
        输入参数 paths: 逗号分隔的文件路径列表,需要时绝对路径
        返回值是文件的源代码    
        '''
        paths = [p.strip() for p in paths.split(",")]
        source_code_str = ""
        for path in paths:
            with open(path, "r",encoding="utf-8") as f:
                source_code = f.read()
                sc = SourceCode(module_name=path, source_code=source_code)
                source_code_str += f"##File: {sc.module_name}\n"
                source_code_str += f"{sc.source_code}\n\n"

        return source_code_str


    def get_auto_coder_knowledge(query: str):
        """
        你可以通过使用该工具来获得 auto-coder 如何使用，参数如何配置。        
        返回相关的知识文本。
        """
        old_enable_rag_search = args.enable_rag_search
        old_collections = args.collections

        if not args.enable_rag_search:
            args.enable_rag_search= True,
        if not args.collections:
            args.collections="auto-coder"  

        logger.info(f"collections: {args.collections}")
        from autocoder.rag.rag_entry import RAGFactory
        rag = RAGFactory.get_rag(llm=llm, args=args, path="")
        source_codes = rag.search(query)

        args.enable_rag_search = old_enable_rag_search
        args.collections = old_collections

        return "\n".join([sc.source_code for sc in source_codes])
        
    from llama_index.core.tools import FunctionTool
    tools = [
        FunctionTool.from_defaults(get_project_related_files),
        FunctionTool.from_defaults(generate_auto_coder_yaml),
        FunctionTool.from_defaults(get_auto_coder_knowledge),
        FunctionTool.from_defaults(read_source_codes)
    ]
    return tools


class Planner:
    def __init__(self, args: AutoCoderArgs, llm: byzerllm.ByzerLLM):
        self.llm = llm
        if args.planner_model:
            self.llm = self.llm.get_sub_client("planner_model")
        self.args = args
        self.tools = get_tools(args=args, llm=llm)    

    def run(self, query: str, max_iterations: int = 10):
        from byzerllm.apps.llama_index.byzerai import ByzerAI
        from llama_index.core.agent import ReActAgent
        agent = ReActAgent.from_tools(
            tools=self.tools,
            llm=ByzerAI(llm=self.llm),
            verbose=True,
            max_iterations=max_iterations,
            context=context.prompt(),
        )
        r = agent.chat(message=query)
        return r.response
