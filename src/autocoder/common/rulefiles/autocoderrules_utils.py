
import os
from pathlib import Path
from threading import Lock
import threading
from typing import Dict, List, Optional
from loguru import logger

# 尝试导入 FileMonitor
try:
    from autocoder.common.file_monitor.monitor import FileMonitor, Change
except ImportError:
    # 如果导入失败，提供一个空的实现
    logger.warning("警告: 无法导入 FileMonitor，规则文件变更监控将不可用")
    FileMonitor = None
    Change = None


class AutocoderRulesManager:
    """
    管理和监控 autocoderrules 目录中的规则文件。
    
    实现单例模式，确保全局只有一个规则管理实例。
    支持监控规则文件变化，当规则文件变化时自动重新加载。
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(AutocoderRulesManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        self._rules: Dict[str, str] = {}  # 存储规则文件内容: {file_path: content}
        self._rules_dir: Optional[str] = None  # 当前使用的规则目录
        self._file_monitor = None  # FileMonitor 实例
        self._monitored_dirs: List[str] = []  # 被监控的目录列表
        
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
        project_root = os.getcwd()
        
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
            project_root = os.getcwd()
            
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
                print(f"已注册规则目录监控: {dir_path}")
            
            # 启动监控
            if not self._file_monitor.is_running():
                self._file_monitor.start()
                print("规则文件监控已启动")
                
        except Exception as e:
            print(f"设置规则文件监控时出错: {e}")

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
            print(f"检测到规则相关变化 ({change_type.name}): {changed_path}")
            # 重新加载规则
            self._load_rules()
            print("已重新加载规则")

    def get_rules(self) -> Dict[str, str]:
        """获取所有规则文件内容"""
        return self._rules.copy()


# 对外提供单例
_rules_manager = AutocoderRulesManager()

def get_rules() -> Dict[str, str]:
    """获取所有规则文件内容"""
    return _rules_manager.get_rules()
