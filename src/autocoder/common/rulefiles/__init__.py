
# -*- coding: utf-8 -*-
"""
AutoCoder 规则文件管理模块

提供读取、解析和监控 AutoCoder 规则文件的功能。
"""

from .autocoderrules_utils import (
    get_all_rules,
    get_rule_content,
    get_rules_by_tag,
)

__all__ = [
    'get_all_rules',
    'get_rule_content',
    'get_rules_by_tag',
]
