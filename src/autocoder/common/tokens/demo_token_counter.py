

"""
Token统计模块演示

展示如何使用TokenStatsCalculator进行文件和目录的token统计
"""

import os
import tempfile
from autocoder.common.tokens import TokenStatsCalculator
from autocoder.rag.variable_holder import VariableHolder
from autocoder.common.buildin_tokenizer import BuildinTokenizer


def setup_tokenizer():
    """设置tokenizer - 在实际使用中需要先初始化"""
    try:
        # 尝试使用内置tokenizer
        builtin_tokenizer = BuildinTokenizer()
        VariableHolder.TOKENIZER_MODEL = builtin_tokenizer.tokenizer
        print("✓ 成功初始化内置tokenizer")
        return True
    except Exception as e:
        print(f"✗ 初始化tokenizer失败: {e}")
        return False


def demo_file_token_counting():
    """演示单个文件token统计"""
    print("\n=== 单个文件Token统计演示 ===")
    
    calculator = TokenStatsCalculator()
    
    # 创建临时测试文件
    test_files = {
        "python_file.py": '''
def hello_world():
    """一个简单的问候函数"""
    print("Hello, World!")
    return "success"

if __name__ == "__main__":
    hello_world()
''',
        "text_file.txt": "这是一个简单的文本文件，包含一些中文内容。",
        "json_file.json": '''
{
    "name": "Token统计演示",
    "version": "1.0.0",
    "description": "演示文件的token统计功能"
}
''',
        "binary_file.jpg": b'\xff\xd8\xff\xe0\x00\x10JFIF'  # 模拟JPEG文件
    }
    
    with tempfile.TemporaryDirectory() as temp_dir:
        for filename, content in test_files.items():
            file_path = os.path.join(temp_dir, filename)
            
            if isinstance(content, bytes):
                with open(file_path, 'wb') as f:
                    f.write(content)
            else:
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            
            # 统计token
            stats = calculator.count_file_tokens(file_path)
            print(f"\n文件: {filename}")
            print(f"  状态: {'成功' if stats.is_success else ('跳过' if stats.skipped else '错误')}")
            
            if stats.is_success:
                print(f"  Token数量: {stats.token_count}")
            elif stats.skipped:
                print(f"  跳过原因: {stats.skip_reason}")
            elif stats.error:
                print(f"  错误信息: {stats.error}")


def demo_directory_token_counting():
    """演示目录token统计"""
    print("\n=== 目录Token统计演示 ===")
    
    calculator = TokenStatsCalculator()
    
    # 创建临时目录结构
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建子目录
        src_dir = os.path.join(temp_dir, "src")
        docs_dir = os.path.join(temp_dir, "docs")
        images_dir = os.path.join(temp_dir, "images")
        
        os.makedirs(src_dir)
        os.makedirs(docs_dir)
        os.makedirs(images_dir)
        
        # 创建各种类型的文件
        files_to_create = [
            ("src/main.py", "def main():\n    print('主程序')\n\nif __name__ == '__main__':\n    main()"),
            ("src/utils.py", "def helper_function():\n    return 'helper'"),
            ("docs/README.md", "# 项目文档\n\n这是一个演示项目。"),
            ("docs/API.md", "# API文档\n\n## 接口说明\n\n- `/api/v1/test`"),
            ("images/logo.png", b'\x89PNG\r\n\x1a\n'),  # PNG文件头
            ("images/icon.jpg", b'\xff\xd8\xff\xe0'),   # JPEG文件头
            ("config.json", '{"debug": true, "port": 8080}'),
            ("requirements.txt", "requests==2.28.0\nflask==2.0.0"),
        ]
        
        for file_path, content in files_to_create:
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            
            if isinstance(content, bytes):
                with open(full_path, 'wb') as f:
                    f.write(content)
            else:
                with open(full_path, 'w', encoding='utf-8') as f:
                    f.write(content)
        
        print(f"临时目录: {temp_dir}")
        
        # 统计整个目录
        print("\n--- 统计整个目录 ---")
        stats = calculator.count_directory_tokens(temp_dir)
        print(stats)
        
        # 只统计Python文件
        print("\n--- 只统计Python文件 ---")
        py_stats = calculator.count_directory_tokens(
            temp_dir, 
            file_pattern=r".*\.py$"
        )
        print(py_stats)
        
        # 只统计文档文件
        print("\n--- 只统计Markdown文件 ---")
        md_stats = calculator.count_directory_tokens(
            temp_dir,
            file_pattern=r".*\.md$"
        )
        print(md_stats)
        
        # 生成详细报告
        print("\n--- 详细统计报告 ---")
        report = calculator.get_summary_report(stats)
        print(report)


def demo_custom_extensions():
    """演示自定义文件扩展名"""
    print("\n=== 自定义文件扩展名演示 ===")
    
    # 创建自定义扩展名的计算器
    custom_text_extensions = {'.py', '.txt', '.md', '.custom'}
    custom_binary_extensions = {'.jpg', '.png', '.bin', '.ignore'}
    
    calculator = TokenStatsCalculator(
        text_extensions=custom_text_extensions,
        binary_extensions=custom_binary_extensions
    )
    
    with tempfile.TemporaryDirectory() as temp_dir:
        test_files = [
            ("test.custom", "这是自定义扩展名的文本文件"),
            ("data.ignore", "这个文件会被当作二进制文件跳过"),
            ("unknown.xyz", "未知扩展名文件")
        ]
        
        for filename, content in test_files:
            file_path = os.path.join(temp_dir, filename)
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            stats = calculator.count_file_tokens(file_path)
            print(f"\n文件: {filename}")
            if stats.is_success:
                print(f"  ✓ 成功统计: {stats.token_count} tokens")
            elif stats.skipped:
                print(f"  - 跳过: {stats.skip_reason}")
            else:
                print(f"  ✗ 错误: {stats.error}")


def demo_ignore_files():
    """演示ignore文件功能"""
    print("\n=== Ignore文件功能演示 ===")
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # 创建.autocoderignore文件
        ignore_content = '''
# 忽略日志文件
*.log

# 忽略临时文件
*.tmp
temp/

# 忽略特定文件
secret.txt
'''
        ignore_file = os.path.join(temp_dir, '.autocoderignore')
        with open(ignore_file, 'w') as f:
            f.write(ignore_content)
        
        # 创建测试文件
        test_files = [
            ("main.py", "print('main')"),
            ("app.log", "日志内容"),
            ("data.tmp", "临时数据"),
            ("secret.txt", "机密信息"),
            ("public.txt", "公开信息"),
            ("temp/cache.txt", "缓存文件")
        ]
        
        for file_path, content in test_files:
            full_path = os.path.join(temp_dir, file_path)
            os.makedirs(os.path.dirname(full_path), exist_ok=True)
            with open(full_path, 'w') as f:
                f.write(content)
        
        # 使用ignore文件的计算器
        calculator_with_ignore = TokenStatsCalculator(
            use_ignore_files=True,
            project_root=temp_dir
        )
        
        # 不使用ignore文件的计算器
        calculator_without_ignore = TokenStatsCalculator(
            use_ignore_files=False,
            project_root=temp_dir
        )
        
        print("使用ignore文件:")
        stats_with = calculator_with_ignore.count_directory_tokens(temp_dir)
        print(f"  处理文件数: {stats_with.total_files}")
        print(f"  成功统计: {stats_with.successful_files}")
        print(f"  跳过文件: {stats_with.skipped_files}")
        
        print("\n不使用ignore文件:")
        stats_without = calculator_without_ignore.count_directory_tokens(temp_dir)
        print(f"  处理文件数: {stats_without.total_files}")
        print(f"  成功统计: {stats_without.successful_files}")
        print(f"  跳过文件: {stats_without.skipped_files}")


def main():
    """主演示函数"""
    print("=== Token统计模块演示 ===")
    
    # 首先设置tokenizer
    if not setup_tokenizer():
        print("无法初始化tokenizer，演示将无法进行token统计")
        return
    
    try:
        # 演示各种功能
        demo_file_token_counting()
        demo_directory_token_counting()
        demo_custom_extensions()
        demo_ignore_files()
        
        print("\n=== 演示完成 ===")
        print("Token统计模块提供了以下主要功能：")
        print("1. 单个文件token统计")
        print("2. 目录递归token统计")
        print("3. 正则表达式文件过滤")
        print("4. 自动识别和跳过二进制文件")
        print("5. 支持.autocoderignore文件")
        print("6. 自定义文件扩展名配置")
        print("7. 详细的统计报告生成")
        
    except Exception as e:
        print(f"演示过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()


