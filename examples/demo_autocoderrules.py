
# -*- coding: utf-8 -*-
"""
AutoCoder 规则文件管理演示脚本

展示如何使用 autocoderrules_utils 模块读取和处理规则文件。
"""

import os
import time
import shutil
from pathlib import Path

# 尝试导入 AutoCoderRulesManager
try:
    from autocoder.common.rulefiles.autocoderrules_utils import (
        get_all_rules,
        get_rule_content,
        get_rules_by_tag,
        AutoCoderRulesManager
    )
except ImportError as e:
    print(f"无法导入 AutoCoderRulesManager: {e}")
    print("请确保项目根目录在 PYTHONPATH 中，或者调整导入路径。")
    exit(1)

def create_test_rules():
    """创建测试规则文件"""
    # 创建规则目录
    rules_dir = os.path.join(os.getcwd(), '.auto-coder/autocoderrules')
    os.makedirs(rules_dir, exist_ok=True)
    
    # 创建一些测试规则文件
    rules = {
        "python_rules.md": """# Python 编程规则

## 命名规范
- 类名使用 CamelCase 命名法
- 函数和变量使用 snake_case 命名法
- 常量使用全大写 SNAKE_CASE 命名法

## 代码风格
- 使用 4 个空格缩进
- 每行不超过 79 个字符
- 使用 docstrings 记录函数和类

#python #style #naming
""",
        "web_rules.md": """# Web 开发规则

## HTML 规则
- 使用语义化标签
- 确保 HTML 结构清晰

## CSS 规则
- 使用 BEM 命名约定
- 避免使用 !important

## JavaScript 规则
- 使用 ES6+ 语法
- 优先使用 const 和 let，避免使用 var

#web #html #css #javascript
""",
        "git_rules.md": """# Git 使用规则

## 提交信息
- 使用明确的提交信息
- 每个提交只做一件事

## 分支管理
- 使用 feature 分支进行开发
- 定期合并主分支到开发分支

#git #version-control
"""
    }
    
    # 写入规则文件
    for filename, content in rules.items():
        file_path = os.path.join(rules_dir, filename)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"已创建测试规则文件: {file_path}")
    
    return rules_dir

def demo_rules_manager():
    """演示 AutoCoderRulesManager 的使用"""
    print("\n=== 演示 AutoCoderRulesManager 的使用 ===\n")
    
    # 创建测试规则文件
    rules_dir = create_test_rules()
    
    # 获取 AutoCoderRulesManager 单例
    manager = AutoCoderRulesManager()
    
    # 演示获取所有规则
    print("\n--- 获取所有规则 ---")
    all_rules = get_all_rules()
    print(f"找到 {len(all_rules)} 个规则文件:")
    for path in all_rules.keys():
        print(f" - {os.path.basename(path)}")
    
    # 演示获取特定规则内容
    print("\n--- 获取特定规则内容 ---")
    python_rules = get_rule_content("python_rules")
    if python_rules:
        print("Python 规则内容的前 100 个字符:")
        print(python_rules[:100] + "...")
    else:
        print("未找到 Python 规则文件")
    
    # 演示按标签获取规则
    print("\n--- 按标签获取规则 ---")
    web_rules = get_rules_by_tag("#web")
    print(f"找到 {len(web_rules)} 个包含 #web 标签的规则")
    
    # 演示文件监控功能
    print("\n--- 演示文件监控功能 ---")
    print("1. 修改现有规则文件")
    python_rule_path = os.path.join(rules_dir, "python_rules.md")
    with open(python_rule_path, 'a', encoding='utf-8') as f:
        f.write("\n\n## 新增规则\n- 使用类型注解\n- 使用 f-strings 进行字符串格式化\n")
    print(f"已修改规则文件: {python_rule_path}")
    
    print("\n2. 创建新的规则文件")
    new_rule_path = os.path.join(rules_dir, "database_rules.md")
    with open(new_rule_path, 'w', encoding='utf-8') as f:
        f.write("""# 数据库使用规则

## SQL 规则
- 使用参数化查询防止 SQL 注入
- 合理使用索引

## ORM 规则
- 使用事务确保数据一致性
- 避免 N+1 查询问题

#database #sql #orm
""")
    print(f"已创建新规则文件: {new_rule_path}")
    
    # 等待文件监控器检测变化
    print("\n等待文件监控器检测变化 (3 秒)...")
    time.sleep(3)
    
    # 再次获取所有规则，验证是否检测到变化
    print("\n--- 再次获取所有规则 ---")
    updated_rules = get_all_rules()
    print(f"现在找到 {len(updated_rules)} 个规则文件:")
    for path in updated_rules.keys():
        print(f" - {os.path.basename(path)}")
    
    # 获取新规则内容
    print("\n--- 获取新规则内容 ---")
    db_rules = get_rule_content("database_rules")
    if db_rules:
        print("数据库规则内容的前 100 个字符:")
        print(db_rules[:100] + "...")
    else:
        print("未找到数据库规则文件")
    
    # 清理测试文件
    print("\n--- 是否清理测试文件？ ---")
    answer = input("是否删除测试规则文件？(y/n): ")
    if answer.lower() == 'y':
        try:
            shutil.rmtree(rules_dir)
            print(f"已删除测试规则目录: {rules_dir}")
        except Exception as e:
            print(f"删除测试规则目录时出错: {e}")
    else:
        print(f"保留测试规则目录: {rules_dir}")

if __name__ == "__main__":
    demo_rules_manager()
