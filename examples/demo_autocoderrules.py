import os
from autocoder.common.file_monitor.monitor import FileMonitor
from autocoder.common.rulefiles.autocoderrules_utils import get_rules, get_parsed_rules, parse_rule_file

if __name__ == "__main__":
    os.chdir("/Users/allwefantasy/projects/auto-coder")
    monitor = FileMonitor(".")
    monitor.start()
    
    single_rule = parse_rule_file("/Users/allwefantasy/projects/auto-coder/.autocoderrules/always_repsond_in_chinese.md")
    print(single_rule)
    print(f"单个规则文件解析结果:")
    print(f"文件路径: {single_rule.file_path}")
    print(f"描述: {single_rule.description}")
    print(f"匹配模式: {single_rule.globs}")
    print(f"是否总是应用: {single_rule.always_apply}")
    print(f"内容摘要: {single_rule.content[:150]}..." if len(single_rule.content) > 150 else single_rule.content)