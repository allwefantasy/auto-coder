from typing import List, Dict, Optional, Tuple
import os
import yaml
from loguru import logger
import byzerllm
import pydantic
import git

from autocoder.common.action_yml_file_manager import ActionYmlFileManager


class DemandItem(pydantic.BaseModel):
    """单个需求项"""
    type: str = pydantic.Field(description="需求类型：New/Update/Delete/Other")
    description: str = pydantic.Field(description="需求描述")
    reason: Optional[str] = pydantic.Field(description="需求原因", default=None)    


class OrganizedDemands(pydantic.BaseModel):
    """整理后的需求列表，按组织划分"""    
    group_name: str = pydantic.Field(description="需求组名")
    demands: List[DemandItem]


def load_yaml_config(yaml_file: str) -> Dict:
    """加载YAML配置文件"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading yaml file {yaml_file}: {str(e)}")
        return {}


class AutoDemandOrganizer:
    def __init__(self, llm: byzerllm.ByzerLLM,
                 project_dir: str,
                 skip_diff: bool = False,
                 file_size_limit: int = 100):
        """
        初始化需求整理器

        Args:
            llm: ByzerLLM 实例
            project_dir: 项目根目录
            file_size_limit: 最多分析多少历史任务
        """
        self.project_dir = project_dir
        self.action_file_manager = ActionYmlFileManager(project_dir)
        self.actions_dir = os.path.join(project_dir, "actions")
        self.llm = llm
        self.file_size_limit = file_size_limit
        self.skip_diff = skip_diff

    @byzerllm.prompt()
    def organize_demands(self, querie_with_urls: List[Tuple[str, List[str], str]]) -> str:
        """
        根据历史开发任务，整理出清晰的产品需求变更记录。

        输入数据格式：
        querie_with_urls 包含多个历史任务信息，每个任务由以下部分组成：
        1. query: 任务需求描述
        2. urls: 修改的文件路径列表
        3. diff: Git diff信息，展示具体的代码修改

        示例数据：
        <queries>
        {% for query,urls,diff in querie_with_urls %}
        ## {{ query }}        

        修改的文件:
        {% for url in urls %}
        - {{ url }}
        {% endfor %}
        {% if diff %}

        代码变更:
        ```diff
        {{ diff }}
        ```
        {% endif %}        
        {% endfor %}
        </queries>

        整理规则：
        1. 将每个任务拆分为多个独立的需求点
        2. 为每个需求点添加类型标签：
           - New: 新增功能
           - Update: 功能更新
           - Delete: 功能删除
           - Other: 不确定的变更
        3. 每个需求点应包含：
           - 清晰的描述
           - 相关原因（如果有）
           - 涉及的文件列表（如果有）
        4. 保持原始信息的完整性，不要遗漏任何细节

        返回格式说明：
        返回符合以下格式的JSON:
        {
          "group_name": "需求组名称",
          "demands": [
            {
              "type": "需求类型",
              "description": "需求描述",
              "reason": "需求原因（可选）"              
            }
          ]
        }

        示例返回：
        {
          "group_name": "用户系统优化",
          "demands": [
            {
              "type": "New",
              "description": "新增用户登录功能",
              "reason": "满足用户身份验证需求"              
            },
            {
              "type": "Update",
              "description": "优化登录页面UI"              
            }
          ]
        }
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

        action_files = action_files[:self.file_size_limit]

        querie_with_urls_and_diffs = []
        repo = git.Repo(self.project_dir)

        # 收集所有query、urls和对应的commit diff
        for yaml_file in action_files:
            yaml_path = os.path.join(self.actions_dir, yaml_file)
            config = load_yaml_config(yaml_path)

            if not config:
                continue

            query = config.get('query', '')
            urls = config.get('urls', [])

            if query and urls:
                commit_diff = ""
                if not self.skip_diff:                                    
                    commit_id = self.action_file_manager.get_commit_id_from_file(yaml_file)
                    commit = repo.commit(commit_id)
                    if commit:
                        if commit.parents:
                            parent = commit.parents[0]
                            commit_diff = repo.git.diff(
                                parent.hexsha, commit.hexsha)
                        else:
                            commit_diff = repo.git.show(commit.hexsha)

                querie_with_urls_and_diffs.append((query, urls, commit_diff))

        return querie_with_urls_and_diffs

    def organize(self) -> Optional[OrganizedDemands]:
        """
        整理需求变更

        Returns:
            OrganizedDemands: 整理后的需求列表，如果整理失败则返回None
        """
        history_tasks = self.parse_history_tasks()
        
        if not history_tasks:
            logger.warning("No history tasks found")
            return None

        try:
            result = self.organize_demands.with_llm(self.llm).with_return_type(OrganizedDemands).run(
                querie_with_urls=history_tasks
            )
            return result
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error organizing demands: {str(e)}")
            return None