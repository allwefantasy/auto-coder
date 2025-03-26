import os
import yaml
import hashlib
import git
from typing import List, Dict, Tuple, Optional, Union, Any
from loguru import logger
from autocoder.common.git_utils import get_repo
from autocoder.common.printer import Printer
import byzerllm
from autocoder.common import git_utils

class ActionYmlFileManager:
    """
    Actions 目录文件操作工具类，用于抽象和管理 actions 目录下的 YAML 文件操作。
    
    主要功能包括：
    - 获取最新的 YAML 文件
    - 按序号排序 YAML 文件
    - 创建新的 YAML 文件
    - 更新 YAML 文件内容
    - 处理 commit 消息与 YAML 文件的关联
    """
    
    def __init__(self, source_dir: Optional[str] = None):
        """
        初始化 ActionYmlFileManager
        
        Args:
            source_dir: 项目根目录
        """
        self.source_dir = source_dir or os.getcwd()
        self.actions_dir = os.path.join(self.source_dir, "actions")
        self.printer = Printer()
        
    def ensure_actions_dir(self) -> bool:
        """
        确保 actions 目录存在
        
        Returns:
            bool: 如果目录存在或创建成功返回 True，否则返回 False
        """
        if not os.path.exists(self.actions_dir):
            try:
                os.makedirs(self.actions_dir, exist_ok=True)
                return True
            except Exception as e:
                logger.error(f"Failed to create actions directory: {e}")
                return False
        return True    
    
    def get_action_files(self, filter_prefix: Optional[str] = None, limit: Optional[int] = None) -> List[str]:
        """
        获取所有符合条件的 YAML 文件名，并按数字部分降序排序
        
        Args:
            filter_prefix: 可选的文件名前缀过滤
            
        Returns:
            List[str]: 符合条件的文件名列表，按数字部分降序排序
        """
        if not os.path.exists(self.actions_dir):
            return []
            
        action_files = [
            f for f in os.listdir(self.actions_dir) 
            if f[:3].isdigit() and "_" in f and f.endswith('_chat_action.yml')
        ]
        
        if filter_prefix:
            action_files = [f for f in action_files if f.startswith(filter_prefix)]
            
        # 按数字部分降序排序
        def get_numeric_part(filename: str) -> int:
            try:
                return int(filename.split('_')[0])
            except (ValueError, IndexError):
                return 0

        if limit:
            return sorted(action_files, key=get_numeric_part, reverse=True)[0:limit]
        else:
            return sorted(action_files, key=get_numeric_part, reverse=True)
    
    def get_sequence_number(self, file_name: str) -> int:
        """
        从文件名中提取序号
        
        Args:
            file_name: YAML 文件名
            
        Returns:
            int: 文件序号
        """
        try:
            return int(file_name.split("_")[0])
        except (ValueError, IndexError):
            return 0
    
    def get_latest_action_file(self, filter_prefix: Optional[str] = None) -> Optional[str]:
        """
        获取最新的 action 文件名（序号最大的）
        
        Args:
            filter_prefix: 可选的文件名前缀过滤
            
        Returns:
            Optional[str]: 最新文件名，如果没有则返回 None
        """
        action_files = self.get_action_files(filter_prefix)
        
        if not action_files:
            return None
            
        # 按序号排序
        sorted_files = sorted(action_files, key=self.get_sequence_number, reverse=True)
        return sorted_files[0] if sorted_files else None
    
    def get_next_sequence_number(self) -> int:
        """
        获取下一个序号
        
        Returns:
            int: 下一个序号
        """
        action_files = self.get_action_files()
        
        if not action_files:
            return 1
            
        seqs = [self.get_sequence_number(f) for f in action_files]
        return max(seqs) + 1
    
    def create_next_action_file(self, name: str, content: Optional[str] = None, 
                               from_yaml: Optional[str] = None) -> Optional[str]:
        """
        创建下一个序号的 action 文件
        
        Args:
            name: 文件基本名称（不含序号和扩展名）
            content: 可选的文件内容
            from_yaml: 可选的基于某个已有 YAML 文件（指定前缀）
            
        Returns:
            Optional[str]: 创建的文件路径，如果创建失败返回 None
        """
        if not self.ensure_actions_dir():
            return None
            
        next_seq = str(self.get_next_sequence_number()).zfill(12)
        new_file_name = f"{next_seq}_{name}.yml"
        new_file_path = os.path.join(self.actions_dir, new_file_name)
        
        if from_yaml:
            from_files = [f for f in self.get_action_files() if f.startswith(from_yaml)]
            if from_files:
                from_file = from_files[0]  # 取第一个匹配的文件
                try:
                    with open(os.path.join(self.actions_dir, from_file), "r", encoding="utf-8") as f:
                        content = f.read()
                except Exception as e:
                    logger.error(f"Failed to read from yaml file: {e}")
                    return None
            else:
                logger.error(f"No YAML file found matching prefix: {from_yaml}")
                return None
        else:
            # 如果没有指定内容和基础文件，则尝试复制最新的文件内容
            if content is None:
                latest_file = self.get_latest_action_file()
                if latest_file:
                    try:
                        with open(os.path.join(self.actions_dir, latest_file), "r", encoding="utf-8") as f:
                            content = f.read()
                    except Exception as e:
                        logger.error(f"Failed to read latest yaml file: {e}")
                        content = ""
                else:
                    content = ""
        
        try:
            with open(new_file_path, "w", encoding="utf-8") as f:
                f.write(content or "")
            return new_file_path
        except Exception as e:
            logger.error(f"Failed to create new action file: {e}")
            return None
    
    def load_yaml_content(self, file_name: str) -> Dict:
        """
        加载 YAML 文件内容
        
        Args:
            file_name: YAML 文件名（仅文件名，不含路径）
            
        Returns:
            Dict: YAML 内容，如果加载失败返回空字典
        """
        yaml_path = os.path.join(self.actions_dir, file_name)         
        try:
            with open(yaml_path, 'r', encoding='utf-8') as f:
                content = yaml.safe_load(f) or {}
            return content
        except Exception as e:            
            self.printer.print_in_terminal("yaml_load_error", style="red", 
                                          yaml_file=yaml_path, error=str(e))
            return {}
        
    def get_full_path_by_file_name(self, file_name: str) -> str:
        """
        根据文件名获取完整路径
        """
        return os.path.join(self.actions_dir, file_name)
    
    def save_yaml_content(self, file_name: str, content: Dict) -> bool:
        """
        保存 YAML 文件内容
        
        Args:
            file_name: YAML 文件名（仅文件名，不含路径）
            content: 要保存的内容
            
        Returns:
            bool: 保存成功返回 True，否则返回 False
        """
        yaml_path = os.path.join(self.actions_dir, file_name)
        
        try:
            with open(yaml_path, 'w', encoding='utf-8') as f:
                yaml.dump(content, f, allow_unicode=True, default_flow_style=False)
            self.printer.print_in_terminal("yaml_update_success", style="green", yaml_file=yaml_path)
            return True
        except Exception as e:
            self.printer.print_in_terminal("yaml_save_error", style="red", 
                                          yaml_file=yaml_path, error=str(e))
            return False
    
    def update_yaml_field(self, file_name: str, field: str, value: Any) -> bool:
        """
        更新 YAML 文件中的特定字段
        
        Args:
            file_name: YAML 文件名（仅文件名，不含路径）
            field: 要更新的字段名
            value: 字段值
            
        Returns:
            bool: 更新成功返回 True，否则返回 False
        """
        yaml_content = self.load_yaml_content(file_name)
        yaml_content[field] = value
        return self.save_yaml_content(file_name, yaml_content)

    def get_all_commit_id_from_file(self,file_name:str):
        '''
        会包含 revert 信息
        '''
        repo = get_repo(self.source_dir)
        if repo is None:
            logger.error("Repository is not initialized.")
            return []
        
        commit_hashes = []        
        for commit in repo.iter_commits():
            lines = commit.message.strip().split('\n')
            last_line = lines[-1]            
            if file_name in last_line or (commit.message.startswith("<revert>") and file_name in commit.message):
                commit_hash = commit.hexsha
                commit_hashes.append(commit_hash)
                
        return commit_hashes

    
    def get_commit_id_from_file(self, file_name: str) -> Optional[str]:
        """
        从文件内容计算 commit ID
        
        Args:
            file_name: YAML 文件名（仅文件名，不含路径）
            
        Returns:
            Optional[str]: commit ID，如果计算失败返回 None
        """
        repo = get_repo(self.source_dir)
        if repo is None:
            logger.error("Repository is not initialized.")
            return None
        
        commit_hash = None
        # 这里遍历从最新的commit 开始遍历
        for commit in repo.iter_commits():
            last_line = commit.message.strip().split('\n')[-1]
            if file_name in last_line and not commit.message.startswith("<revert>"):
                commit_hash = commit.hexsha
                break
        return commit_hash
    
    def get_file_name_from_commit_id(self, commit_id: str) -> Optional[str]:
        """
        从 commit ID 中提取文件名
        
        Args:
            commit_id: commit ID
            
        Returns:
            Optional[str]: 文件名，如果提取失败返回 None
        """
        if not commit_id.startswith("auto_coder_"):
            return None
            
        try:
            # auto_coder_000000001926_chat_action.yml_88614d5bd4046a068786c252fbc39c13
            # auto_coder_000000001926_chat_action.yml
            if commit_id.endswith("_chat_action.yml"):
                return commit_id[len("auto_coder_"):]
            else:
                return "_".join(commit_id[len("auto_coder_"):].split("_")[0:-1])
            return None
        except Exception:
            return None
    
    def get_file_name_from_commit_msg(self, commit_msg: str) -> Optional[str]:
        """
        从 commit 消息中提取文件名，获取消息最后一行，然后调用 get_file_name_from_commit_id
        
        Args:
            commit_msg: commit 消息内容
            
        Returns:
            Optional[str]: 文件名，如果提取失败返回 None
        """
        if not commit_msg:
            return None
            
        try:
            # 获取消息的最后一行
            last_line = commit_msg.strip().split('\n')[-1]
            # 调用 get_file_name_from_commit_id 从最后一行提取文件名
            return self.get_file_name_from_commit_id(last_line)
        except Exception as e:
            logger.error(f"Failed to extract file name from commit message: {e}")
            return None            
    
    def get_commit_changes(self, file_name: Optional[str] = None) -> List[Tuple[str, List[str], Dict[str, Tuple[str, str]]]]:
        """
        获取与特定文件相关的 commit 变更
        
        Args:
            file_name: 可选的 YAML 文件名（仅文件名，不含路径）
            
        Returns:
            List[Tuple[str, List[str], Dict[str, Tuple[str, str]]]]: 变更信息列表
        """
        if not file_name:
            file_name = self.get_latest_action_file()
            if not file_name:
                self.printer.print_in_terminal("no_latest_commit", style="red")
                return []
        
        yaml_content = self.load_yaml_content(file_name)
        query = yaml_content.get('query', '')
        urls = yaml_content.get('urls', [])
        
        commit_id = self.get_commit_id_from_file(file_name)
        if not commit_id:
            return [(query, urls, {})]
        
        changes = {}
        try:
            repo = git.Repo(self.source_dir)
            commit =repo.commit(commit_id)            
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
            self.printer.print_in_terminal("git_command_error", style="red", error=str(e))
        except Exception as e:
            self.printer.print_in_terminal("get_commit_changes_error", style="red", error=str(e))
        
        return [(query, urls, changes)]
    
    def revert_file(self, file_name: str) -> bool:
        revert_result = git_utils.revert_changes(
            self.source_dir, f"auto_coder_{file_name}"
        )
        if revert_result:
            self.update_yaml_field(file_name, "revert_commit_id", revert_result.get("new_commit_hash"))
            return True
        return False
    
    def parse_history_tasks(self, limit: int = 5) -> List[Dict]:
        """
        解析历史任务信息
        
        Args:
            limit: 最多解析的文件数量
            
        Returns:
            List[Dict]: 每个字典包含一个历史任务的信息
        """
        action_files = self.get_action_files()
        
        if not action_files:
            return []
            
        # 按序号排序
        sorted_files = sorted(action_files, key=self.get_sequence_number, reverse=True)
        limited_files = sorted_files[:limit]
        
        history_tasks = []
        for file_name in limited_files:
            yaml_content = self.load_yaml_content(file_name)
            if yaml_content:
                yaml_content['file_name'] = file_name
                history_tasks.append(yaml_content)
        
        return history_tasks 
    
    @byzerllm.prompt()
    def _to_tasks_prompt(self, history_tasks: List[Dict]) -> str:
        """       
        <history_tasks>                
        最近的任务历史记录，从最新到最旧排序：
        
        {% for task in history_tasks %}
        ## 任务 {{ loop.index }}: {{ task.file_name }}
        
        {% if task.query %}
        **用户需求**: {{ task.query }}
        {% endif %}
        
        {% if task.urls %}
        **用户提供的相关文件**:
        {% if task.urls is string %}
        - {{ task.urls }}
        {% else %}
        {% for url in task.urls %}
        - {{ url }}
        {% endfor %}
        {% endif %}
        {% endif %}
        
        {% if task.dynamic_urls %}
        **系统提取的相关文件**:
        {% if task.dynamic_urls is string %}
        - {{ task.dynamic_urls }}
        {% else %}
        {% for url in task.dynamic_urls %}
        - {{ url }}
        {% endfor %}
        {% endif %}
        {% endif %}
        
        {% if task.add_updated_urls %}
        **变更的文件**:
        {% if task.add_updated_urls is string %}
        - {{ task.add_updated_urls }}
        {% else %}
        {% for url in task.add_updated_urls %}
        - {{ url }}
        {% endfor %}
        {% endif %}
        {% endif %}
        
        {% if task.how_to_reproduce %}
        **变更过程**:
        ```
        {{ task.how_to_reproduce }}
        ```
        {% endif %}
        
        {% if not loop.last %}
        ---
        {% endif %}
        {% endfor %}
        </history_tasks>
        请注意上述历史任务记录，以便更好地理解当前用户需求的上下文和连续性。
        """
    
    def to_tasks_prompt(self, limit: int = 5) -> str:
        history_tasks = self.parse_history_tasks(limit)
        return self._to_tasks_prompt.prompt(history_tasks)