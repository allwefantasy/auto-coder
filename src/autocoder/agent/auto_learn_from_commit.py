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
from autocoder.common.action_yml_file_manager import ActionYmlFileManager
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
        self.args = args
        self.actions_dir = os.path.join(args.source_dir, "actions")
        self.llm = llm        
        self.skip_diff = skip_diff
        self.console = console or Console()
        self.action_manager = ActionYmlFileManager(args.source_dir)

    @byzerllm.prompt()
    def learn(self, querie_with_urls_and_changes: List[Tuple[str, List[str], Dict[str, Tuple[str, str]]]], query: str) -> Generator[str,None,None]:
        """        
        下面是触发这次代码变更的原始任务需求：
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
        
        你的目标是，总结出这次修改重现步骤，要尽可能详细，达到当用户重新提交相同的需求，系统可以根据你这个流程，可以重新实现这一次修改。
        
        在描述中，如果涉及到文件请用如下示例的格式：        
        @src/autocoder/utils/_markitdown.py
        如果涉及到符号，比如函数名，变量名，类名等等，请用如下示例的格式：
        @@DocxConverter(location: src/autocoder/utils/_markitdown.py) 

        """
        pass

    def parse_history_tasks(self, commit_file_name: Optional[str] = None) -> List[Dict]:
        """
        解析历史任务信息

        Returns:
            List[Dict]: 每个字典包含一个历史任务的信息
        """
        # 使用 ActionManager 获取文件
        if commit_file_name:
            action_file = commit_file_name
        else:
            action_file = self.action_manager.get_latest_action_file()
            if not action_file:
                return []

        querie_with_urls_and_changes = []
        repo = git.Repo(self.project_dir)

        # 收集所有query、urls和对应的文件变化
        yaml_content = self.action_manager.load_yaml_content(action_file)
        
        if not yaml_content:
            return []

        query = yaml_content.get('query', '')
        urls = yaml_content.get('urls', [])

        if query:
            changes = {}
            if not self.skip_diff:
                # 使用 ActionManager 获取 commit ID
                commit_id = self.action_manager.get_commit_id_from_file(action_file)
                commit = repo.commit(commit_id)                
                if commit and commit.parents:
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

            querie_with_urls_and_changes.append((query, urls, changes))

        return querie_with_urls_and_changes,action_file
    
    def get_commit_changes(self, commit_id: str) -> List[Tuple[str, List[str], Dict[str, Tuple[str, str]]]]:
        """
        直接从Git仓库获取指定commit的变更

        Args:
            commit_id: Git commit的ID

        Returns:
            List[Tuple[str, List[str], Dict[str, Tuple[str, str]]]]: 与parse_history_tasks格式相同的结果
        """
        printer = Printer()
        querie_with_urls_and_changes = []
        changes = {}
        modified_files = []
        query = f"Review commit: {commit_id}"

        try:
            repo = git.Repo(self.project_dir)
            commit = repo.commit(commit_id)
            
            if not commit.parents:
                # 这是首次提交
                printer.print_in_terminal("commit_is_initial", style="yellow", commit_id=commit_id)
                # 获取首次提交的所有文件
                for item in commit.tree.traverse():
                    if item.type == 'blob':  # 只处理文件，不处理目录
                        file_path = item.path
                        modified_files.append(file_path)
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
                    modified_files.append(file_path)
                    
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
            
            # 使用commit消息作为查询内容
            query = commit.message
            querie_with_urls_and_changes.append((query, modified_files, changes))
            
        except git.exc.GitCommandError as e:
            printer.print_in_terminal("git_command_error", style="red", error=str(e))
        except Exception as e:
            printer.print_in_terminal("get_commit_changes_error", style="red", error=str(e))
            
        return querie_with_urls_and_changes,None

    def learn_from_commit(self,query: str, conversations: List[Dict],commit_id: Optional[str] = None) -> Generator[str,None,None]:
        """
        从最新的代码提交中学习通用模式

        Args:
            query: 用户的查询/要求
            conversations: 之前的对话历史
            commit_id: 可选的指定commit ID，如果提供则直接学习该commit

        Returns:
            Optional[Generator]: 学习结果生成器，如果出错则返回None
        """
        printer = Printer()
        commit_file_name = None
        if commit_id:
            # 使用 ActionManager 从 commit ID 获取文件名
            commit_file_name = self.action_manager.get_file_name_from_commit_id(commit_id)
            
            if not commit_file_name:
                raise ValueError(printer.get_message_from_key_with_format("no_commit_file_name", commit_id=commit_id))
        
        # 获取最新的提交信息
        changes,tmp_file_name = self.parse_history_tasks(commit_file_name=commit_file_name)
        commit_file_name = tmp_file_name
        if not changes:            
            printer.print_in_terminal("no_latest_commit", style="red")
            return None, None

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
                    llm_config={},
                    args=self.args
            )
            return v, commit_file_name
        except Exception as e:            
            printer.print_in_terminal("code_learn_error", style="red", error=str(e))
            return None, commit_file_name