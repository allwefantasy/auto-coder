"""
AutoCommandTools 快速入门

这个脚本展示了AutoCommandTools的基本用法，适合快速了解其核心功能。
"""

import os
from autocoder.commands.tools import AutoCommandTools
from autocoder.common import AutoCoderArgs
from autocoder.utils.llms import get_single_llm

# 设置项目路径
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
print(f"项目根目录: {project_root}")

# 初始化工具
print("初始化LLM和AutoCommandTools...")
llm = get_single_llm("v3_chat", product_mode="lite")
args = AutoCoderArgs(model="v3_chat", source_dir=project_root)
tools = AutoCommandTools(args, llm)

# 1. 读取文件示例
print("\n===== 读取文件示例 =====")
example_file = os.path.join(project_root, "notebooks/test.py")
if os.path.exists(example_file):
    content = tools.read_files(paths=example_file, line_ranges="1-10")
    print(f"文件内容 (前10行):\n{content}")
else:
    print(f"文件 {example_file} 不存在，尝试另一个文件")
    # 尝试读取当前脚本自身
    content = tools.read_files(paths=__file__, line_ranges="1-10")
    print(f"当前脚本内容 (前10行):\n{content}")

# 2. 搜索代码示例
print("\n===== 搜索代码示例 =====")
search_results = tools.search_code(
    query="AutoCommandTools class", 
    num_results=2
)
print(f"搜索结果:\n{search_results}")

# 3. 文件查找示例
print("\n===== 文件查找示例 =====")
files = tools.find_files(
    query="*.py", 
    num_results=3
)
print(f"找到的文件:\n{files}")

# 4. 执行简单命令
print("\n===== 执行命令示例 =====")
cmd_result = tools.run_command(
    command=f"ls -l {project_root}/notebooks",
    working_dir=project_root
)
print(f"命令执行结果:\n{cmd_result}")

# 5. 组合使用示例 - 查找文件并读取内容
print("\n===== 组合使用示例 =====")
# 先找到一个Python文件
found_files = tools.find_files(query="demo_*.py", num_results=1)
if found_files:
    # 从结果中提取文件路径
    file_path = found_files.split("\n")[0].strip()
    if os.path.exists(file_path):
        # 读取这个文件的内容
        file_content = tools.read_files(paths=file_path, line_ranges="1-5")
        print(f"找到文件: {file_path}")
        print(f"文件前5行内容:\n{file_content}")
    else:
        print(f"未能解析有效的文件路径: {file_path}")
else:
    print("没有找到匹配的文件")

print("\n演示完成，您已经了解了AutoCommandTools的基本用法！") 