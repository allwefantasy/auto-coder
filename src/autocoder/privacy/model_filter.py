import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Literal, Union, Any
from enum import Enum
import pathspec
import os
from dataclasses import dataclass

from autocoder.common import AutoCoderArgs
from autocoder.utils import llms as llm_utils

# 尝试导入 FileMonitor
try:
    from autocoder.common.file_monitor.monitor import FileMonitor, Change
except ImportError:
    # 如果导入失败，提供一个空的实现
    print("警告: 无法导入 FileMonitor，过滤器文件变更监控将不可用")
    FileMonitor = None
    Change = None


class Permission(str, Enum):
    """权限枚举类型"""
    ALLOW = "ALLOW"           # 显式允许访问
    DENY = "DENY"             # 完全禁止访问
    DENY_READ = "DENY_READ"   # 禁止读取但允许写入
    DENY_WRITE = "DENY_WRITE" # 禁止写入但允许读取


class AccessOperation(str, Enum):
    """访问操作类型"""
    READ = "READ"
    WRITE = "WRITE"


@dataclass
class LineRange:
    """行范围定义"""
    start: int
    end: int
    
    def contains(self, line_number: int) -> bool:
        """检查指定行号是否在范围内"""
        return self.start <= line_number <= self.end


@dataclass
class AccessRule:
    """访问规则"""
    pattern: str
    permission: Permission
    line_ranges: List[LineRange] = None
    
    @classmethod
    def from_dict(cls, rule_dict: Dict[str, Any]) -> 'AccessRule':
        """从字典创建规则"""
        pattern = rule_dict.get('pattern')
        permission = Permission(rule_dict.get('permission', 'DENY'))
        
        line_ranges = None
        ranges_data = rule_dict.get('line_ranges')
        if ranges_data:
            line_ranges = []
            for range_dict in ranges_data:
                start = range_dict.get('start', 1)
                end = range_dict.get('end', float('inf'))
                line_ranges.append(LineRange(start, end))
                
        return cls(pattern=pattern, permission=permission, line_ranges=line_ranges)


class ModelPathFilter:
    def __init__(self,
                 model_name: str,
                 args: AutoCoderArgs,
                 default_rules: List[Dict[str, Any]] = None):
        """
        模型路径过滤器
        :param model_name: 当前使用的模型名称
        :param args: 自动编码器参数
        :param default_rules: 默认访问规则
        """
        self.model_name = model_name
        self.args = args
        if args.model_filter_path:
            # 如果是相对路径，转换为绝对路径
            path = Path(args.model_filter_path)
            if not path.is_absolute():
                path = Path(args.source_dir) / path
            self.config_path = path
        else:
            # 检查项目根目录
            root_config = Path(args.source_dir) / ".model_filters.yml"
            if root_config.exists():
                self.config_path = root_config
            else:
                # 检查.auto-coder目录
                auto_coder_config = Path(args.source_dir) / ".auto-coder" / ".model_filters.yml"
                self.config_path = auto_coder_config
        
        self.default_rules = default_rules or []
        self._rules_cache: Dict[str, List[AccessRule]] = {}
        self._path_specs: Dict[str, pathspec.PathSpec] = {}
        self._file_monitor = None
        self._load_rules()
        self._setup_file_monitor()

    def _load_rules(self):
        """加载并编译路径过滤规则"""
        if not self.config_path.exists():            
            return

        with open(self.config_path, 'r', encoding="utf-8") as f:
            config = yaml.safe_load(f) or {}
        
        # 处理模型特定规则
        model_config = config.get('model_filters', {}).get(self.model_name, {})
        model_rules = model_config.get('rules', [])
        
        # 处理默认规则
        config_default_rules = config.get('default_rules', [])
        all_rules = []
        
        # 将所有规则转换为 AccessRule 对象
        for rule_dict in model_rules + config_default_rules + self.default_rules:
            if isinstance(rule_dict, str):
                # 兼容旧版本的简单字符串格式
                rule = AccessRule(pattern=rule_dict, permission=Permission.DENY)
            else:
                rule = AccessRule.from_dict(rule_dict)
            all_rules.append(rule)
            
        # 缓存规则
        self._rules_cache[self.model_name] = all_rules
        
        # 创建路径匹配器
        patterns = [rule.pattern for rule in all_rules]
        self._path_specs[self.model_name] = pathspec.PathSpec.from_lines('gitwildmatch', patterns)

    def _setup_file_monitor(self):
        """设置文件监控，当过滤器文件变化时重新加载规则"""
        if FileMonitor is None or not self.config_path.exists():
            return
        
        try:
            # 获取或创建 FileMonitor 实例
            root_dir = os.path.dirname(str(self.config_path))
            self._file_monitor = FileMonitor(root_dir=root_dir)
            
            # 注册过滤器文件的回调
            self._file_monitor.register(str(self.config_path), self._on_filter_file_changed)
        except Exception as e:
            print(f"设置过滤器文件监控时出错: {e}")

    def _on_filter_file_changed(self, change_type: Change, changed_path: str):
        """当过滤器文件发生变化时的回调函数"""
        if os.path.abspath(changed_path) == os.path.abspath(str(self.config_path)):
            print(f"检测到过滤器文件变化 ({change_type.name}): {changed_path}")
            self.reload_rules()
            print(f"已重新加载模型 {self.model_name} 的过滤规则")

    def _normalize_path(self, file_path: str) -> str:
        """标准化文件路径"""
        if not file_path:
            return ""
        # 转换为相对路径
        rel_path = os.path.relpath(file_path, self.args.source_dir)
        # 统一路径分隔符
        return rel_path.replace(os.sep, '/')

    def _get_applicable_rules(self, file_path: str) -> List[AccessRule]:
        """获取适用于指定文件的所有规则"""
        if not file_path:
            return []
            
        normalized_path = self._normalize_path(file_path)
        path_spec = self._path_specs.get(self.model_name)
        rules = self._rules_cache.get(self.model_name, [])
        
        if not path_spec or not rules:
            return []
            
        # 找出所有匹配此路径的规则
        matching_rules = []
        for rule in rules:
            # 使用PathSpec检查单个匹配
            single_spec = pathspec.PathSpec.from_lines('gitwildmatch', [rule.pattern])
            if single_spec.match_file(normalized_path):
                matching_rules.append(rule)
                
        return matching_rules

    def is_accessible(self, 
                      file_path: str, 
                      operation: Union[AccessOperation, str] = AccessOperation.READ,
                      line_number: int = None) -> bool:
        """
        检查文件路径在指定操作和行号下是否可访问
        :param file_path: 文件路径
        :param operation: 访问操作类型(READ/WRITE)
        :param line_number: 可选的行号
        :return: True表示允许访问,False表示禁止
        """
        if not file_path:
            return True
            
        # 确保operation是AccessOperation类型
        if isinstance(operation, str):
            operation = AccessOperation(operation)
            
        # 获取所有适用规则
        applicable_rules = self._get_applicable_rules(file_path)
        if not applicable_rules:
            return True
            
        # 按优先级处理规则 (ALLOW > DENY_specific > DENY)
        for rule in applicable_rules:
            # 检查行范围限制
            if rule.line_ranges and line_number:
                # 如果规则有行范围限制但当前行不在范围内，跳过此规则
                if not any(r.contains(line_number) for r in rule.line_ranges):
                    continue
                    
            # 检查权限
            if rule.permission == Permission.ALLOW:
                return True
            elif rule.permission == Permission.DENY:
                return False
            elif rule.permission == Permission.DENY_READ and operation == AccessOperation.READ:
                return False
            elif rule.permission == Permission.DENY_WRITE and operation == AccessOperation.WRITE:
                return False
                
        # 如果没有规则明确禁止，默认允许访问
        return True

    def is_readable(self, file_path: str, line_number: int = None) -> bool:
        """检查文件是否可读取"""
        return self.is_accessible(file_path, AccessOperation.READ, line_number)
        
    def is_writable(self, file_path: str, line_number: int = None) -> bool:
        """检查文件是否可写入"""
        return self.is_accessible(file_path, AccessOperation.WRITE, line_number)

    def get_accessible_line_ranges(self, 
                                  file_path: str, 
                                  operation: Union[AccessOperation, str] = AccessOperation.READ) -> List[LineRange]:
        """
        获取文件在指定操作下的可访问行范围
        :return: 可访问的行范围列表
        """
        if not file_path:
            return [LineRange(1, float('inf'))]  # 默认完全可访问
            
        # 确保operation是AccessOperation类型
        if isinstance(operation, str):
            operation = AccessOperation(operation)
            
        # 获取所有适用规则
        applicable_rules = self._get_applicable_rules(file_path)
        if not applicable_rules:
            return [LineRange(1, float('inf'))]  # 默认完全可访问
            
        # 检查是否有ALLOW规则
        for rule in applicable_rules:
            if rule.permission == Permission.ALLOW:
                return [LineRange(1, float('inf'))]  # 显式允许则完全可访问
                
        # 检查是否有完全DENY规则
        for rule in applicable_rules:
            if rule.permission == Permission.DENY:
                return []  # 完全禁止则无可访问行
            elif ((rule.permission == Permission.DENY_READ and operation == AccessOperation.READ) or
                  (rule.permission == Permission.DENY_WRITE and operation == AccessOperation.WRITE)):
                if not rule.line_ranges:
                    return []  # 如果没有指定行范围限制，则完全禁止指定操作
                    
        # 收集所有限制的行范围
        restricted_ranges = []
        for rule in applicable_rules:
            if ((rule.permission == Permission.DENY_READ and operation == AccessOperation.READ) or
                (rule.permission == Permission.DENY_WRITE and operation == AccessOperation.WRITE)):
                if rule.line_ranges:
                    restricted_ranges.extend(rule.line_ranges)
                    
        # 如果没有限制范围，则全部可访问
        if not restricted_ranges:
            return [LineRange(1, float('inf'))]
            
        # 计算可访问范围 (补集)
        # 简化处理: 目前仅返回第一个受限区域前的行和最后一个受限区域后的行
        sorted_ranges = sorted(restricted_ranges, key=lambda r: r.start)
        accessible = []
        
        # 第一个受限区域前的行
        if sorted_ranges[0].start > 1:
            accessible.append(LineRange(1, sorted_ranges[0].start - 1))
            
        # 相邻受限区域之间的行
        for i in range(len(sorted_ranges) - 1):
            if sorted_ranges[i].end + 1 < sorted_ranges[i+1].start:
                accessible.append(LineRange(sorted_ranges[i].end + 1, sorted_ranges[i+1].start - 1))
                
        # 最后一个受限区域后的行
        if sorted_ranges[-1].end < float('inf'):
            accessible.append(LineRange(sorted_ranges[-1].end + 1, float('inf')))
            
        return accessible

    def add_temp_rule(self, pattern: str, permission: Union[Permission, str] = Permission.DENY):
        """
        添加临时规则
        :param pattern: gitignore格式的匹配模式
        :param permission: 权限类型
        """
        # 确保permission是Permission类型
        if isinstance(permission, str):
            permission = Permission(permission)
            
        # 创建新规则
        new_rule = AccessRule(pattern=pattern, permission=permission)
        
        # 添加到规则缓存
        rules = self._rules_cache.get(self.model_name, [])
        rules.append(new_rule)
        self._rules_cache[self.model_name] = rules
        
        # 更新路径匹配器
        patterns = [rule.pattern for rule in rules]
        self._path_specs[self.model_name] = pathspec.PathSpec.from_lines('gitwildmatch', patterns)

    def reload_rules(self):
        """重新加载规则配置"""
        self._rules_cache.clear()
        self._path_specs.clear()
        self._load_rules()

    def has_rules(self):
        """检查是否存在规则"""
        return self.model_name in self._rules_cache and bool(self._rules_cache[self.model_name])

    @classmethod
    def from_model_object(cls,
                         llm_obj,
                         args: AutoCoderArgs,
                         default_rules: Optional[List[Dict[str, Any]]] = None):
        """
        从LLM对象创建过滤器
        :param llm_obj: ByzerLLM实例或类似对象
        :param args: 自动编码器参数
        :param default_rules: 默认访问规则
        """
        model_name = ",".join(llm_utils.get_llm_names(llm_obj))
        if not model_name:
            raise ValueError(f"{model_name} is not found")

        return cls(
            model_name=model_name,
            args=args,
            default_rules=default_rules
        )