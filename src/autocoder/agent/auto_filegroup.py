from typing import List, Dict, Optional, Any, Tuple
import os
import yaml
from loguru import logger
import byzerllm
import pydantic
from autocoder.common.action_yml_file_manager import ActionYmlFileManager


class FileGroup(pydantic.BaseModel):
    name: str
    description: str
    queries: List[str]
    urls: List[str]    


class FileGroups(pydantic.BaseModel):
    groups: List[FileGroup]


def load_yaml_config(yaml_file: str) -> Dict:
    """加载YAML配置文件"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading yaml file {yaml_file}: {str(e)}")
        return {}


class AutoFileGroup:
    def __init__(self, llm: byzerllm.ByzerLLM, 
                 project_dir: str, 
                 skip_diff: bool = False,
                 group_num_limit: int = 10,
                 file_size_limit: int = 100):
        """
        初始化AutoFileGroup

        Args:
            actions_dir: 包含YAML文件的目录
        """
        self.project_dir = project_dir
        self.action_manager = ActionYmlFileManager(project_dir)
        self.actions_dir = os.path.join(project_dir, "actions")
        self.llm = llm
        self.file_size_limit = file_size_limit
        self.skip_diff = skip_diff
        self.group_num_limit = group_num_limit

    @byzerllm.prompt()
    def group_by_similarity(self, querie_with_urls: List[Tuple[str, List[str], str]]) -> str:
        """
        分析多个开发任务的关联性，将相互关联的任务进行分组。

        输入说明：
        querie_with_urls 包含多个开发任务信息，每个任务由以下部分组成：
        1. query: 任务需求描述
        2. urls: 需要修改的文件路径列表
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

        分组规则：
        1. 每个分组至少包含2个query
        2. 根据以下维度判断任务的关联性：
           - 功能相似性：任务是否属于同一个功能模块
           - 文件关联：修改的文件是否有重叠或紧密关联
           - 代码依赖：代码修改是否存在依赖关系
           - 业务目的：任务的最终业务目标是否一致
        3. 输出的分组数量最多不超过 {{ group_num_limit }}

        期望输出：
        返回符合以下格式的JSON:
        {
          "groups": [
            {
              "name": "分组名称",
              "description": "分组的功能概述，描述该组任务的共同目标",
              "queries": ["相关的query1", "相关的query2"],
              "urls": ["相关的文件1", "相关的文件2"]
            }
          ]
        }

        特别说明：
        1. 分组名称应该简洁且具有描述性，能反映该组任务的主要特征
        2. 分组描述应突出任务间的共同点和关联性
        3. 返回的urls应该是该组任务涉及的所有相关文件的并集
        """
        return {
            "group_num_limit": self.group_num_limit
        }


    def group_files(self) -> List[Dict]:
        """
        根据YAML文件中的query和urls进行文件分组，并获取相关的git commit信息

        Returns:
            List[Dict]: 分组结果列表
        """
        import git
        import hashlib

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
                    # 计算文件的MD5用于匹配commit
                    commit_id = self.action_manager.get_commit_id_from_file(yaml_file)
                    commit = repo.commit(commit_id)                
                    # 查找对应的commit                   
                    if commit and commit.parents:
                        parent = commit.parents[0]
                        commit_diff = repo.git.diff(
                            parent.hexsha, commit.hexsha)
                    else:
                        commit_diff = repo.git.show(commit.hexsha)                    

                querie_with_urls_and_diffs.append((query, urls, commit_diff))

        if not querie_with_urls_and_diffs:
            return []

        # 使用LLM进行分组
        try:            
            result = self.group_by_similarity.with_llm(self.llm).with_return_type(FileGroups).run(
                querie_with_urls=querie_with_urls_and_diffs
            )
            return result.groups
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Error during grouping: {str(e)}")
            return []


def create_file_groups(actions_dir: str) -> List[Dict]:
    """
    创建文件分组的便捷函数

    Args:
        actions_dir: YAML文件所在目录

    Returns:
        List[Dict]: 分组结果，每个字典包含name, queries和urls
    """
    grouper = AutoFileGroup(actions_dir)
    return grouper.group_files()
