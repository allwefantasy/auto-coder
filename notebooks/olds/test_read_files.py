from autocoder.commands.tools import AutoCommandTools
from autocoder.common import AutoCoderArgs
import byzerllm
import os

def test_read_files():
    # 设置测试环境
    args = AutoCoderArgs(
        source_dir="/Users/allwefantasy/projects/auto-coder",
        project_type="py"
    )
    
    # 初始化LLM和AutoCommandTools
    llm = byzerllm.SimpleByzerLLM()
    tools = AutoCommandTools(args=args, llm=llm)
    
    # # 测试场景1: 使用完整路径读取单个文件
    file_path = "src/autocoder/commands/tools.py"
    result1 = tools.read_files(file_path)
    print("=== Test 1: Read single file ===")
    print(f"Result length: {len(result1)}")
    print(f"First 200 characters:\n{result1[:200]}\n")

    # 测试场景2: 使用行范围读取文件
    result2 = tools.read_files(file_path, "1-10")
    print("=== Test 2: Read file with line range ===")
    print(result2)
    
    # # 测试场景3: 读取多个文件
    multiple_files = "src/autocoder/commands/tools.py,src/autocoder/commands/__init__.py"
    result3 = tools.read_files(multiple_files)
    print("=== Test 3: Read multiple files ===")
    print(f"Result contains tools.py: {'tools.py' in result3}")
    print(f"Result contains __init__.py: {'__init__.py' in result3}")

    # # 测试场景4: 读取多个文件的特定行范围
    result4 = tools.read_files(multiple_files, "1-10,1-5")
    print("=== Test 4: Read multiple files with line ranges ===")
    print(result4)

if __name__ == "__main__":
    test_read_files()