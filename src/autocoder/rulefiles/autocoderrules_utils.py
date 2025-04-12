
# -*- coding: utf-8 -*-
import os
from pathlib import Path
from threading import Lock
import threading
from typing import Dict, List, Optional, Set

# 尝试导入 FileMonitor
try:
    from autocoder.common.file_monitor.monitor import FileMonitor, Change
except ImportError:
    # 如果导入失败，提供一个空的实现
    print("警告: 无法导入 FileMonitor，规则文件变更监控将不可用")
    FileMonitor = None
    Change = None

# 默认规则文件目录
DEFAULT_RULES_DIR = '.auto-coder/autocoderrules'


class AutoCoderRulesManager:
    """
    管理 AutoCoder 规则文件的类。
    
    提供读取、解析和监控规则文件变化的功能。
    实现单例模式，确保全局只有一个规则管理器实例。
    """
    _instance = None
    _lock = Lock()

    def __new__(cls):
        if not cls._instance:
            with cls._lock:
                if not cls._instance:
                    cls._instance = super(AutoCoderRulesManager, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # 存储规则文件及其内容
        self._rules_files: Dict[str, str] = {}
        # 规则文件目录
        self._rules_dir = os.path.join(os.getcwd(), DEFAULT_RULES_DIR)
        # 文件监控器
        self._file_monitor = None
        
        # 加载规则文件
        self._load_rules()
        # 设置文件监控
        self._setup_file_monitor()

    def _load_rules(self):
        """加载所有规则文件"""
        self._rules_files.clear()
        
        # 检查规则目录是否存在
        if not os.path.exists(self._rules_dir):
            print(f"规则目录不存在: {self._rules_dir}")
            return
        
        # 遍历规则目录中的所有 .md 文件
        for file_name in os.listdir(self._rules_dir):
            if file_name.endswith('.md'):
                file_path = os.path.join(self._rules_dir, file_name)
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    self._rules_files[file_path] = content
                    print(f"已加载规则文件: {file_path}")
                except Exception as e:
                    print(f"读取规则文件 {file_path} 时出错: {e}")

    def _setup_file_monitor(self):
        """设置文件监控，当规则文件变化时重新加载"""
        if FileMonitor is None or not os.path.exists(self._rules_dir):
            return
        
        try:
            # 获取或创建 FileMonitor 实例
            root_dir = os.path.dirname(self._rules_dir)
            self._file_monitor = FileMonitor(root_dir=root_dir)
            
            # 注册规则目录的回调
            self._file_monitor.register(self._rules_dir, self._on_rules_dir_changed)
            
            # 确保监控器已启动
            if not self._file_monitor.is_running():
                self._file_monitor.start()
                print(f"已启动规则文件监控: {self._rules_dir}")
                        
        except Exception as e:
            print(f"设置规则文件监控时出错: {e}")

    def _on_rules_dir_changed(self, change_type: Change, changed_path: str):
        """当规则目录或其中的文件发生变化时的回调函数"""
        # 只处理 .md 文件的变化
        if not changed_path.endswith('.md'):
            return
            
        print(f"检测到规则文件变化 ({change_type.name}): {changed_path}")
        # 重新加载所有规则
        self._load_rules()
        print("已重新加载所有规则文件")

    def get_all_rules(self) -> Dict[str, str]:
        """获取所有规则文件及其内容"""
        return self._rules_files.copy()

    def get_rule_content(self, rule_name: str) -> Optional[str]:
        """
        获取指定规则文件的内容
        
        :param rule_name: 规则文件名（带或不带 .md 后缀）
        :return: 规则文件内容，如果不存在则返回 None
        """
        if not rule_name.endswith('.md'):
            rule_name += '.md'
            
        rule_path = os.path.join(self._rules_dir, rule_name)
        
        # 如果规则文件在缓存中
        if rule_path in self._rules_files:
            return self._rules_files[rule_path]
            
        # 如果规则文件不在缓存中但文件存在，尝试读取
        if os.path.isfile(rule_path):
            try:
                with open(rule_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                self._rules_files[rule_path] = content
                return content
            except Exception as e:
                print(f"读取规则文件 {rule_path} 时出错: {e}")
                
        return None

    def get_rules_by_tag(self, tag: str) -> List[str]:
        """
        获取包含指定标签的所有规则文件内容
        
        :param tag: 要搜索的标签（例如 #python, #web 等）
        :return: 包含该标签的规则文件内容列表
        """
        matching_rules = []
        
        for file_path, content in self._rules_files.items():
            if tag.lower() in content.lower():
                matching_rules.append(content)
                
        return matching_rules


# 对外提供单例
_rules_manager = AutoCoderRulesManager()

def get_all_rules() -> Dict[str, str]:
    """获取所有规则文件及其内容"""
    return _rules_manager.get_all_rules()

def get_rule_content(rule_name: str) -> Optional[str]:
    """获取指定规则文件的内容"""
    return _rules_manager.get_rule_content(rule_name)

def get_rules_by_tag(tag: str) -> List[str]:
    """获取包含指定标签的所有规则文件内容"""
    return _rules_manager.get_rules_by_tag(tag)
