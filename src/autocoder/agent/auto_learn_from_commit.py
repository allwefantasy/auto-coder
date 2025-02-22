from typing import Generator, List, Dict, Union, Tuple, Optional
import os
import yaml
import byzerllm
import pydantic
import git
from rich.console import Console
from autocoder.common.printer import Printer
from autocoder.common import AutoCoderArgs
from autocoder.common.utils_code_auto_generate import stream_chat_with_continue
import hashlib


def load_yaml_config(yaml_file: str) -> Dict:
    """加载YAML配置文件"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        printer = Printer()
        printer.print_in_terminal("yaml_load_error", style="red", yaml_file=yaml_file, error=str(e))
        return {}


class AutoLearnFromCommit:
    def __init__(self, llm: Union[byzerllm.ByzerLLM,byzerllm.SimpleByzerLLM],
                 args:AutoCoderArgs,                 
                 skip_diff: bool = False,                 
                 console: Optional[Console] = None):
        """
        初始化 AutoLearnFromCommit

        Args:
            llm: ByzerLLM 实例，用于代码学习
            project_dir: 项目根目录
            skip_diff: 是否跳过获取 diff 信息            
        """
        self.project_dir = args.source_dir
        self.actions_dir = os.path.join(args.source_dir, "actions")
        self.llm = llm        
        self.skip_diff = skip_diff
        self.console = console or Console()

    @byzerllm.prompt()
    def learn(self, querie_with_urls_and_changes: List[Tuple[str, List[str], Dict[str, Tuple[str, str]]]], query: str) -> Generator[str,None,None]:
        """
        请根据下面的代码变更，总结出通用的代码调整模式，以帮助实现类似的需求。

        下面用户对本次的目标以及你需要总结的要求：
        <goal>
        {{ query }}
        </goal>

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

        请总结以下内容：
        1. 代码调整模式：描述为了实现这个目标，通常需要对代码做出哪些通用调整
        2. 关键修改点：指出本次提交中最关键或最具代表性的修改点
        3. 潜在扩展：基于这些修改，未来类似需求可能需要进行哪些扩展
        4. 注意事项：在实现类似功能时需要注意哪些问题

        总结要求：
        1. 总结应该抽象化，不要局限于具体实现细节
        2. 对于每个模式都应该提供明确的适用场景
        3. 应该考虑代码的可维护性和可扩展性
        4. 应该指出在不同技术栈或框架下的通用性
        """
        pass

    def parse_history_tasks(self) -> List[Dict]:
        """
        解析历史任务信息

        Returns:
            List[Dict]: 每个字典包含一个历史任务的信息
        """
        # 获取所有YAML文件
        action_files = [
            f for f in os.listdir(self.actions_dir)
            if f[:3].isdigit() and "_" in f and f.endswith('.yml')
        ]

        # 按序号排序
        def get_seq(name):
            return int(name.split("_")[0])

        # 获取最新的action文件列表
        action_files = sorted(action_files, key=get_seq)
        action_files.reverse()        

        action_file = action_files[0]

        querie_with_urls_and_changes = []
        repo = git.Repo(self.project_dir)

        # 收集所有query、urls和对应的文件变化
        for yaml_file in [action_file]:
            yaml_path = os.path.join(self.actions_dir, yaml_file)
            config = load_yaml_config(yaml_path)

            if not config:
                continue

            query = config.get('query', '')
            urls = config.get('urls', [])

            if query:
                changes = {}
                if not self.skip_diff:
                    # 计算文件的MD5用于匹配commit   
                    with open(yaml_path, 'r', encoding='utf-8') as f:
                        yaml_content = f.read()                 
                        file_md5 = hashlib.md5(yaml_content.encode("utf-8")).hexdigest()
                    response_id = f"auto_coder_{yaml_file}_{file_md5}"
                    # 查找对应的commit                   
                    try:
                        for commit in repo.iter_commits():
                            if response_id in commit.message:
                                if commit.parents:
                                    parent = commit.parents[0]
                                    # 获取所有文件的前后内容
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
                                break
                    except git.exc.GitCommandError as e:
                        printer = Printer()
                        printer.print_in_terminal("git_command_error", style="red", error=str(e))
                    except Exception as e:
                        printer = Printer()
                        printer.print_in_terminal("get_commit_changes_error", style="red", error=str(e))

                querie_with_urls_and_changes.append((query, urls, changes))

        return querie_with_urls_and_changes
    

    def learn_from_commit(self,query: str, conversations: List[Dict]) -> Generator[str,None,None]:
        """
        从最新的代码提交中学习通用模式

        Returns:
            Optional[Generator]: 学习结果生成器，如果出错则返回None
        """
        printer = Printer()
        # 获取最新的提交信息
        changes = self.parse_history_tasks()
        if not changes:            
            printer.print_in_terminal("no_latest_commit", style="red")
            return None

        # 调用LLM进行代码学习
        try:
            # 获取 prompt 内容            
            query = self.learn.prompt(changes, query)
            new_conversations = conversations.copy()[0:-1]
            new_conversations.append({"role": "user", "content": query})
            # 构造对话消息            
            v = stream_chat_with_continue(
                    llm=self.llm,
                    conversations=new_conversations,
                    llm_config={}
            )
            return v
        except Exception as e:            
            printer.print_in_terminal("code_learn_error", style="red", error=str(e))
            return None