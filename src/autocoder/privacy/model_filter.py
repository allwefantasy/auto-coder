import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from loguru import logger


class ModelPathFilter:
    def __init__(self,
                 model_name: str,
                 config_path: str = "model_filters.yml",
                 default_forbidden: List[str] = None):
        """
        模型路径过滤器
        :param model_name: 当前使用的模型名称
        :param config_path: 过滤规则配置文件路径
        :param default_forbidden: 默认禁止路径规则
        """
        self.model_name = model_name
        self.config_path = Path(config_path)
        self.default_forbidden = default_forbidden or []
        self._rules_cache: Dict[str, List[re.Pattern]] = {}
        self._load_rules()

    def _load_rules(self):
        """加载并编译正则规则"""
        if not self.config_path.exists():
            logger.warning(f"Filter config {self.config_path} not found")
            return

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        model_rules = config.get('model_filters', {}).get(self.model_name, {})
        all_rules = model_rules.get('forbidden_paths', []) + self.default_forbidden

        # 预编译正则表达式
        self._rules_cache[self.model_name] = [
            re.compile(rule) for rule in all_rules
        ]

    def is_accessible(self, file_path: str) -> bool:
        """
        检查文件路径是否符合访问规则
        :return: True表示允许访问,False表示禁止
        """
        # 优先使用模型专属规则
        patterns = self._rules_cache.get(self.model_name, [])

        # 回退到默认规则
        if not patterns and self.default_forbidden:
            patterns = [re.compile(rule) for rule in self.default_forbidden]

        # 如果路径为空或None,直接返回True
        if not file_path:
            return True

        return not any(pattern.search(file_path) for pattern in patterns)

    def add_temp_rule(self, rule: str):
        """
        添加临时规则
        :param rule: 正则表达式规则
        """
        patterns = self._rules_cache.get(self.model_name, [])
        patterns.append(re.compile(rule))
        self._rules_cache[self.model_name] = patterns

    def reload_rules(self):
        """重新加载规则配置"""
        self._rules_cache.clear()
        self._load_rules()

    @classmethod
    def from_model_object(cls,
                         llm_obj,
                         config_path: Optional[str] = None,
                         default_forbidden: Optional[List[str]] = None):
        """
        从LLM对象创建过滤器
        :param llm_obj: ByzerLLM实例或类似对象
        :param config_path: 可选的自定义配置文件路径
        :param default_forbidden: 默认禁止路径规则
        """
        model_name = getattr(llm_obj, 'default_model_name', None)
        if not model_name:
            model_name = "unknown(without default model name)"

        return cls(
            model_name=model_name,
            config_path=config_path or "model_filters.yml",
            default_forbidden=default_forbidden
        )