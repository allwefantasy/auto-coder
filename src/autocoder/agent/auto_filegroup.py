from typing import List, Dict, Optional, Any, Tuple
import os
import yaml
from loguru import logger
import byzerllm
import pydantic


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
    def __init__(self, llm: byzerllm.ByzerLLM, actions_dir: str, file_size_limit: int = 100):
        """
        初始化AutoFileGroup

        Args:
            actions_dir: 包含YAML文件的目录
        """
        self.actions_dir = actions_dir
        self.llm = llm
        self.file_size_limit = file_size_limit

    @byzerllm.prompt()
    def group_by_similarity(self, querie_with_urls: List[Tuple[str, List[str]]]) -> str:
        """
        urls 和 query 之间关系：
        大模型可以根据一组 urls（文件路径列表） 来实现对需求（query）进行编码，从而实现该需求。
        大模型最后编码产出是会对urls里��部分或者全部文件进行更新，以及新增一些文件。

        下面是用户查询以及对应的文件列表：
        <queries>
        {% for query,urls in querie_with_urls %}
        ## {{ query }}        
        {% for url in urls %}
        - {{ url }}
        {% endfor %}
        </urls>
        {% endfor %}
        </queries>


        请分析这些查询和文件，根据它们的相关性进行分组。返回以下格式的JSON:
        {
          "groups": [
            {
              "name": "分组名称",
              "description": "分组描述，用简短的词语概括这个分组的主要功能或目的",
              "queries": ["相关的query1", "相关的query2"],
              "urls": ["相关的文件1", "相关的文件2"]
            }
          ]
        }
        """

    def group_files(self) -> List[Dict]:
        """
        根据YAML文件中的query和urls进行文件分组

        Returns:
            List[Dict]: 分组结果列表
        """
        # 获取所有YAML文件
        action_files = [
            f for f in os.listdir(self.actions_dir)
            if f[:3].isdigit() and "_" in f and f.endswith(".yml")
        ]

        # 按序号排序
        def get_seq(name):
            return int(name.split("_")[0])
        action_files = sorted(action_files, key=get_seq)

        action_files = action_files[:self.file_size_limit]

        querie_with_urls = []

        # 收集所有query和对应的urls
        for yaml_file in action_files:
            yaml_path = os.path.join(self.actions_dir, yaml_file)
            config = load_yaml_config(yaml_path)

            if not config:
                continue

            query = config.get('query', '')
            urls = config.get('urls', [])

            if query and urls:
                querie_with_urls.append((query, urls))

        if not querie_with_urls:
            return []

        # 使用LLM进行分组
        try:
            result = self.group_by_similarity.with_llm(self.llm).with_return_type(FileGroups).run(
                querie_with_urls=querie_with_urls
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
