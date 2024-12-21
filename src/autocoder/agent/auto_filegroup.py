from typing import List, Dict, Optional
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
    def analyze_file_similarity(self, query: str, urls: List[str]) -> str:
        """
        分析一组文件是否属于同一个需求组
        
        {{ query }}
        
        Files to analyze:
        {% for url in urls %}
        - {{ url }}
        {% endfor %}
        
        请分析这些文件是否与query描述的需求相关,返回以下格式的JSON:
        {
            "is_related": true/false,
            "reason": "详细解释文件之间的关联性"
        }
        """
    
    def group_files(self) -> List[Dict]:
        """
        根据YAML文件中的query和urls进行文件分组
        
        Returns:
            List[Dict]: 分组结果列表，每个字典包含一组相关文件
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
        
        file_groups = []
        current_group = None
        
        for yaml_file in action_files:
            yaml_path = os.path.join(self.actions_dir, yaml_file)
            config = load_yaml_config(yaml_path)
            
            if not config:
                continue
                
            query = config.get('query', '')
            urls = config.get('urls', [])
            
            if not query or not urls:
                continue
            
            # 分析当前文件与已有分组的关联性
            if current_group:
                similarity_result = self.analyze_file_similarity.with_llm(self.llm).run(
                    query=query,
                    urls=urls
                )
                try:
                    result = yaml.safe_load(similarity_result)
                    if result.get('is_related', False):
                        # 添加到当前分组
                        current_group['files'].extend(urls)
                        current_group['queries'].append(query)
                        continue
                except Exception as e:
                    logger.error(f"Error parsing similarity result: {str(e)}")
            
            # 创建新分组
            current_group = {
                'files': urls.copy(),
                'queries': [query],
                'group_id': len(file_groups) + 1
            }
            file_groups.append(current_group)
        
        return file_groups

def create_file_groups(actions_dir: str) -> List[Dict]:
    """
    创建文件分组的便捷函数
    
    Args:
        actions_dir: YAML文件所在目录
    
    Returns:
        List[Dict]: 分组结果
    """
    grouper = AutoFileGroup(actions_dir)
    return grouper.group_files()