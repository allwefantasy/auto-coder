from autocoder.commands.tools import AutoCommandTools
from autocoder.common import AutoCoderArgs
import byzerllm
import os

def test_read_file_with_keyword_ranges():
    # 设置测试环境
    args = AutoCoderArgs(
        source_dir="/Users/allwefantasy/projects/auto-coder",
        project_type="py"
    )
    
    # 初始化LLM和AutoCommandTools
    llm = byzerllm.SimpleByzerLLM()
    tools = AutoCommandTools(args=args, llm=llm)
    
    # 测试场景1: 搜索单个关键字
    file_path = "src/autocoder/commands/tools.py"
    keyword = "read_file_with_keyword_ranges"
    result1 = tools.read_file_with_keyword_ranges(file_path, keyword, before_size=5, after_size=5)
    print("=== Test 1: Search single keyword ===")
    print(result1)
    print("\n")

    # 测试场景2: 搜索多次出现的关键字
    keyword2 = "def"
    result2 = tools.read_file_with_keyword_ranges(file_path, keyword2, before_size=2, after_size=2)
    print("=== Test 2: Search frequently appearing keyword ===")
    print(result2)
    print("\n")

    # 测试场景3: 搜索不存在的关键字
    keyword3 = "nonexistentkeyword123456"
    result3 = tools.read_file_with_keyword_ranges(file_path, keyword3, before_size=3, after_size=3)
    print("=== Test 3: Search non-existent keyword ===")
    print(result3)
    print("\n")

    # 测试场景4: 使用不同的before_size和after_size
    keyword4 = "AutoCommandTools"
    result4 = tools.read_file_with_keyword_ranges(file_path, keyword4, before_size=10, after_size=20)
    print("=== Test 4: Different before and after sizes ===")
    print(result4)

if __name__ == "__main__":
    test_read_file_with_keyword_ranges()