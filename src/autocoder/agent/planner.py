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
    auto-coder 是一个命令行 + YAML 配置文件的工具，用于阅读和生成代码。

    下面是 auto-coder 的基本配置：

    ```
    query: |
      关注 byzerllm_client.py,command_args.py,common/__init__.py  等几个文件，
      添加一个 byzerllm agent 命令
    ```

    生成时，以上面为模板，根据需要修改 query 字段即可。

    用户的需求往往是一个目标描述。比如，我想实现 byzerllm agent 命令。
    对应到项目里，我们需要将其转化实现逻辑，通常你可以按照下面的方式进行思考：

    1. 我需要能够找到项目中和用户命令行功能相关的文件，为了能够找到相关的文件，我需要将 query 转换成 "从目录结构以及源码描述中找到项目的命令行入口相关的文件"。假设此时找到了 byzerllm.py 为命令行相关的文件。
    2. 如果在生成的过程中遇到 yaml 配置相关的问题，可以查阅 auto-coder 的相关知识。
    3. 生成 auto-coder 的 yaml 配置文件，
        通常 auto-coder YAML 文件的query 要覆盖以下几个方面：

        1. 需要修改的文件是什么
        2. 修改逻辑是什么
        3. 具体的修改范例是什么（可选）

        所以我们将yaml中的query 要转换成： "关注byzerllm.py文件，添加一个 byzerllm agent 命令"，
        这样 auto-coder 就知道应该修改哪些文件，以及怎么修改。

    我们提供了相关的工具，你可以使用这些工具并且按照上面的大致思路来解决问题。
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
        return "\n".join([file.file_path for file in file_list])

    def generate_auto_coder_yaml(yaml_file_name: str, yaml_str: str) -> str:
        """
        该工具主要用于生成 auto-coder yaml 配置文件。
        返回生成的 yaml 文件路径。
        """
        actions_dir = os.path.join(os.getcwd(), "actions")
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

            yaml_content = yaml.load(content)
            yaml_content["query"] = yaml_str
            new_content = yaml.dump(yaml_content)
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
