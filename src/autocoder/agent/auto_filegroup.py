from typing import List, Dict, Optional, Any
import os
import yaml
from loguru import logger
import byzerllm

def load_yaml_config(yaml_file: str) -> Dict:
    """加载YAML配置文件"""
    try:
        with open(yaml_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        logger.error(f"Error loading yaml file {yaml_file}: {str(e)}")
        return {}

class AutoFileGroup:
    def __init__(self, actions_dir: str):
        """
        初始化AutoFileGroup
        
        Args:
            actions_dir: 包含YAML文件的目录
        """
        self.actions_dir = actions_dir
        self.llm = byzerllm.ByzerLLM()
        self.llm.setup_template(model="deepseek_chat", template="auto")
    
    @byzerllm.prompt()
    def group_by_similarity(self, queries: List[str], urls: List[str]) -> Dict[str, Any]:
        """
        根据query和urls的相似性进行分组
        
        用户的查询列表:
        {% for query in queries %}
        - {{ query }}
        {% endfor %}
        
        相关的文件列表:
        {% for url in urls %}
        - {{ url }}
        {% endfor %}
        
        请分析这些查询和文件，根据它们的相关性进行分组。返回以下格式的JSON:
        {
          "groups": [
            {
              "name": "分组名称，用简短的词语概括这个分组的主要功能或目的",
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
        
        all_queries = []
        all_urls = []
        
        # 收集所有query和urls
        for yaml_file in action_files:
            yaml_path = os.path.join(self.actions_dir, yaml_file)
            config = load_yaml_config(yaml_path)
            
            if not config:
                continue
                
            query = config.get('query', '')
            urls = config.get('urls', [])
            
            if query and urls:
                all_queries.append(query)
                all_urls.extend(urls)
        
        if not all_queries or not all_urls:
            return []
        
        # 使用LLM进行分组
        try:
            result = self.group_by_similarity.with_llm(self.llm).run(
                queries=all_queries,
                urls=all_urls
            )
            return yaml.safe_load(result)['groups']
        except Exception as e:
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