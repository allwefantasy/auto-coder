# -*- coding: utf-8 -*-
import os
import time
import shutil
from pathlib import Path

# 尝试导入 AutocoderRulesManager
try:
    # 假设项目根目录在 PYTHONPATH 中
    from autocoder.ignorefiles.autocoderrules_utils import AutocoderRulesManager, get_rules
except ImportError as e:
    print(f"无法导入 AutocoderRulesManager: {e}")
    print("请确保项目根目录在 PYTHONPATH 中，或者调整导入路径。")
    # 提供一个假的实现以便脚本至少能运行
    class AutocoderRulesManager:
        _instance = None
        def __new__(cls, *args, **kwargs):
            if cls._instance is None:
                cls._instance = super(AutocoderRulesManager, cls).__new__(cls)
            return cls._instance
        def __init__(self): print("警告：AutocoderRulesManager 未正确导入，功能将无法工作。")
        def get_rules(self): return {}
        @classmethod
        def get_instance(cls): return cls._instance
    def get_rules(): return {}


# --- 示例用法 ---
if __name__ == '__main__':
    # 创建临时目录作为示例
    example_run_dir = os.path.join(os.path.dirname(__file__), "rules_run_temp")
    if os.path.exists(example_run_dir):
        shutil.rmtree(example_run_dir)
    os.makedirs(example_run_dir)
    
    # 创建测试规则目录结构
    rules_dirs = [
        os.path.join(example_run_dir, ".autocoderrules"),
        os.path.join(example_run_dir, ".auto-coder", "autocoderrules"),
        os.path.join(example_run_dir, ".auto-coder", "autocoderules")
    ]
    
    # 创建目录结构
    for dir_path in rules_dirs:
        os.makedirs(dir_path, exist_ok=True)
    
    # 创建一些测试规则文件
    rule_files = [
        (os.path.join(rules_dirs[0], "rule1.md"), "# 规则1\n这是第一个规则文件，位于 .autocoderrules 目录"),
        (os.path.join(rules_dirs[1], "rule2.md"), "# 规则2\n这是第二个规则文件，位于 .auto-coder/autocoderrules 目录"),
        (os.path.join(rules_dirs[2], "rule3.md"), "# 规则3\n这是第三个规则文件，位于 .auto-coder/autocoderules 目录")
    ]
    
    for file_path, content in rule_files:
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
    
    print(f"创建了测试规则目录和文件：")
    for dir_path in rules_dirs:
        print(f" - {dir_path}")
    for file_path, _ in rule_files:
        print(f" - {file_path}")
    
    # 保存当前工作目录
    original_cwd = os.getcwd()
    
    try:
        # 切换到测试目录
        os.chdir(example_run_dir)
        print(f"\n切换工作目录到: {example_run_dir}")
        
        # 初始化 AutocoderRulesManager
        print("\n--- 初始化 AutocoderRulesManager ---")
        rules_manager = AutocoderRulesManager()
        
        # 获取并显示规则
        print("\n--- 获取初始规则 ---")
        rules = get_rules()
        print(f"找到 {len(rules)} 个规则文件:")
        for path, content in rules.items():
            print(f" - {path}: {content[:50]}...")
        
        # 演示文件变更监控
        print("\n--- 修改规则文件以触发监控 ---")
        print("等待 2 秒以确保监控已启动...")
        time.sleep(2)
        
        # 修改一个规则文件
        if rules:
            first_rule_path = next(iter(rules.keys()))
            print(f"修改规则文件: {first_rule_path}")
            with open(first_rule_path, "a") as f:
                f.write("\n\n这是新添加的内容，用于测试文件监控")
            
            print("等待 2 秒以确保变更被检测...")
            time.sleep(2)
            
            # 再次获取规则，应该已更新
            print("\n--- 再次获取规则（应已更新） ---")
            updated_rules = get_rules()
            print(f"找到 {len(updated_rules)} 个规则文件:")
            for path, content in updated_rules.items():
                print(f" - {path}: {content[:50]}...")
        
        # 创建新的规则文件
        print("\n--- 创建新的规则文件 ---")
        new_rule_path = os.path.join(".autocoderrules", "new_rule.md")
        with open(new_rule_path, "w", encoding="utf-8") as f:
            f.write("# 新规则\n这是一个新创建的规则文件，用于测试文件监控")
        
        print("等待 2 秒以确保变更被检测...")
        time.sleep(2)
        
        # 再次获取规则，应该包含新文件
        print("\n--- 再次获取规则（应包含新文件） ---")
        final_rules = get_rules()
        print(f"找到 {len(final_rules)} 个规则文件:")
        for path, content in final_rules.items():
            print(f" - {path}: {content[:50]}...")
        
        print("\n--- 示例完成 ---")
        
    except Exception as e:
        print(f"运行示例时出错: {e}")
    finally:
        # 恢复原始工作目录
        os.chdir(original_cwd)
        print(f"已恢复工作目录到: {original_cwd}")
        
        # 清理临时目录
        print("清理临时目录...")
        try:
            shutil.rmtree(example_run_dir)
            print(f"成功删除临时目录: {example_run_dir}")
        except OSError as e:
            print(f"警告: 无法删除临时目录: {e}")
