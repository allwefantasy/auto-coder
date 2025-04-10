"""
AutoCommandTools 功能演示

这个脚本展示了如何使用AutoCommandTools来辅助代码分析和处理。
AutoCommandTools提供了一系列工具方法来搜索、读取、分析代码。
"""

import os
from pathlib import Path
from loguru import logger

from autocoder.commands.tools import AutoCommandTools
from autocoder.common import AutoCoderArgs
from autocoder.utils.llms import get_single_llm

# 设置基本目录
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
print(f"项目根目录: {project_root}")

# 初始化LLM和参数
llm = get_single_llm("v3_chat", product_mode="lite")
args = AutoCoderArgs(model="v3_chat", source_dir=project_root)

# 创建AutoCommandTools实例
tools = AutoCommandTools(args, llm)

# 示例1: 读取文件内容
print("\n=== 示例1: 读取文件内容 ===")
file_path = os.path.join(project_root, "src/autocoder/common/mcp_server.py")
file_content = tools.read_files(paths=file_path, line_ranges="1-50")
print(f"文件前50行内容:\n{file_content[:500]}...(内容已截断)")

# 示例2: 读取多个文件
print("\n=== 示例2: 读取多个文件 ===")
multiple_files = tools.read_files(
    paths=[
        os.path.join(project_root, "src/autocoder/common/__init__.py"),
        os.path.join(project_root, "src/autocoder/common/types.py")
    ],
    line_ranges=["1-10", "1-10"]
)
print(f"多个文件内容:\n{multiple_files[:500]}...(内容已截断)")

# 示例3: 搜索代码库
print("\n=== 示例3: 搜索代码库 ===")
search_results = tools.search_code(
    query="AutoCommandTools class definition",
    num_results=5
)
print(f"搜索结果:\n{search_results[:500]}...(内容已截断)")

# 示例4: 执行终端命令
print("\n=== 示例4: 执行终端命令 ===")
cmd_result = tools.run_command(
    command="ls -la " + os.path.join(project_root, "src/autocoder/commands"),
    working_dir=project_root
)
print(f"命令执行结果:\n{cmd_result}")

# 示例5: 查找文件
print("\n=== 示例5: 查找文件 ===")
files = tools.find_files(
    query="tools.py",
    num_results=5
)
print(f"文件查找结果:\n{files}")

# 示例6: 分析文件内容与结构
print("\n=== 示例6: 分析文件内容与结构 ===")
file_to_analyze = os.path.join(project_root, "src/autocoder/commands/tools.py")
if os.path.exists(file_to_analyze):
    analysis = tools.analyze_code(
        file_path=file_to_analyze
    )
    print(f"文件分析结果:\n{analysis[:500]}...(内容已截断)")
else:
    print(f"文件 {file_to_analyze} 不存在，跳过分析")

# 示例7: 结合多个工具的复杂操作
print("\n=== 示例7: 结合多个工具的复杂操作 ===")
# 首先搜索包含特定功能的文件
search_query = "read_files function implementation"
search_result = tools.search_code(query=search_query, num_results=2)
print(f"搜索 '{search_query}' 的结果:\n{search_result[:300]}...\n")

# 然后从搜索结果中提取文件路径（这里为了演示，我们直接指定）
target_file = os.path.join(project_root, "src/autocoder/commands/tools.py")
if os.path.exists(target_file):
    # 读取此文件的内容
    file_content = tools.read_files(paths=target_file, line_ranges="1-100")
    print(f"提取到的文件内容:\n{file_content[:300]}...\n")
    
    # 运行一个命令来查看文件信息
    cmd = f"wc -l {target_file}"
    cmd_result = tools.run_command(command=cmd, working_dir=project_root)
    print(f"文件行数: {cmd_result}")
else:
    print(f"文件 {target_file} 不存在，跳过此示例")

# 示例8: 使用工具辅助代码生成
print("\n=== 示例8: 使用工具辅助代码生成 ===")
prompt = """
根据下面的要求生成一个Python函数:
1. 函数名为calculate_statistics
2. 接收一个数字列表作为输入
3. 返回一个包含平均值、中位数、最大值和最小值的字典
"""
# 注意：在实际使用中，这需要一个支持代码生成的模型
# 这里仅为演示目的展示如何组合使用工具
print(f"提示:\n{prompt}\n")
print("生成的代码将基于提示和工具的辅助...")

print("\n演示完成!") 