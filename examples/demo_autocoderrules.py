
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

from autocoder.common.rulefiles import get_rules

if __name__ == "__main__":
    rules = get_rules()  # 获取所有规则文件内容，返回 {文件路径: 文件内容} 字典
    for path, content in rules.items():
        print(f"规则文件: {path}")
        print(content)
        print("="*40)