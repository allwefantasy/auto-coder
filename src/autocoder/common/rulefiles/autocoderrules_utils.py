import os
import os
from pathlib import Path
from threading import Lock
import threading
from typing import Dict, List, Optional, Any
from loguru import logger
import re
import yaml
import byzerllm
from pydantic import BaseModel, Field

# 尝试导入 FileMonitor
try:
    from autocoder.common.file_monitor.monitor import FileMonitor, Change
except ImportError:
    # 如果导入失败，提供一个空的实现
    logger.warning("警告: 无法导入 FileMonitor，规则文件变更监控将不可用")
    FileMonitor = None
    Change = None


class RuleFile(BaseModel):
    """规则文件的Pydantic模型"""
    description: str = Field(default="", description="规则的描述")
    globs: List[str] = Field(default_factory=list, description="文件匹配模式列表")
    always_apply: bool = Field(default=False, alias="alwaysApply", description="是否总是应用规则")
    content: str = Field(default="", description="规则文件的正文内容")
    file_path: str = Field(default="", description="规则文件的路径")


class AutocoderRulesManager:
    """
    管理和监控 autocoderrules 目录中的规则文件。
    
    实现单例模式，确保全局只有一个规则管理实例。
    支持监控规则文件变化，当规则文件变化时自动重新加载。
    """
    _instance = None
    _lock = Lock()

    def __new__(cls, project_root: Optional[str] = None):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(AutocoderRulesManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, project_root: Optional[str] = None):
        if self._initialized:
            return
        self._initialized = True
        
        self._rules: Dict[str, str] = {}  # 存储规则文件内容: {file_path: content}
        self._rules_dir: Optional[str] = None  # 当前使用的规则目录
        self._file_monitor = None  # FileMonitor 实例
        self._monitored_dirs: List[str] = []  # 被监控的目录列表
        self._project_root = project_root if project_root is not None else os.getcwd()  # 项目根目录
        
        # 加载规则
        self._load_rules()
        # 设置文件监控
        self._setup_file_monitor()

    def _load_rules(self):
        """
        按优先级顺序加载规则文件。
        优先级顺序：
        1. .autocoderrules/
        2. .auto-coder/.autocoderrules/
        3. .auto-coder/autocoderrules/
        """
        self._rules = {}
        project_root = self._project_root
        
        # 按优先级顺序定义可能的规则目录
        rules_dirs = [
            os.path.join(project_root, ".autocoderrules"),
            os.path.join(project_root, ".auto-coder", ".autocoderrules"),
            os.path.join(project_root, ".auto-coder", "autocoderrules")
        ]
        
        # 按优先级查找第一个存在的目录
        found_dir = None
        for rules_dir in rules_dirs:
            if os.path.isdir(rules_dir):
                found_dir = rules_dir
                break
        
        if not found_dir:
            logger.info("未找到规则目录")
            return
        
        self._rules_dir = found_dir
        logger.info(f"使用规则目录: {self._rules_dir}")
        
        # 加载目录中的所有 .md 文件
        try:
            for fname in os.listdir(self._rules_dir):
                if fname.endswith(".md"):
                    fpath = os.path.join(self._rules_dir, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            content = f.read()
                            self._rules[fpath] = content
                            logger.info(f"已加载规则文件: {fpath}")
                    except Exception as e:
                        logger.info(f"加载规则文件 {fpath} 时出错: {e}")
                        continue
        except Exception as e:
            logger.info(f"读取规则目录 {self._rules_dir} 时出错: {e}")

    def _setup_file_monitor(self):
        """设置文件监控，当规则文件或目录变化时重新加载规则"""
        if FileMonitor is None or not self._rules_dir:
            return
        
        try:
            # 获取项目根目录
            project_root = self._project_root
            
            # 创建 FileMonitor 实例
            self._file_monitor = FileMonitor(root_dir=project_root)
            
            # 监控所有可能的规则目录
            self._monitored_dirs = [
                os.path.join(project_root, ".autocoderrules"),
                os.path.join(project_root, ".auto-coder", ".autocoderrules"),
                os.path.join(project_root, ".auto-coder", "autocoderrules")
            ]
            
            # 注册目录监控
            for dir_path in self._monitored_dirs:
                # 创建目录（如果不存在）
                os.makedirs(dir_path, exist_ok=True)
                # 注册监控
                self._file_monitor.register(dir_path, self._on_rules_changed)
                logger.info(f"已注册规则目录监控: {dir_path}")
            
            # 启动监控
            if not self._file_monitor.is_running():
                self._file_monitor.start()
                logger.info("规则文件监控已启动")
                
        except Exception as e:
            logger.warning(f"设置规则文件监控时出错: {e}")

    def _on_rules_changed(self, change_type: Change, changed_path: str):
        """当规则文件或目录发生变化时的回调函数"""
        # 检查变化是否与规则相关
        is_rule_related = False
        
        # 检查是否是 .md 文件
        if changed_path.endswith(".md"):
            # 检查文件是否在监控的目录中
            for dir_path in self._monitored_dirs:
                if os.path.abspath(changed_path).startswith(os.path.abspath(dir_path)):
                    is_rule_related = True
                    break
        else:
            # 检查是否是监控的目录本身
            for dir_path in self._monitored_dirs:
                if os.path.abspath(changed_path) == os.path.abspath(dir_path):
                    is_rule_related = True
                    break
        
        if is_rule_related:
            logger.info(f"检测到规则相关变化 ({change_type.name}): {changed_path}")
            # 重新加载规则
            self._load_rules()
            logger.info("已重新加载规则")

    def parse_rule_file(self, file_path: str) -> RuleFile:
        """
        解析规则文件并返回结构化的Pydantic模型对象
        
        Args:
            file_path: 规则文件的路径
            
        Returns:
            RuleFile: 包含规则文件结构化内容的Pydantic模型
        """
        if not os.path.exists(file_path) or not file_path.endswith('.md'):
            logger.warning(f"无效的规则文件路径: {file_path}")
            return RuleFile(file_path=file_path)
            
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 解析YAML头部和Markdown内容
            yaml_pattern = re.compile(r'^---\s*\n(.*?)\n---\s*\n', re.DOTALL)
            yaml_match = yaml_pattern.search(content)
            
            metadata = {}
            markdown_content = content
            
            if yaml_match:
                yaml_content = yaml_match.group(1)
                try:
                    metadata = yaml.safe_load(yaml_content)
                    # 移除YAML部分，仅保留Markdown内容
                    markdown_content = content[yaml_match.end():]
                except Exception as e:
                    logger.warning(f"解析规则文件YAML头部时出错: {e}")
            
            # 创建并返回Pydantic模型
            rule = RuleFile(
                description=metadata.get('description', ''),
                globs=metadata.get('globs', []),
                always_apply=metadata.get('alwaysApply', False),
                content=markdown_content.strip(),
                file_path=file_path
            )
            
            return rule
            
        except Exception as e:
            logger.warning(f"解析规则文件时出错: {file_path}, 错误: {e}")
            return RuleFile(file_path=file_path)

    def get_rules(self) -> Dict[str, str]:
        """获取所有规则文件内容"""
        return self._rules.copy()
        
    def get_parsed_rules(self) -> List[RuleFile]:
        """获取所有解析后的规则文件"""
        parsed_rules = []
        for file_path in self._rules:
            parsed_rule = self.parse_rule_file(file_path)
            parsed_rules.append(parsed_rule)
        return parsed_rules


class RuleSelector:
    """
    Selects relevant rules based on a query using an LLM.
    """
    def __init__(self, llm: Any, args: Any):
        """
        Initializes the RuleSelector.

        Args:
            llm: An instance of a language model (e.g., from byzerllm).
            args: Configuration arguments.
        """
        self.llm = llm
        self.args = args
        # Access the singleton instance of the rules manager
        global _rules_manager
        if _rules_manager is None:
            # Initialize if not already done (though it usually should be)
            _rules_manager = AutocoderRulesManager(project_root=getattr(args, 'source_dir', None))
        self._rules_manager = _rules_manager

    def _is_rule_relevant(self, query: str, rule: RuleFile) -> bool:
        """
        Uses the LLM to determine if a rule is relevant to the query.
        """
        prompt = f"""
Given the user query, the rule file name, its description, and its content, determine if the rule is relevant to the query.
Answer with only 'yes' or 'no'.

User Query:
{query}

Rule File: {rule.file_path}
Rule Description: {rule.description}

Rule Content:
```
{rule.content}
```

Is this rule relevant to the user query? Answer 'yes' or 'no'.
"""
        try:
            # Assuming llm has a chat_oai compatible method
            # Adjust the model parameter if needed based on args
            model = getattr(self.args, 'model', None) # Or get model from llm instance if possible
            resp = self.llm.chat_oai(model=model, conversations=[{"role": "user", "content": prompt}])
            response_text = resp[0].output.strip().lower()
            logger.debug(f"LLM relevance check for rule '{rule.file_path}': Query='{query}', Response='{response_text}'")
            return response_text == 'yes'
        except Exception as e:
            logger.error(f"Error calling LLM for rule relevance check ({rule.file_path}): {e}")
            # Default to not relevant in case of error
            return False

    def select_rules(self, query: str) -> Dict[str, str]:
        """
        Selects rules that are always applied or deemed relevant by the LLM.

        Args:
            query: The user's query or request.

        Returns:
            A dictionary mapping selected rule file paths to their content.
        """
        selected_rules: Dict[str, str] = {}
        parsed_rules = self._rules_manager.get_parsed_rules()
        logger.info(f"Starting rule selection for query: '{query}'")
        logger.info(f"Total rules found: {len(parsed_rules)}")

        for rule in parsed_rules:
            if rule.always_apply:
                logger.info(f"Including rule (alwaysApply=True): {rule.file_path}")
                selected_rules[rule.file_path] = rule.content
            else:
                logger.debug(f"Checking relevance for rule (alwaysApply=False): {rule.file_path}")
                if self.llm and self._is_rule_relevant(query, rule):
                    logger.info(f"Including rule (LLM deemed relevant): {rule.file_path}")
                    selected_rules[rule.file_path] = rule.content
                else:
                    logger.info(f"Skipping rule (not relevant or LLM error): {rule.file_path}")

        logger.info(f"Selected {len(selected_rules)} rules out of {len(parsed_rules)}.")
        return selected_rules


# 对外提供单例
_rules_manager = None

def get_rules_manager(project_root: Optional[str] = None) -> AutocoderRulesManager:
    """Gets the singleton instance of the AutocoderRulesManager."""
    global _rules_manager
    if _rules_manager is None:
        _rules_manager = AutocoderRulesManager(project_root=project_root)
    elif project_root is not None and _rules_manager._project_root != os.path.abspath(project_root):
         # If called with a different project root, re-initialize (or handle differently if needed)
         logger.warning(f"Re-initializing AutocoderRulesManager for new project root: {project_root}")
         _rules_manager = AutocoderRulesManager(project_root=project_root)
    return _rules_manager

def get_rules(project_root: Optional[str] = None) -> Dict[str, str]:
    """获取所有规则文件内容，可指定项目根目录"""
    """获取所有规则文件内容，可指定项目根目录"""
    manager = get_rules_manager(project_root=project_root)
    return manager.get_rules()

def get_parsed_rules(project_root: Optional[str] = None) -> List[RuleFile]:
    """获取所有解析后的规则文件，可指定项目根目录"""
    """获取所有解析后的规则文件，可指定项目根目录"""
    manager = get_rules_manager(project_root=project_root)
    return manager.get_parsed_rules()

def parse_rule_file(file_path: str, project_root: Optional[str] = None) -> RuleFile:
    """解析指定的规则文件，可指定项目根目录"""
    """解析指定的规则文件，可指定项目根目录"""
    manager = get_rules_manager(project_root=project_root)
    return manager.parse_rule_file(file_path)
