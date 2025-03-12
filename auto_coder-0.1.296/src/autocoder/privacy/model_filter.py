import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional
from autocoder.common import AutoCoderArgs
from autocoder.utils import llms as llm_utils


class ModelPathFilter:
    def __init__(self,
                 model_name: str,
                 args: AutoCoderArgs,
                 default_forbidden: List[str] = None):
        """
        模型路径过滤器
        :param model_name: 当前使用的模型名称
        :param args: 自动编码器参数
        :param default_forbidden: 默认禁止路径规则
        """
        self.model_name = model_name
        if args.model_filter_path:
            self.config_path = Path(args.model_filter_path)
        else:
            self.config_path = Path(args.source_dir, ".model_filters.yml")
        self.default_forbidden = default_forbidden or []
        self._rules_cache: Dict[str, List[re.Pattern]] = {}
        self._load_rules()

    def _load_rules(self):
        """加载并编译正则规则"""
        if not self.config_path.exists():            
            return

        with open(self.config_path, 'r', encoding="utf-8") as f:
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

    def has_rules(self):
        """检查是否存在规则"""
        return bool(self._rules_cache.get(self.model_name, []))

    @classmethod
    def from_model_object(cls,
                         llm_obj,
                         args: AutoCoderArgs,
                         default_forbidden: Optional[List[str]] = None):
        """
        从LLM对象创建过滤器
        :param llm_obj: ByzerLLM实例或类似对象
        :param args: 自动编码器参数
        :param default_forbidden: 默认禁止路径规则
        """
        model_name = ",".join(llm_utils.get_llm_names(llm_obj))
        if not model_name:
            raise ValueError(f"{model_name} is not found")

        return cls(
            model_name=model_name,
            args=args,
            default_forbidden=default_forbidden
        )