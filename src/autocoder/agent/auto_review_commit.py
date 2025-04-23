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
from autocoder.common.action_yml_file_manager import ActionYmlFileManager


def load_yaml_config(yaml_file: str) -> Dict:
    """加载YAML配置文件"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        printer = Printer()
        printer.print_in_terminal("yaml_load_error", style="red", yaml_file=yaml_file, error=str(e))
        return {}


class AutoReviewCommit:
    def __init__(self, llm: Union[byzerllm.ByzerLLM,byzerllm.SimpleByzerLLM],
                 args:AutoCoderArgs,                 
                 skip_diff: bool = False,                 
                 console: Optional[Console] = None):
        """
        初始化 AutoReviewCommit

        Args:
            llm: ByzerLLM 实例，用于代码审查
            project_dir: 项目根目录
            skip_diff: 是否跳过获取 diff 信息            
        """
        self.project_dir = args.source_dir
        self.args = args
        self.actions_dir = os.path.join(args.source_dir, "actions")
        self.llm = llm        
        self.skip_diff = skip_diff
        self.console = console or Console()
        self.action_yml_manager = ActionYmlFileManager(source_dir=args.source_dir)

    @byzerllm.prompt()
    def review(self, querie_with_urls_and_changes: List[Tuple[str, List[str], Dict[str, Tuple[str, str]]]], query: str) -> Generator[str,None,None]:
        """
        如果前面我们对话提供了文档，请参考上面的文档对提交的代码变更进行审查，提供改进建议，你所有的输出都要以markdown语法输出。

        下面包含最新一次提交的信息：        
        <commit>
        {% for query,urls,changes in querie_with_urls_and_changes %}
        ## 任务需求
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
        </commit>

        审查要求：
        1. 代码质量评估
           - 代码可读性：命名、注释、代码结构是否清晰
           - 代码风格：是否符合项目规范
           - 实现逻辑：算法和数据结构的选择是否合适
           
        2. 潜在问题检查
           - 常见错误：缩进（比如python）,闭合标签（前端vue,reactjs）,是否存在空指针，数组越界，类型转换，未声明变量,typo等低级错误
           - 安全性：是否存在安全隐患
           - 性能：是否有性能问题
           - 并发：是否有并发安全问题
           - 异常处理：错误处理是否完善
           - 资源管理：是否有资源泄露风险
           
        3. 架构合理性
           - 模块化：职责划分是否合理
           - 可扩展性：是否方便未来扩展
           - 依赖关系：组件耦合是否合理
           - 复用性：是否有重复代码

        评审结果包含以下内容
        1. issues: 发现的具体问题列表        
        3. severity: 问题的严重程度(low/medium/high)，从高到底进行描述。
        4. suggestions: 对应的改进建议列表
        4. affected_files: 受影响的文件列表
        5. summary: 总体评价
        6. action: 1. 修改完美，可以继续。 2. 用户需要revert 代码，然后重新修改提示词，你推荐的提示词是什么。 3. 用户可以在现在的基础上，再做一些迭代，来完成这次，应该怎么提供提示词。

        {% if query %}
        用户额外 review 需求：
        <user_review_requirement>
        {{ query }}
        </user_review_requirement>
        {% endif %}

        注意：
        1. 评审意见应该具体且可操作，而不是泛泛而谈
        2. 对于每个问题都应该提供明确的改进建议
        3. 严重程度的判断要考虑问题对系统的潜在影响
        4. 建议应该符合项目的技术栈和开发规范     

        注意，请以「纯 Markdown」输出，不要出现 <markdown>、</markdown> 之类标签。   
        """
        return {}


    def parse_history_tasks(self,commit_file_name: Optional[str] = None) -> List[Dict]:
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

        if commit_file_name:
            action_files = [f for f in action_files if f == commit_file_name]
        else:
            # 按序号排序
            def get_seq(name):
                return int(name.split("_")[0])

            # 获取最新的action文件列表
            action_files = sorted(action_files, key=get_seq)
            action_files.reverse()   
        
        if not action_files:
            return []
            
        action_file = action_files[0]
        querie_with_urls_and_changes = []

        # 使用ActionYmlFileManager获取提交变更
        changes = self.action_yml_manager.get_commit_changes(action_file)
        if changes:
            querie_with_urls_and_changes = changes

        return querie_with_urls_and_changes
    
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
            
        return querie_with_urls_and_changes

    def review_commit(self,query: str, conversations: List[Dict],commit_id: Optional[str] = None) -> Generator[str,None,None]:
        """
        审查代码提交

        Args:
            query: 用户的查询/要求
            conversations: 之前的对话历史
            commit_id: 可选的指定commit ID，如果提供则直接审查该commit

        Returns:
            Generator[str,None,None]: 审查结果的生成器
        """
        printer = Printer()
        commit_file_name = None
        if commit_id:
            # 利用ActionYmlFileManager获取文件名
            repo = git.Repo(self.project_dir)
            commit = repo.commit(commit_id)
            commit_file_name = self.action_yml_manager.get_file_name_from_commit_msg(commit.message)
            
            if not commit_file_name:
                raise ValueError(printer.get_message_from_key_with_format("no_commit_file_name",commit_id=commit_id))
        
        changes = self.parse_history_tasks(commit_file_name=commit_file_name)  
                              
        if not changes:            
            printer.print_in_terminal("no_commit_found", style="red")
            return None

        # 调用LLM进行代码审查
        try:
            # 获取 prompt 内容            
            prompt_content = self.review.prompt(changes, query)
            new_conversations = conversations.copy()[0:-1]
            new_conversations.append({"role": "user", "content": prompt_content})
            # 构造对话消息            
            v = stream_chat_with_continue(
                    llm=self.llm,
                    conversations=new_conversations,
                    llm_config={},
                    args=self.args
            )
            return v
        except Exception as e:            
            printer.print_in_terminal("code_review_error", style="red", error=str(e))
            return None
