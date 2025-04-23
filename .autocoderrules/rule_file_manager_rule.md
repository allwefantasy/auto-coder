
---
description: 管理和加载 .autocoderrules 目录下的规则文件
globs: ["*/*.py"]
alwaysApply: false
---

# 管理和加载 .autocoderrules 目录下的规则文件

## 简要说明
提供一个 `AutocoderRulesManager` 类，用于自动发现、加载、解析（支持 YAML frontmatter + Markdown 内容）和管理项目 `.autocoderrules` 目录下的规则文件。它还集成了文件监控功能（基于 `FileMonitor`），可以实现规则文件的热加载。适用于需要集中管理配置、规则或文档片段，并希望它们能动态更新的场景。

## 典型用法
```python
# 导入必要的库
import os
import time
from typing import Dict, Optional
from loguru import logger

# 假设 AutocoderRulesManager 类定义在 'my_rules_manager_module.py'
# from my_rules_manager_module import AutocoderRulesManager, get_rules_manager
# 为了示例独立，我们直接使用 autocoderrules_utils.py 中的类
from autocoder.common.rulefiles.autocoderrules_utils import AutocoderRulesManager, get_rules_manager, get_rules

# --- 示例项目结构 ---
# project_root/
# ├── .autocoderrules/
# │   ├── rule1.md  (包含 YAML frontmatter 和 Markdown)
# │   └── rule2.yml  (纯 YAML，也会被加载)
# │   └── subdir/
# │       └── nested_rule.md
# └── main.py

# --- 准备示例规则文件 ---
def setup_example_rules(rules_dir):
    os.makedirs(os.path.join(rules_dir, "subdir"), exist_ok=True)
    
    rule1_content = """---
name: rule1
priority: 10
tags: [core, validation]
---
# Rule 1 Documentation
This is the main content of rule 1.
It uses Markdown format.
"""
    with open(os.path.join(rules_dir, "rule1.md"), "w") as f:
        f.write(rule1_content)

    rule2_content = """name: rule2
priority: 5
description: A simple YAML rule file.
"""
    with open(os.path.join(rules_dir, "rule2.yml"), "w") as f:
        f.write(rule2_content)
        
    nested_rule_content = """---
name: nested_rule
---
Content for the nested rule.
"""
    with open(os.path.join(rules_dir, "subdir", "nested_rule.md"), "w") as f:
        f.write(nested_rule_content)

# --- 主程序 ---
if __name__ == "__main__":
    # 1. 定义项目根目录和规则目录
    project_root = os.path.abspath("./rule_manager_test_project")
    rules_dir = os.path.join(project_root, ".autocoderrules")
    os.makedirs(rules_dir, exist_ok=True)
    logger.info(f"项目根目录: {project_root}")
    logger.info(f"规则目录: {rules_dir}")

    # 创建示例规则文件
    setup_example_rules(rules_dir)
    logger.info("示例规则文件已创建。")

    # 2. 获取 AutocoderRulesManager 单例实例
    # 首次调用会自动扫描规则目录
    try:
        rules_manager = get_rules_manager(project_root=project_root)
        # 或者使用 AutocoderRulesManager(project_root=project_root)
    except Exception as e:
        logger.error(f"初始化 AutocoderRulesManager 失败: {e}")
        exit(1)

    # 3. 访问加载的规则
    logger.info("--- 加载的规则 ---")
    all_rules = rules_manager.get_all_rules() # 获取所有规则的原始内容
    for file_path, content in all_rules.items():
        logger.info(f"规则文件: {file_path}")
        # logger.debug(f"内容:\n{content}") # 打印内容

    logger.info("\n--- 解析后的规则元数据 (带 frontmatter 的) ---")
    parsed_rules = rules_manager.get_parsed_rules() # 获取解析后的规则 (包含元数据和内容)
    for file_path, data in parsed_rules.items():
        logger.info(f"规则文件: {file_path}")
        logger.info(f"  元数据: {data.get('metadata')}")
        # logger.debug(f"  内容: {data.get('content')}") # 打印内容

    # 4. 使用便捷函数 get_rules() (常用)
    # 这通常在其他模块中使用，以获取当前所有有效的规则内容
    logger.info("\n--- 使用 get_rules() 获取规则 ---")
    current_rules = get_rules()
    for file_path, content in current_rules.items():
        logger.info(f"规则: {os.path.basename(file_path)}")


    # 5. 启动文件监控以实现热加载 (如果需要)
    # 注意: AutocoderRulesManager 内部会自动使用 FileMonitor (如果可用)
    # 无需手动启动 FileMonitor，除非你想独立控制它
    if rules_manager.monitor and rules_manager.monitor.is_running():
        logger.info("\n规则文件监控已自动启动。")
        
        # 模拟修改规则文件
        logger.info("将在 5 秒后模拟修改 rule1.md...")
        time.sleep(5)
        with open(os.path.join(rules_dir, "rule1.md"), "a") as f:
            f.write("\n\n*Updated content.*")
        logger.info("rule1.md 已修改。等待规则管理器重新加载...")
        
        # 等待监控器检测到变化并重新加载 (时间取决于监控器设置)
        time.sleep(5) 
        
        logger.info("\n--- 再次使用 get_rules() 获取更新后的规则 ---")
        updated_rules = get_rules()
        logger.info(f"rule1.md 内容是否包含 'Updated': {'Updated content' in updated_rules.get(os.path.join(rules_dir, 'rule1.md'), '')}")

    else:
        logger.info("\n规则文件监控未运行 (可能 FileMonitor 未初始化或被禁用)。")

    # 6. 清理 (如果需要停止监控)
    # 通常不需要手动停止，除非应用结束
    # if rules_manager.monitor and rules_manager.monitor.is_running():
    #     rules_manager.monitor.stop()
    #     logger.info("文件监控已停止。")

```

## 依赖说明
- `PyYAML`: 用于解析 YAML frontmatter。 (`pip install PyYAML`)
- `python-frontmatter`: 用于方便地处理带有 frontmatter 的文件。 (`pip install python-frontmatter`)
- `autocoder.common.file_monitor`: 依赖于之前定义的 `FileMonitor` (及其依赖 `watchfiles`, `pathspec`) 来实现热加载。
- `loguru` (可选, 用于日志记录)。
- Python 标准库 (`os`, `glob`, `threading`, etc.)

## 学习来源
从 `/Users/allwefantasy/projects/auto-coder/src/autocoder/common/rulefiles/autocoderrules_utils.py` 文件中的 `AutocoderRulesManager` 类和相关函数 (`get_rules_manager`, `get_rules`) 提取。该模块展示了如何构建一个健壮的规则/配置文件管理系统，并结合文件监控实现动态更新。
