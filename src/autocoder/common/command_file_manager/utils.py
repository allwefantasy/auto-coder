"""
命令管理模块的工具函数

提供用于处理命令文件和提取Jinja2变量的工具函数。
"""

import os
import re
from typing import List, Set, Dict, Optional, Tuple

from autocoder.common.command_file_manager.models import JinjaVariable, CommandFileAnalysisResult


def extract_jinja2_variables(content: str) -> Set[str]:
    """
    从文本内容中提取Jinja2变量名
    
    Args:
        content: 文本内容
        
    Returns:
        Set[str]: 变量名集合
    """
    # 匹配 {{ variable }} 格式的变量
    pattern = r'{{\s*([a-zA-Z0-9_]+)\s*}}'
    variables = set(re.findall(pattern, content))
    
    # 匹配 {% if variable %} 等控制结构中的变量
    control_pattern = r'{%\s*(?:if|for|elif|unless)\s+(?:not\s+)?([a-zA-Z0-9_]+)'
    control_vars = set(re.findall(control_pattern, content))
    
    # 合并结果
    variables.update(control_vars)
    
    return variables


def extract_jinja2_variables_with_metadata(content: str) -> List[JinjaVariable]:
    """
    从文本内容中提取Jinja2变量及其元数据（如默认值和描述）
    
    此函数会查找特殊注释格式来提取变量的元数据：
    {# @var: variable_name, default: default_value, description: variable description #}
    
    Args:
        content: 文本内容
        
    Returns:
        List[JinjaVariable]: 变量对象列表
    """
    # 首先提取所有原始变量名
    raw_variables = extract_jinja2_variables(content)
    
    # 查找变量元数据注释
    metadata_pattern = r'{#\s*@var:\s*([a-zA-Z0-9_]+)(?:\s*,\s*default:\s*([^,]+))?(?:\s*,\s*description:\s*([^#]+))?\s*#}'
    metadata_matches = re.finditer(metadata_pattern, content)
    
    # 创建变量字典，键为变量名
    variables_dict: Dict[str, JinjaVariable] = {}
    
    # 处理元数据注释
    for match in metadata_matches:
        var_name = match.group(1).strip()
        default_value = match.group(2).strip() if match.group(2) else None
        description = match.group(3).strip() if match.group(3) else None
        
        variables_dict[var_name] = JinjaVariable(
            name=var_name,
            default_value=default_value,
            description=description
        )
    
    # 为没有元数据的变量创建基本对象
    for var_name in raw_variables:
        if var_name not in variables_dict:
            variables_dict[var_name] = JinjaVariable(name=var_name)
    
    return list(variables_dict.values())


def analyze_command_file(file_path: str, file_content: str) -> CommandFileAnalysisResult:
    """
    分析命令文件，提取其中的Jinja2变量
    
    Args:
        file_path: 文件路径
        file_content: 文件内容
        
    Returns:
        CommandFileAnalysisResult: 分析结果
    """
    file_name = os.path.basename(file_path)
    
    # 提取变量及其元数据
    variables = extract_jinja2_variables_with_metadata(file_content)
    raw_variable_names = extract_jinja2_variables(file_content)
    
    # 创建分析结果
    result = CommandFileAnalysisResult(
        file_path=file_path,
        file_name=file_name,
        variables=variables,
        raw_variables=raw_variable_names
    )
    
    return result


def is_command_file(file_name: str) -> bool:
    """
    检查文件是否为命令文件
    
    Args:
        file_name: 文件名
        
    Returns:
        bool: 是否为命令文件
    """
    return file_name.endswith('.md')
