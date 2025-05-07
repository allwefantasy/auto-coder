import os
from pathlib import Path
from threading import Lock
import threading
from typing import Dict, List, Optional
from loguru import logger
import re
import yaml
import byzerllm # Added import
from pydantic import BaseModel, Field
from typing import List, Dict, Optional, Any # Added Any
from autocoder.common import AutoCoderArgs
import concurrent.futures  # 添加线程池导入

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
    always_apply: bool = Field(default=False, description="是否总是应用规则")
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

    @classmethod
    def reset_instance(cls):
        """
        重置单例实例。
        如果当前实例正在运行，则先取消注册监控的目录，然后重置实例。
        """
        with cls._lock:
            if cls._instance is not None:
                # 取消注册监控的目录
                if cls._instance._file_monitor:
                    for dir_path in cls._instance._monitored_dirs:
                        try:
                            cls._instance._file_monitor.unregister(dir_path)
                            logger.info(f"已取消注册目录监控: {dir_path}")
                        except Exception as e:
                            logger.warning(f"取消注册目录 {dir_path} 时出错: {e}")
                cls._instance = None
                logger.info("AutocoderRulesManager单例已被重置")


# 对外提供单例
_rules_manager = None

def get_rules(project_root: Optional[str] = None) -> Dict[str, str]:
    """获取所有规则文件内容，可指定项目根目录"""
    global _rules_manager
    if _rules_manager is None:
        _rules_manager = AutocoderRulesManager(project_root=project_root)
    return _rules_manager.get_rules()

def get_parsed_rules(project_root: Optional[str] = None) -> List[RuleFile]:
    """获取所有解析后的规则文件，可指定项目根目录"""
    global _rules_manager
    if _rules_manager is None:
        _rules_manager = AutocoderRulesManager(project_root=project_root)
    return _rules_manager.get_parsed_rules()

def parse_rule_file(file_path: str, project_root: Optional[str] = None) -> RuleFile:
    """解析指定的规则文件，可指定项目根目录"""
    global _rules_manager
    if _rules_manager is None:
        _rules_manager = AutocoderRulesManager(project_root=project_root)
    return _rules_manager.parse_rule_file(file_path)

def reset_rules_manager():
    """重置AutocoderRulesManager单例实例"""
    AutocoderRulesManager.reset_instance()
    global _rules_manager
    _rules_manager = None

# 添加用于返回类型的Pydantic模型
class RuleRelevance(BaseModel):
    """用于规则相关性判断的返回模型"""
    is_relevant: bool = Field(description="规则是否与当前任务相关")
    reason: str = Field(default="", description="判断理由")


class RuleSelector:
    """
    根据LLM的判断和规则元数据选择适用的规则。
    """
    def __init__(self, llm: Optional[byzerllm.ByzerLLM], args: Optional[AutoCoderArgs] = None):
        """
        初始化RuleSelector。

        Args:
            llm: ByzerLLM 实例，用于判断规则是否适用。如果为 None，则只选择 always_apply=True 的规则。
            args: 传递给 Agent 的参数，可能包含用于规则选择的上下文信息。            
        """
        self.llm = llm
        self.args = args        

    @byzerllm.prompt()
    def _build_selection_prompt(self, rule: RuleFile, context: str = "") -> str:
        """
        判断规则是否适用于当前任务。

        规则描述:
        {{ rule.description }}

        规则内容摘要 (前200字符):
        {{ rule.content[:200] }}

        {% if context %}
        任务上下文:
        {{ context }}
        {% endif %}

        基于以上信息，判断这条规则 (路径: {{ rule.file_path }}) 是否与当前任务相关并应该被应用？
        
        请以JSON格式返回结果:
        ```json
        {
            "is_relevant": true或false,
            "reason": "判断理由"
        }
        ```
        """
        # 注意：确保 rule 对象和 context 字典能够被 Jinja2 正确访问。
        # Pydantic模型可以直接在Jinja2中使用其属性。
        return {
            "rule": rule,
            "context": context
        }
        
    def _evaluate_rule(self, rule: RuleFile, context: str) -> tuple[RuleFile, bool, Optional[str]]:
        """
        评估单个规则是否适用于当前上下文。
        
        Args:
            rule: 要评估的规则
            context: 上下文信息
            
        Returns:
            tuple: (规则, 是否选中, 理由)
        """
        # 如果规则设置为总是应用，直接返回选中
        if rule.always_apply:
            return (rule, True, "规则设置为总是应用")
            
        # 如果没有LLM，无法评估non-always规则
        if self.llm is None:
            return (rule, False, "未提供LLM，无法评估non-always规则")
            
        try:
            prompt = self._build_selection_prompt.prompt(rule=rule, context=context)
            logger.debug(f"为规则 '{os.path.basename(rule.file_path)}' 生成的判断 Prompt (片段): {prompt[:200]}...")
            
            result = None
            try:
                # 使用with_return_type方法获取结构化结果
                result = self._build_selection_prompt.with_llm(self.llm).with_return_type(RuleRelevance).run(rule=rule, context=context)
                if result and result.is_relevant:
                    return (rule, True, result.reason)
                else:
                    return (rule, False, result.reason if result else "未提供理由")
            except Exception as e:
                logger.warning(f"LLM 未能为规则 '{os.path.basename(rule.file_path)}' 提供有效响应: {e}")
                return (rule, False, f"LLM评估出错: {str(e)}")
                
        except Exception as e:
            logger.error(f"评估规则 '{os.path.basename(rule.file_path)}' 时出错: {e}", exc_info=True)
            return (rule, False, f"评估过程出错: {str(e)}")

    def select_rules(self, context: str) -> List[RuleFile]:
        """
        选择适用于当前上下文的规则。使用线程池并发评估规则。

        Args:
            context: 可选的字典，包含用于规则选择的上下文信息 (例如，用户指令、目标文件等)。

        Returns:
            List[RuleFile]: 选定的规则列表。
        """
        rules = get_parsed_rules()
        selected_rules: List[RuleFile] = []
        logger.info(f"开始选择规则，总规则数: {len(rules)}")
        
        # 预先分类处理always_apply规则
        always_apply_rules = []
        need_llm_rules = []
        
        for rule in rules:
            if rule.always_apply:
                always_apply_rules.append(rule)
            elif self.llm is not None:
                need_llm_rules.append(rule)
        
        # 添加always_apply规则
        for rule in always_apply_rules:
            selected_rules.append(rule)
            logger.debug(f"规则 '{os.path.basename(rule.file_path)}' (AlwaysApply=True) 已自动选择。")
            
        # 如果没有需要LLM评估的规则，直接返回结果
        if not need_llm_rules:
            logger.info(f"规则选择完成，选中规则数: {len(selected_rules)}")
            return selected_rules
            
        # 使用线程池并发评估规则
        with concurrent.futures.ThreadPoolExecutor() as executor:
            # 提交所有评估任务
            future_to_rule = {
                executor.submit(self._evaluate_rule, rule, context): rule 
                for rule in need_llm_rules
            }
            
            # 收集评估结果
            for future in concurrent.futures.as_completed(future_to_rule):
                rule, is_selected, reason = future.result()
                if is_selected:
                    selected_rules.append(rule)
                    logger.info(f"规则 '{os.path.basename(rule.file_path)}' (AlwaysApply=False) 已被 LLM 选择，原因: {reason}")
                else:
                    logger.debug(f"规则 '{os.path.basename(rule.file_path)}' (AlwaysApply=False) 未被 LLM 选择，原因: {reason}")
                    
        logger.info(f"规则选择完成，选中规则数: {len(selected_rules)}")
        return selected_rules

    def get_selected_rules_content(self, context: Optional[Dict] = None) -> Dict[str, str]:
        """
        获取选定规则的文件路径和内容字典。

        Args:
            context: 传递给 select_rules 的上下文。

        Returns:
            Dict[str, str]: 选定规则的 {file_path: content} 字典。
        """
        selected_rules = self.select_rules(context=context)
        # 使用 os.path.basename 获取文件名作为 key，如果需要的话
        # return {os.path.basename(rule.file_path): rule.content for rule in selected_rules}
        # 保持 file_path 作为 key
        return {rule.file_path: rule.content for rule in selected_rules}

def auto_select_rules(context: str, llm: Optional[byzerllm.ByzerLLM] = None,args:Optional[AutoCoderArgs] = None) -> List[Dict[str, str]]:
    """
    根据LLM的判断和规则元数据选择适用的规则。
    """
    selector = RuleSelector(llm=llm, args=args)    
    return selector.get_selected_rules_content(context=context)

def get_required_and_index_rules() -> Dict[str, str]:
    """
    获取所有必须应用的规则文件(always_apply=True)和Index.md文件。
    
    Args:
        project_root: 可选的项目根目录路径，用于初始化规则管理器。
        
    Returns:
        Dict[str, str]: 包含必须应用的规则和Index.md文件的{file_path: content}字典。
    """
    # 获取所有解析后的规则文件
    parsed_rules = get_parsed_rules()
    result: Dict[str, str] = {}
    logger.info(f"获取所有解析后的规则文件完成，总数: {len(parsed_rules)}")
    
    for rule in parsed_rules:
        # 检查是否是always_apply=True的规则
        if rule.always_apply:
            result[rule.file_path] = rule.content
            logger.info(f"添加必须应用的规则: {os.path.basename(rule.file_path)}")
        
        # 检查是否是Index.md文件
        if os.path.basename(rule.file_path).lower() == "index.md":
            result[rule.file_path] = rule.content
            logger.info(f"添加Index.md文件: {rule.file_path}")
    
    logger.info(f"获取必须应用的规则和Index.md文件完成，总数: {len(result)}")
    return result
