from llama_index.core.agent import ReActAgent
from llama_index.core.tools import FunctionTool
from autocoder.index.index import IndexManager
from autocoder.pyproject import PyProject
from autocoder.tsproject import TSProject
from autocoder.suffixproject import SuffixProject
from autocoder.common import AutoCoderArgs
from autocoder.rag.simple_rag import SimpleRAG
from byzerllm.apps.llama_index.byzerai import ByzerAI
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

    auto-coder 会自动完成后续的代码修改工作。
    
    你的目标是根据用户的问题，生成一个或者多个 yaml 配置文件。

    下面是 auto-coder 的基本配置：

    ```
    query: |
      关注 byzerllm_client.py,command_args.py,common/__init__.py  等几个文件，
      添加一个 byzerllm agent 命令
    ```

    以上面为模板，根据需要修改 query 字段即可。

    注意，用户的需求往往是一个目标描述，请按如下思路思索问题：

    1. 你总是需要找到当前问题需要涉及到的文件。注意，你需要对问题进行理解，然后转换成一个查询。比如用户说：我想增加一个 agent命令。那我们的查询应该是："项目的命令行入口相关文件"
    2. 如果在生成的过程中遇到 yaml 配置相关的问题，可以查阅 auto-coder 的相关知识。
    3. 生成 auto-coder 的 yaml 配置文件，
        
        通常 auto-coder YAML 文件的 query 要覆盖以下几个方面：

        1. 需要修改的文件是什么
        2. 修改逻辑是什么
        3. 具体的修改范例是什么（可选）

        这里也需要对用户的问题进行转换，将前面我们得到的文件和改写后的问题合并到一起作为 yaml 中的query。
        比如用户说：我想增加一个 agent命令，此时将yaml中的 query 比较合适的是： "关注byzerllm.py文件，添加一个 byzerllm agent 命令"，
        这样 auto-coder 就知道应该修改哪些文件，以及怎么修改，满足我们前面的要求。

    如果用户的问题比较复杂，你可能需要拆解成多个步骤，每个步骤生成一个对应一个 yaml 配置文件。
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
            f
            for f in os.listdir(actions_dir)
            if f[:3].isdigit() and f.endswith(".yml") and f[:3] != "101"
        ]
        if not action_files:
            max_seq = 0
        else:
            seqs = [int(f[:3]) for f in action_files]
            max_seq = max(seqs)

        new_seq = str(max_seq + 1).zfill(3)
        prev_files = [f for f in action_files if int(f[:3]) < int(new_seq)]

        if not prev_files:
            new_file = os.path.join(actions_dir, f"{new_seq}_{yaml_file_name}.yml")
            with open(new_file, "w") as f:
                pass
        else:
            prev_file = sorted(prev_files)[-1]  # 取序号最大的文件
            with open(os.path.join(actions_dir, prev_file), "r") as f:
                content = f.read()

            yaml_content = yaml.safe_load(content)
            if yaml_content is None:
                raise Exception("The previous yaml file is empty. Please check it.")
            
            new_temp_yaml_content = yaml.load(yaml_str)
            
            for k, v in new_temp_yaml_content.items():
                yaml_content[k] = v             

            new_content = yaml.safe_dump(yaml_content, encoding='utf-8',allow_unicode=True).decode('utf-8')
            new_file = os.path.join(actions_dir, f"{new_seq}_{yaml_file_name}.yml")
            with open(new_file, "w") as f:
                f.write(new_content)

        return new_file

    def get_auto_coder_knowledge(query: str):
        """
        你可以通过使用该工具来获得 auto-coder 相关问题的回答。
        返回相关的知识文本。
        """
        rag = SimpleRAG(llm=llm, args=args, path="")
        source_codes = rag.search(query)
        return "\n".join([sc.source_code for sc in source_codes])

    tools = [
        FunctionTool.from_defaults(get_project_related_files),
        FunctionTool.from_defaults(generate_auto_coder_yaml),
        FunctionTool.from_defaults(get_auto_coder_knowledge),
    ]
    return tools


class Planner:
    def __init__(self, args: AutoCoderArgs, llm: byzerllm.ByzerLLM):
        self.llm = llm
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
