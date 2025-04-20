# This is an empty file created to demonstrate autocoderrules usage.
# The core logic for loading rules is now centralized in:
# from autocoder.common.rulefiles import get_rules
#
# Example usage:
# rules = get_rules()
# print(rules)
# 示例：如何加载和使用 autocoderrules 工具
#
# 文件用途：
#   本文件演示如何在项目中加载和使用 autocoderrules 规则文件。
#   autocoderrules 用于集中管理项目的自动化代码生成、编辑或质量检测规则。
#
# 基本用法：
#   1. 确保项目根目录下存在规则目录（优先级顺序）：
#      - .autocoderrules/
#      - .auto-coder/.autocoderrules/
#      - .auto-coder/autocoderrules/
#   2. 在 rules 目录下放置 .md 规则文件。
#   3. 使用 get_rules() 方法加载所有规则内容。
#
# 示例代码：

from autocoder.common.file_monitor.monitor import FileMonitor
from autocoder.common.rulefiles.autocoderrules_utils import get_rules, get_parsed_rules, parse_rule_file

if __name__ == "__main__":
    monitor = FileMonitor(".")
    monitor.start()
    
    # 示例1：获取所有规则文件内容
    print("示例1：获取所有规则文件内容")
    rules = get_rules()  # 获取所有规则文件内容，返回 {文件路径: 文件内容} 字典
    for path, content in rules.items():
        print(f"规则文件: {path}")
        print(content[:100] + "..." if len(content) > 100 else content)  # 只显示前100个字符
        print("="*40)
    
    # 示例2：获取并解析所有规则文件
    print("\n示例2：获取并解析所有规则文件")
    parsed_rules = get_parsed_rules()  # 获取所有解析后的规则文件，返回 RuleFile 对象列表
    for rule in parsed_rules:
        print(f"规则文件路径: {rule.file_path}")
        print(f"规则描述: {rule.description}")
        print(f"文件匹配模式: {rule.globs}")
        print(f"是否总是应用: {rule.always_apply}")
        print(f"规则内容预览: {rule.content[:100]}..." if len(rule.content) > 100 else rule.content)
        print("="*40)
    
    # 示例3：解析单个规则文件
    print("\n示例3：解析单个规则文件")
    if rules:  # 确保有规则文件
        first_rule_path = next(iter(rules.keys()))
        single_rule = parse_rule_file(first_rule_path)
        print(f"单个规则文件解析结果:")
        print(f"文件路径: {single_rule.file_path}")
        print(f"描述: {single_rule.description}")
        print(f"匹配模式: {single_rule.globs}")
        print(f"是否总是应用: {single_rule.always_apply}")
        print(f"内容摘要: {single_rule.content[:150]}..." if len(single_rule.content) > 150 else single_rule.content)